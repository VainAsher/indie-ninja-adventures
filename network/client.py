"""
Multiplayer game client — asyncio TCP, background thread.

The pygame main loop is synchronous; all asyncio I/O runs in a daemon
thread. Communication between threads uses stdlib queue.Queue (no
asyncio primitives needed on the pygame side).

Typical usage from demo_game.py:

    from network.client import NetworkClient
    client = NetworkClient("192.168.1.5", 7777, player_id="p1")
    if client.connect():                    # blocks up to 5 s for handshake
        ...
        # inside frame loop:
        client.send_input(current_command, pos=..., vel=..., health=...)
        state = client.poll_state()         # non-blocking; None if nothing new
        ...
        client.disconnect()
"""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
import uuid
from dataclasses import dataclass
from typing import Optional

from .commands import InputCommand
from .protocol import MessageType, read_message, write_message
from .snapshots import MultiplayerSnapshot

log = logging.getLogger("ninja_dash.network.client")

CLIENT_VERSION = "1.0.0"
SEND_TIMEOUT = 0.016        # 1 frame at 60 Hz — max time to block waiting for input


@dataclass
class _SendItem:
    command: InputCommand
    pos: tuple[float, float]
    vel: tuple[float, float]
    health: int
    facing: int
    is_dead: bool


class NetworkClient:
    """
    Thread-safe multiplayer client.

    send_queue  — pygame puts _SendItem objects here each frame.
    recv_queue  — pygame reads MultiplayerSnapshot dicts from here.
    """

    def __init__(self, host: str, port: int, player_id: str = "") -> None:
        self.host = host
        self.port = port
        self.player_id = player_id or str(uuid.uuid4())[:8]

        self._send_queue: queue.Queue[_SendItem] = queue.Queue(maxsize=120)
        self._recv_queue: queue.Queue[dict] = queue.Queue(maxsize=120)
        # Phase 3: authoritative WorldSnapshot queue (server-simulated world state)
        self._world_state_queue: queue.Queue[dict] = queue.Queue(maxsize=120)
        # Outbound entity events (local → server)
        self._entity_send_queue: queue.Queue[dict] = queue.Queue(maxsize=256)
        # Inbound entity events (remote clients → this client, via server broadcast)
        self._entity_event_queue: queue.Queue[dict] = queue.Queue(maxsize=256)

        self._connected = threading.Event()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._error: Optional[str] = None

        # Filled in after SERVER_HELLO
        self.server_seed: Optional[int] = None
        self.local_slot: Optional[int] = None
        self.max_players: Optional[int] = None

        # Filled in after GAME_START — world generation parameters that must
        # match the server so all clients produce identical tile layouts.
        self.server_shape: Optional[str] = None
        self.server_rooms: Optional[int] = None
        self.server_hub_id: Optional[str] = None

        # Lobby / game-start state (set from background thread, read from pygame thread)
        self.game_started: threading.Event = threading.Event()
        self.connected_count: int = 1       # at minimum, we are connected
        self.last_leave_slot: Optional[int] = None   # slot of most recently departed player

    # ── Public API (pygame-side) ──────────────────────────────────────────────

    def connect(self, timeout: float = 5.0) -> bool:
        """
        Start the background thread and wait for the server handshake.
        Returns True if connected successfully within *timeout* seconds.
        """
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="NetworkClient"
        )
        self._thread.start()
        ok = self._connected.wait(timeout=timeout)
        if not ok:
            log.warning("Connection to %s:%d timed out", self.host, self.port)
        return ok

    def disconnect(self) -> None:
        """Signal the background thread to stop."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def send_input(
        self,
        command: InputCommand,
        pos: tuple[float, float] = (0.0, 0.0),
        vel: tuple[float, float] = (0.0, 0.0),
        health: int = 5,
        facing: int = 1,
        is_dead: bool = False,
    ) -> None:
        """
        Queue an input frame for sending. Non-blocking; drops oldest item
        if the queue is full (i.e. the network thread is lagging).
        """
        item = _SendItem(command, pos, vel, health, facing, is_dead)
        try:
            self._send_queue.put_nowait(item)
        except queue.Full:
            try:
                self._send_queue.get_nowait()   # drop oldest
            except queue.Empty:
                pass
            self._send_queue.put_nowait(item)

    def send_entity_event(self, etype: str, entity_id: str, **data) -> None:
        """
        Notify the server of a world-state mutation (Phase 2.5).

        The server echoes this to all OTHER clients so they can apply the same
        change to their local simulation.

        Args:
            etype:     Event class — "pickup_collect", "enemy_kill", "platform_trigger"
            entity_id: Stable world-space ID for the affected entity.
            **data:    Optional extra fields (e.g. pos=(x, y)).
        """
        payload: dict = {"etype": etype, "entity_id": entity_id, "slot": self.local_slot}
        payload.update(data)
        # Piggyback onto the send queue as a special dict sentinel so we don't
        # need a second queue.  The send loop detects non-_SendItem dicts and
        # emits them as ENTITY_EVENT messages.
        self._entity_send_queue.put_nowait(payload)   # picked up by _send_loop

    def poll_world_state(self) -> Optional[dict]:
        """
        Return the most recent WorldSnapshot dict received from the server, or None.

        This is the Phase 3 equivalent of poll_state() — the server's authoritative
        world state that clients should apply directly to their local entities.
        Drains the queue so only the latest frame is returned.
        """
        latest = None
        while True:
            try:
                latest = self._world_state_queue.get_nowait()
            except queue.Empty:
                break
        return latest

    def poll_entity_events(self) -> list[dict]:
        """
        Return all pending entity-event dicts received from remote clients.
        Drains the queue; returns [] if nothing is waiting.
        """
        events: list[dict] = []
        while True:
            try:
                events.append(self._entity_event_queue.get_nowait())
            except queue.Empty:
                break
        return events

    def poll_state(self) -> Optional[dict]:
        """
        Return the most recent ServerState dict received, or None.
        Drains the queue so only the latest frame is returned.
        """
        latest = None
        while True:
            try:
                latest = self._recv_queue.get_nowait()
            except queue.Empty:
                break
        return latest

    @property
    def is_connected(self) -> bool:
        return self._connected.is_set() and not self._stop_event.is_set()

    @property
    def last_error(self) -> Optional[str]:
        return self._error

    # ── Background thread ─────────────────────────────────────────────────────

    def _run(self) -> None:
        """Entry point for the daemon thread."""
        try:
            asyncio.run(self._async_main())
        except Exception as exc:
            self._error = str(exc)
            log.error("NetworkClient fatal error: %s", exc)
        finally:
            self._connected.clear()

    async def _async_main(self) -> None:
        log.debug("Attempting TCP connect to %s:%d", self.host, self.port)
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=5.0,
            )
        except (asyncio.TimeoutError, OSError) as exc:
            self._error = f"Could not connect to {self.host}:{self.port}: {exc}"
            log.warning("TCP connect failed — %s", self._error)
            return

        log.debug("TCP socket open to %s:%d — sending CLIENT_HELLO (id=%s, version=%s)",
                  self.host, self.port, self.player_id, CLIENT_VERSION)
        try:
            # Send CLIENT_HELLO
            await write_message(writer, MessageType.CLIENT_HELLO, {
                "player_id": self.player_id,
                "version": CLIENT_VERSION,
            })

            # Wait for SERVER_HELLO
            hello = await asyncio.wait_for(read_message(reader), timeout=10.0)
            if hello.type == MessageType.ERROR:
                self._error = hello.payload.get("message", "Server rejected connection")
                log.warning("Handshake rejected by server: %s", self._error)
                return
            if hello.type != MessageType.SERVER_HELLO:
                self._error = f"Unexpected message during handshake: {hello.type}"
                log.warning(self._error)
                return

            self.server_seed = hello.payload.get("seed")
            self.local_slot = hello.payload.get("slot")
            self.max_players = hello.payload.get("max_players")
            max_players = self.max_players if self.max_players is not None else "?"
            log.info(
                "Handshake OK — server=%s:%d  slot=%s  seed=%s  max_players=%s",
                self.host, self.port, self.local_slot, self.server_seed, max_players,
            )
            print(
                f"[NET] Connected to {self.host}:{self.port}  "
                f"slot={self.local_slot}  seed={self.server_seed}"
            )
            self._connected.set()

            # Run send and receive concurrently
            await asyncio.gather(
                self._send_loop(writer),
                self._recv_loop(reader),
            )
        except (asyncio.IncompleteReadError, ConnectionResetError):
            log.info("Connection to %s:%d closed by remote", self.host, self.port)
        except Exception as exc:
            self._error = str(exc)
            log.error("NetworkClient unhandled error: %s", exc, exc_info=True)
        finally:
            log.debug("Closing writer for %s:%d", self.host, self.port)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _send_loop(self, writer: asyncio.StreamWriter) -> None:
        """Drain the send queue and forward each item to the server."""
        loop = asyncio.get_running_loop()
        while not self._stop_event.is_set():
            try:
                item: _SendItem = await loop.run_in_executor(
                    None, self._send_queue.get, True, SEND_TIMEOUT
                )
            except queue.Empty:
                continue

            payload = item.command.to_dict()
            payload["pos"] = list(item.pos)
            payload["vel"] = list(item.vel)
            payload["health"] = item.health
            payload["facing"] = item.facing
            payload["is_dead"] = item.is_dead

            try:
                await write_message(writer, MessageType.INPUT, payload)
            except Exception as exc:
                log.warning("Send INPUT failed: %s", exc)
                break

            # Flush any pending outbound entity events (Phase 2.5)
            while True:
                try:
                    ev = self._entity_send_queue.get_nowait()
                    await write_message(writer, MessageType.ENTITY_EVENT, ev)
                    log.debug("Sent ENTITY_EVENT: etype=%s entity_id=%s",
                              ev.get("etype"), ev.get("entity_id"))
                except queue.Empty:
                    break
                except Exception as exc:
                    log.warning("Send ENTITY_EVENT failed: %s", exc)
                    break

    async def _recv_loop(self, reader: asyncio.StreamReader) -> None:
        """Receive server state messages and put them in the recv queue."""
        _frames_received = 0
        while not self._stop_event.is_set():
            msg = await read_message(reader)

            if msg.type == MessageType.SERVER_STATE:
                _frames_received += 1
                if _frames_received % 300 == 0:   # log throughput every ~5 s at 60 Hz
                    log.debug("SERVER_STATE: %d frames received so far", _frames_received)
                try:
                    self._recv_queue.put_nowait(msg.payload)
                except queue.Full:
                    log.debug("Recv queue full — dropping oldest frame")
                    try:
                        self._recv_queue.get_nowait()
                    except queue.Empty:
                        pass
                    self._recv_queue.put_nowait(msg.payload)

            elif msg.type == MessageType.WORLD_STATE:
                # Phase 3: authoritative world snapshot from server simulation.
                _frames_received += 1
                if _frames_received % 300 == 0:
                    log.debug("WORLD_STATE: %d frames received so far", _frames_received)
                try:
                    self._world_state_queue.put_nowait(msg.payload)
                except queue.Full:
                    try:
                        self._world_state_queue.get_nowait()
                    except queue.Empty:
                        pass
                    self._world_state_queue.put_nowait(msg.payload)

            elif msg.type == MessageType.PLAYER_JOIN:
                pid = msg.payload.get("player_id", "?")
                slot = msg.payload.get("slot", "?")
                log.info("PLAYER_JOIN: id=%s slot=%s", pid, slot)
                print(f"[NET] Player joined: {pid} (slot {slot})")

            elif msg.type == MessageType.PLAYER_LEAVE:
                pid = msg.payload.get("player_id", "?")
                slot = msg.payload.get("slot")
                if slot is not None:
                    self.last_leave_slot = int(slot)
                log.info("PLAYER_LEAVE: id=%s slot=%s", pid, slot)
                print(f"[NET] Player left: {pid}")

            elif msg.type == MessageType.LOBBY_UPDATE:
                prev = self.connected_count
                self.connected_count = msg.payload.get("connected", self.connected_count)
                if self.connected_count != prev:
                    log.debug("LOBBY_UPDATE: %d/%s players",
                              self.connected_count, msg.payload.get("max", "?"))

            elif msg.type == MessageType.GAME_START:
                seed = msg.payload.get("seed")
                if seed is not None:
                    self.server_seed = int(seed)
                shape = msg.payload.get("shape")
                if shape is not None:
                    self.server_shape = str(shape)
                rooms = msg.payload.get("rooms")
                if rooms is not None:
                    self.server_rooms = int(rooms)
                hub_id = msg.payload.get("hub_id")
                if hub_id is not None:
                    self.server_hub_id = str(hub_id)
                self.game_started.set()
                log.info("GAME_START: seed=%s shape=%s rooms=%s hub_id=%s",
                         self.server_seed, self.server_shape, self.server_rooms, self.server_hub_id)
                print(f"[NET] Game started — seed={self.server_seed} shape={self.server_shape} rooms={self.server_rooms} hub_id={self.server_hub_id}")

            elif msg.type == MessageType.ENTITY_EVENT:
                # Phase 2.5: world-state mutation broadcast from server.
                # Ignore events that originated from this client (same slot).
                src_slot = msg.payload.get("slot")
                if src_slot != self.local_slot:
                    try:
                        self._entity_event_queue.put_nowait(msg.payload)
                    except queue.Full:
                        try:
                            self._entity_event_queue.get_nowait()
                        except queue.Empty:
                            pass
                        self._entity_event_queue.put_nowait(msg.payload)
                    log.debug("ENTITY_EVENT queued: etype=%s entity_id=%s from_slot=%s",
                              msg.payload.get("etype"), msg.payload.get("entity_id"), src_slot)

            elif msg.type == MessageType.ERROR:
                self._error = msg.payload.get("message", "Unknown server error")
                log.error("Server sent ERROR: %s", self._error)
                break

            else:
                log.debug("Unhandled message type: %s  payload=%s", msg.type, msg.payload)
