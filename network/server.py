"""
Multiplayer game server — asyncio TCP, authoritative input relay.

Phase 1: input relay only. The server receives InputCommand frames from
each connected client, stamps them with the server frame counter, builds
a MultiplayerSnapshot from the last-known state of every player, and
broadcasts it back to all clients.

No game simulation runs on the server in Phase 1. Full authoritative
simulation is Phase 2 (requires extracting game loop into GameRunner).

Usage (from CLI via demo_game.py --host <port>):

    import asyncio, threading
    from network.server import run_server
    t = threading.Thread(target=lambda: asyncio.run(run_server(port=7777, seed=42)), daemon=True)
    t.start()
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional

from .commands import InputCommand
from .protocol import MessageType, read_message, write_message
from .snapshots import MultiplayerSnapshot, PlayerState

log = logging.getLogger("ninja_dash.network.server")

MAX_PLAYERS = 4
SERVER_VERSION = "1.0.0"
TICK_RATE = 60          # target broadcast ticks per second
TICK_INTERVAL = 1.0 / TICK_RATE


# ──────────────────────────────────────────────────────────────────────────────
# Connected player record
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ConnectedPlayer:
    player_id: str
    slot: int
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    latest_input: Optional[InputCommand] = None
    # Last known position/velocity for snapshot broadcast
    pos: tuple[float, float] = (0.0, 0.0)
    vel: tuple[float, float] = (0.0, 0.0)
    health: int = 5
    facing: int = 1
    is_dead: bool = False
    frame: int = 0


# ──────────────────────────────────────────────────────────────────────────────
# Game session
# ──────────────────────────────────────────────────────────────────────────────

class GameSession:
    """
    Manages one multiplayer session.

    Phase 1: input relay — stores latest input per player, broadcasts
    a MultiplayerSnapshot containing all players' last-known state.
    Phase L2: tracks lobby state; game only starts when host calls start_game().
    """

    def __init__(self, seed: int, max_players: int = MAX_PLAYERS) -> None:
        self.seed = seed
        self.max_players = max_players
        self.frame = 0
        self.players: Dict[str, ConnectedPlayer] = {}
        self._lock = asyncio.Lock()
        self.game_started: bool = False

    @property
    def is_full(self) -> bool:
        return len(self.players) >= self.max_players

    async def add_player(self, player: ConnectedPlayer) -> bool:
        async with self._lock:
            if self.is_full:
                log.warning("add_player: session full, rejecting %s", player.player_id)
                return False
            self.players[player.player_id] = player
            log.info("Player joined: id=%s slot=%d  session=%d/%d",
                     player.player_id, player.slot, len(self.players), self.max_players)
            return True

    async def remove_player(self, player_id: str) -> None:
        async with self._lock:
            self.players.pop(player_id, None)
            log.info("Player left: id=%s  session=%d/%d",
                     player_id, len(self.players), MAX_PLAYERS)

    def next_slot(self) -> int:
        used = {p.slot for p in self.players.values()}
        for s in range(self.max_players):
            if s not in used:
                return s
        return self.max_players

    async def handle_input(self, player_id: str, payload: dict) -> None:
        """Store the latest input for a player and update their state."""
        async with self._lock:
            player = self.players.get(player_id)
            if not player:
                return
            try:
                player.latest_input = InputCommand.from_dict(payload)
                player.frame = payload.get("frame", player.frame)
            except Exception as exc:
                log.debug("Bad input payload from %s: %s", player_id, exc)
            # Update position/health if client sent it alongside input
            if "pos" in payload:
                player.pos = (float(payload["pos"][0]), float(payload["pos"][1]))
            if "vel" in payload:
                player.vel = (float(payload["vel"][0]), float(payload["vel"][1]))
            if "health" in payload:
                player.health = int(payload["health"])
            if "facing" in payload:
                player.facing = int(payload["facing"])
            if "is_dead" in payload:
                player.is_dead = bool(payload["is_dead"])

    def build_snapshot(self) -> MultiplayerSnapshot:
        """Build a MultiplayerSnapshot from current player states."""
        player_states = [
            PlayerState(
                player_id=p.player_id,
                slot=p.slot,
                pos=p.pos,
                vel=p.vel,
                health=p.health,
                facing=p.facing,
                is_dead=p.is_dead,
            )
            for p in sorted(self.players.values(), key=lambda x: x.slot)
        ]
        return MultiplayerSnapshot(
            frame=self.frame,
            seed=self.seed,
            players=player_states,
            metadata={},
        )

    async def broadcast(self, msg_type: str, payload: dict) -> None:
        """Send a message to every connected player."""
        async with self._lock:
            writers = [(p.player_id, p.writer) for p in self.players.values()]
        for pid, writer in writers:
            try:
                await write_message(writer, msg_type, payload)
            except Exception as exc:
                log.debug("Broadcast to %s failed: %s", pid, exc)

    async def broadcast_lobby_update(self) -> None:
        """Broadcast current lobby state to all connected players."""
        async with self._lock:
            players_info = [
                {"player_id": p.player_id, "slot": p.slot}
                for p in sorted(self.players.values(), key=lambda x: x.slot)
            ]
            count = len(self.players)
        await self.broadcast(MessageType.LOBBY_UPDATE, {
            "connected": count,
            "max": self.max_players,
            "players": players_info,
        })

    async def start_game(self) -> None:
        """Mark the session as started and notify all clients."""
        self.game_started = True
        player_ids = list(self.players.keys())
        log.info("GAME_START: seed=%d  players=%s", self.seed, player_ids)
        print(f"[NET] Game starting — seed={self.seed}")
        await self.broadcast(MessageType.GAME_START, {"seed": self.seed})


# ──────────────────────────────────────────────────────────────────────────────
# Game server
# ──────────────────────────────────────────────────────────────────────────────

class GameServer:
    def __init__(self, host: str, port: int, seed: int, max_players: int = MAX_PLAYERS) -> None:
        self.host = host
        self.port = port
        self.session = GameSession(seed=seed, max_players=max_players)
        self._server: Optional[asyncio.Server] = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_client, self.host, self.port
        )
        addrs = [str(s.getsockname()) for s in self._server.sockets]
        log.info("Server listening on %s  seed=%d  max_players=%d",
                 addrs, self.session.seed, self.session.max_players)
        print(f"[NET] Server listening on {self.host}:{self.port}  seed={self.session.seed}")

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def serve_forever(self) -> None:
        if self._server:
            async with self._server:
                await self._server.serve_forever()

    # ── Client handler ────────────────────────────────────────────────────────

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        addr = writer.get_extra_info("peername")
        log.info("Incoming connection from %s", addr)

        if self.session.is_full:
            mp = self.session.max_players
            log.warning("Rejecting %s — session full (%d/%d)", addr, mp, mp)
            await write_message(writer, MessageType.ERROR, {
                "code": "session_full",
                "message": f"Server is full (max {mp} players).",
            })
            writer.close()
            return

        # Handshake
        try:
            hello = await asyncio.wait_for(read_message(reader), timeout=10.0)
        except asyncio.TimeoutError:
            log.warning("Handshake timeout from %s", addr)
            writer.close()
            return
        except Exception as exc:
            log.warning("Handshake error from %s: %s", addr, exc)
            writer.close()
            return

        if hello.type != MessageType.CLIENT_HELLO:
            await write_message(writer, MessageType.ERROR, {
                "code": "expected_hello",
                "message": "Expected client_hello as first message.",
            })
            writer.close()
            return

        client_version = hello.payload.get("version", "")
        log.debug("CLIENT_HELLO from %s: id=%s version=%s",
                  addr, hello.payload.get("player_id", "?"), client_version)
        if client_version != SERVER_VERSION:
            log.warning(
                "Version mismatch from %s: client=%s server=%s (continuing — Phase 1 lenient)",
                addr, client_version, SERVER_VERSION,
            )

        player_id = hello.payload.get("player_id") or str(uuid.uuid4())[:8]
        slot = self.session.next_slot()
        player = ConnectedPlayer(
            player_id=player_id,
            slot=slot,
            reader=reader,
            writer=writer,
        )

        if not await self.session.add_player(player):
            await write_message(writer, MessageType.ERROR, {
                "code": "session_full",
                "message": "Session filled up between check and join.",
            })
            writer.close()
            return

        # Send server hello
        await write_message(writer, MessageType.SERVER_HELLO, {
            "player_id": player_id,
            "slot": slot,
            "frame": self.session.frame,
            "seed": self.session.seed,
            "max_players": self.session.max_players,
        })

        # Notify other players and broadcast updated lobby state
        await self.session.broadcast(MessageType.PLAYER_JOIN, {
            "player_id": player_id,
            "slot": slot,
        })
        await self.session.broadcast_lobby_update()

        # Auto-start when lobby is full
        if not self.session.game_started and self.session.is_full:
            await self.session.start_game()

        log.info("SERVER_HELLO sent to %s: id=%s slot=%d seed=%d",
                 addr, player_id, slot, self.session.seed)

        # Main client loop
        try:
            await self._client_loop(player)
        except (asyncio.IncompleteReadError, ConnectionResetError):
            log.info("Client %s (slot %d) disconnected from %s", player_id, slot, addr)
        except Exception as exc:
            log.error("Client loop error for %s (slot %d): %s",
                      player_id, slot, exc, exc_info=True)
        finally:
            await self.session.remove_player(player_id)
            await self.session.broadcast(MessageType.PLAYER_LEAVE, {
                "player_id": player_id,
                "slot": slot,
            })
            await self.session.broadcast_lobby_update()
            log.info("Cleaned up session entry for %s (slot %d)", player_id, slot)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _client_loop(self, player: ConnectedPlayer) -> None:
        """Read input messages from one client and relay state back."""
        _inputs_processed = 0
        while True:
            msg = await read_message(player.reader)

            if msg.type == MessageType.INPUT:
                await self.session.handle_input(player.player_id, msg.payload)
                # Advance server frame and broadcast updated state
                self.session.frame += 1
                _inputs_processed += 1
                if _inputs_processed % 300 == 0:   # ~5 s at 60 Hz
                    log.debug("Relay: %d inputs processed for %s  server_frame=%d",
                              _inputs_processed, player.player_id, self.session.frame)
                snapshot = self.session.build_snapshot()
                await self.session.broadcast(
                    MessageType.SERVER_STATE, snapshot.to_dict()
                )

            elif msg.type == MessageType.ENTITY_EVENT:
                # Phase 2.5: relay world-state mutation to all other clients so
                # each simulation applies the same pickup/kill/trigger event.
                etype = msg.payload.get("etype", "?")
                eid = msg.payload.get("entity_id", "?")
                log.debug("ENTITY_EVENT from %s (slot %d): etype=%s entity_id=%s",
                          player.player_id, player.slot, etype, eid)
                # Tag the event with the originating slot so clients can ignore
                # their own echoes.
                payload_with_source = dict(msg.payload)
                payload_with_source.setdefault("slot", player.slot)
                await self.session.broadcast(MessageType.ENTITY_EVENT, payload_with_source)

            else:
                log.debug("Unexpected message type '%s' from %s (slot %d)",
                          msg.type, player.player_id, player.slot)


# ──────────────────────────────────────────────────────────────────────────────
# Top-level coroutine
# ──────────────────────────────────────────────────────────────────────────────

async def run_server(
    host: str = "0.0.0.0",
    port: int = 7777,
    seed: int = 0,
    max_players: int = MAX_PLAYERS,
) -> None:
    """
    Start the game server and run until cancelled.
    Intended to be called via asyncio.run() in a daemon thread.
    """
    server = GameServer(host=host, port=port, seed=seed, max_players=max_players)
    await server.start()
    await server.serve_forever()
