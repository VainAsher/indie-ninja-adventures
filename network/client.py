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
import socket
import threading
import uuid
from dataclasses import dataclass
from typing import Optional

from .commands import InputCommand
from .protocol import MessageType, read_message, write_message
from .snapshots import MultiplayerSnapshot

log = logging.getLogger("ninja_dash.network.client")

CLIENT_VERSION = "2.0.0"


class _EntityCache:
    """
    Reconstructs full WorldSnapshot state from a stream of full + delta frames.

    The server sends ``is_delta=False`` every FULL_SNAPSHOT_INTERVAL frames and
    ``is_delta=True`` deltas in between.  This cache applies each delta so
    callers always receive a complete dict regardless of frame type.
    """

    __slots__ = ("_enemies", "_pickups", "_platforms")

    def __init__(self) -> None:
        self._enemies: dict[str, dict] = {}
        self._pickups: dict[str, dict] = {}
        self._platforms: dict[str, dict] = {}

    def apply(self, payload: dict) -> dict:
        """
        Apply a WORLD_STATE payload and return a full-state dict.

        The returned dict always has the same shape as WorldSnapshot.to_dict()
        so downstream code (demo_game.py) requires no changes.
        """
        if not payload.get("is_delta", False):
            # Full snapshot — replace caches wholesale
            self._enemies = {e["enemy_id"]: e for e in payload.get("enemies", [])}
            self._pickups = {p["pickup_id"]: p for p in payload.get("pickups", [])}
            self._platforms = {
                ps["platform_id"]: ps for ps in payload.get("platform_states", [])
            }
            return payload

        # Delta: apply changed and removed entities
        for e in payload.get("enemies_changed", []):
            self._enemies[e["enemy_id"]] = e
        for eid in payload.get("enemies_removed", []):
            self._enemies.pop(eid, None)

        for p in payload.get("pickups_changed", []):
            self._pickups[p["pickup_id"]] = p
        for pid in payload.get("pickups_removed", []):
            self._pickups.pop(pid, None)

        for ps in payload.get("platforms_changed", []):
            self._platforms[ps["platform_id"]] = ps
        for psid in payload.get("platforms_removed", []):
            self._platforms.pop(psid, None)

        return {
            "frame":           payload["frame"],
            "seed":            payload["seed"],
            "is_delta":        False,
            "players":         payload["players"],
            "enemies":         list(self._enemies.values()),
            "pickups":         list(self._pickups.values()),
            "platform_states": list(self._platforms.values()),
            "metadata":        payload.get("metadata", {}),
        }
# Send input immediately on button change; throttle to this many frames between
# identical-state sends (60 Hz game loop ÷ 3 = 20 Hz hold-state send rate).
INPUT_HOLD_INTERVAL = 3


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
        # Base world_seed used by hub_manager — must equal the host's
        # hub_manager.world_seed so SeedDerivation produces identical results.
        self.server_world_seed: Optional[int] = None

        # Lobby / game-start state (set from background thread, read from pygame thread)
        self.game_started: threading.Event = threading.Event()
        self.connected_count: int = 1       # at minimum, we are connected
        self.last_leave_slot: Optional[int] = None   # slot of most recently departed player

        # INPUT rate-limiting (pygame-side, called from main thread only)
        # Send immediately when any button changes; throttle to 20 Hz when
        # holding the same state to avoid sending 60 identical packets/s.
        self._last_sent_buttons: tuple = ()
        self._hold_frames: int = 0

        # WORLD_STATE delta reconstruction — applies full/delta frames from the
        # server and always presents a complete state dict to poll_world_state().
        self._world_cache = _EntityCache()

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

        Rate limiting: any button-state change is sent immediately (full 60 Hz
        responsiveness for new presses/releases).  When the same button state
        is held across consecutive frames we throttle to INPUT_HOLD_INTERVAL
        (≈ 20 Hz) to avoid sending 60 identical packets per second upstream.
        """
        # Compare all gameplay-relevant boolean fields + facing/is_dead.
        # Deliberately exclude command.frame so a frame-counter difference
        # alone does not count as a "new" input.
        buttons = (
            command.up, command.down, command.left, command.right,
            command.jump, command.dash, command.crouch,
            command.attack, command.throw, command.teleport, command.ninjutsu,
            command.interact, command.inventory, command.consumable,
            command.slow_walk, command.menu_confirm, command.menu_back,
            facing, is_dead,
        )
        if buttons == self._last_sent_buttons:
            self._hold_frames += 1
            if self._hold_frames < INPUT_HOLD_INTERVAL:
                return  # same state, throttle
        self._last_sent_buttons = buttons
        self._hold_frames = 0

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

        # Disable Nagle's algorithm so small INPUT packets are sent immediately
        # rather than being buffered for up to 40ms waiting for ACK / MSS.
        _sock = writer.transport.get_extra_info("socket")
        if _sock is not None:
            try:
                _sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except OSError:
                pass

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
        while not self._stop_event.is_set():
            try:
                item: _SendItem = self._send_queue.get_nowait()
            except queue.Empty:
                # Nothing to send — yield to the event loop briefly so that
                # _recv_loop can process inbound data without blocking.
                # 100 µs gives ~10× tighter input latency than the previous
                # 1 ms sleep while still avoiding a busy-spin.
                await asyncio.sleep(0.0001)
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
                # Reconstruct full state from full or delta frame before queuing.
                _frames_received += 1
                if _frames_received % 300 == 0:
                    log.debug("WORLD_STATE: %d frames received so far", _frames_received)
                reconstructed = self._world_cache.apply(msg.payload)
                try:
                    self._world_state_queue.put_nowait(reconstructed)
                except queue.Full:
                    try:
                        self._world_state_queue.get_nowait()
                    except queue.Empty:
                        pass
                    self._world_state_queue.put_nowait(reconstructed)

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
                world_seed = msg.payload.get("world_seed")
                if world_seed is not None:
                    self.server_world_seed = int(world_seed)
                self.game_started.set()
                log.info("GAME_START: seed=%s shape=%s rooms=%s hub_id=%s world_seed=%s",
                         self.server_seed, self.server_shape, self.server_rooms,
                         self.server_hub_id, self.server_world_seed)
                print(f"[NET] Game started — seed={self.server_seed} shape={self.server_shape} rooms={self.server_rooms} hub_id={self.server_hub_id} world_seed={self.server_world_seed}")

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
