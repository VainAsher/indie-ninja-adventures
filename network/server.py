"""
Multiplayer game server — asyncio TCP, authoritative simulation (Phase 3).

Phase 3: The server runs the full game simulation at 60 Hz and broadcasts
WorldSnapshot to all connected clients each tick.  Clients apply the snapshot
authoritatively and no longer rely on client-side divergent simulation.

Phase 1/2.5 relay path is kept intact when the simulator is not yet ready
(i.e. before the first GAME_START).

Usage (from CLI via demo_game.py --host <port>):

    import asyncio, threading
    from network.server import run_server
    t = threading.Thread(target=lambda: asyncio.run(run_server(port=7777, seed=42)), daemon=True)
    t.start()
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from dataclasses import dataclass
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

    async def start_game(self, server: "GameServer | None" = None) -> None:
        """Mark the session as started and notify all clients."""
        self.game_started = True
        player_ids = list(self.players.keys())
        log.info("GAME_START: seed=%d  players=%s", self.seed, player_ids)
        print(f"[NET] Game starting — seed={self.seed}")
        await self.broadcast(MessageType.GAME_START, {
            "seed": self.seed,
            "shape":  getattr(server, "_world_shape",  "snake")        if server else "snake",
            "rooms":  getattr(server, "_world_rooms",  8)              if server else 8,
            "hub_id": getattr(server, "_world_hub_id", "central_hub") if server else "central_hub",
        })
        # Phase 3: bootstrap the authoritative simulator now that we know the
        # seed and player count.  Init is blocking (world gen) so run it in a
        # thread to avoid stalling the event loop.
        if server is not None:
            loop = asyncio.get_event_loop()
            try:
                await loop.run_in_executor(None, server._init_simulator)
            except Exception as exc:
                log.error("[SIM] Failed to initialise GameSimulator: %s", exc, exc_info=True)


# ──────────────────────────────────────────────────────────────────────────────
# Game server
# ──────────────────────────────────────────────────────────────────────────────

class GameServer:
    def __init__(
        self,
        host: str,
        port: int,
        seed: int,
        max_players: int = MAX_PLAYERS,
        world_shape: str = "snake",
        world_rooms: int = 8,
        world_hub_id: str = "central_hub",
    ) -> None:
        self.host = host
        self.port = port
        self.session = GameSession(seed=seed, max_players=max_players)
        self._server: Optional[asyncio.Server] = None
        self._sim_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._world_shape = world_shape
        self._world_rooms = world_rooms
        self._world_hub_id = world_hub_id

        # Phase 3: authoritative simulator (created lazily on first GAME_START)
        self._simulator = None

    # ── Simulator bootstrap ───────────────────────────────────────────────────

    def _init_simulator(self) -> None:
        """
        Initialise the headless GameSimulator for this session.

        Runs pygame in dummy-video mode (already confirmed safe by --headless
        path in demo_game.py).  Generates the world from current_seed, creates
        one Player per configured slot, then wires everything into GameSimulator.
        """
        import pygame
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        if not pygame.get_init():
            pygame.init()

        seed = self.session.seed
        max_slots = self.session.max_players

        # Core systems
        from game.game_initialization import create_core_systems, create_physics_and_collision
        core = create_core_systems()
        bus = core["bus"]
        game_clock = core["game_clock"]
        entity_manager = core["entity_manager"]
        logger = core["logger"]

        phys = create_physics_and_collision(bus, entity_manager, logger, seed)
        collision_system = phys["collision_system"]
        enemy_manager = phys["enemy_manager"]

        from entities import PickupManager, HazardManager
        pickup_manager = PickupManager(bus)
        hazard_manager = HazardManager(bus)

        # World generation — headless, same seed+shape+rooms the clients use
        from game.world_builder import create_server_world
        tiles, platforms, _seed, spawn_x, spawn_y, megamap = create_server_world(
            seed=seed,
            shape=self._world_shape,
            rooms=self._world_rooms,
            collision_system=collision_system,
            enemy_manager=enemy_manager,
            pickup_manager=pickup_manager,
            hazard_manager=hazard_manager,
        )

        # Build dynamic/static platform lists from megamap tiles
        dynamic_platforms: list[dict] = []
        static_platforms: list = []
        if megamap and getattr(megamap, "tilemap", None):
            import pygame as _pg
            import random as _rnd
            from systems.room_generation import (
                TILE_PLATFORM, TILE_PLATFORM_FALLING, TILE_PLATFORM_MOVING,
            )
            tilemap = megamap.tilemap
            height = len(tilemap)
            width = len(tilemap[0]) if height > 0 else 0
            for ty in range(height):
                row = tilemap[ty]
                for tx in range(width):
                    tile_id = row[tx]
                    world_x = tx * 32
                    world_y = ty * 32
                    if tile_id == TILE_PLATFORM:
                        static_platforms.append(_pg.Rect(world_x, world_y, 32, 32))
                    elif tile_id == TILE_PLATFORM_FALLING:
                        rect = _pg.Rect(world_x, world_y, 32, 32)
                        dynamic_platforms.append({
                            "id": f"plat_{tx}_{ty}",
                            "type": "falling",
                            "rect": rect,
                            "origin_x": world_x,
                            "origin_y": world_y,
                            "pos_x": float(world_x),
                            "pos_y": float(world_y),
                            "state": "idle",
                            "timer": 0.0,
                            "vy": 0.0,
                            "active": True,
                            "visible": True,
                        })
                    elif tile_id == TILE_PLATFORM_MOVING:
                        rect = _pg.Rect(world_x, world_y, 32, 32)
                        _seed_p = seed ^ (tx * 73856093) ^ (ty * 19349663)
                        _rng = _rnd.Random(_seed_p)
                        dynamic_platforms.append({
                            "id": f"plat_{tx}_{ty}",
                            "type": "moving",
                            "rect": rect,
                            "origin_x": world_x,
                            "origin_y": world_y,
                            "pos_x": float(world_x),
                            "pos_y": float(world_y),
                            "min_x": float(world_x - 2 * 32),
                            "max_x": float(world_x + 2 * 32),
                            "speed": _rng.uniform(30.0, 70.0),
                            "dir": _rng.choice([-1, 1]),
                            "active": True,
                            "visible": True,
                        })
            collision_system.update_platforms(
                static_platforms + [p["rect"] for p in dynamic_platforms if p["active"]]
            )

        # Create one Player per slot (all slots pre-created for the server simulation)
        from game.game_initialization import create_player
        sim_players: dict[int, object] = {}
        _sx = float(spawn_x) if spawn_x else 100.0
        _sy = float(spawn_y) if spawn_y else 100.0
        for slot in range(max_slots):
            p, _entity, _lm = create_player(
                spawn_x=_sx,
                spawn_y=_sy,
                bus=bus,
                logger=logger,
                collision_system=collision_system,
                entity_manager=entity_manager,
                enemy_manager=enemy_manager,
                hazard_manager=hazard_manager,
            )
            # Override player_id to match slot index
            p.player_id = slot
            sim_players[slot] = p

        # Reset clock so the first tick() call doesn't see accumulated wall time
        # from world generation and fire multiple TickEvents at once.
        game_clock.reset()

        from game.game_simulator import GameSimulator
        self._simulator = GameSimulator(
            bus=bus,
            game_clock=game_clock,
            collision_system=collision_system,
            players=sim_players,
            enemy_manager=enemy_manager,
            pickup_manager=pickup_manager,
            hazard_manager=hazard_manager,
            dynamic_platforms=dynamic_platforms,
            static_platforms=static_platforms,
            megamap=megamap,
            seed=seed,
            handle_platforms=True,
        )
        log.info("[SIM] GameSimulator initialised  seed=%d  slots=%d  enemies=%d  pickups=%d",
                 seed, max_slots,
                 len(enemy_manager.enemies),
                 len(pickup_manager.get_alive_pickups()))

    # ── Simulation loop ───────────────────────────────────────────────────────

    async def _simulation_loop(self) -> None:
        """
        Proactive 60 Hz simulation loop.

        Collects the latest InputCommand from each connected slot, advances the
        GameSimulator by one tick, then broadcasts a WorldSnapshot to all clients.
        Drift correction keeps the loop tight even when a tick takes longer than
        TICK_INTERVAL.
        """
        loop = asyncio.get_event_loop()
        _ticks = 0
        _behind_count = 0

        while not self._stop_event.is_set():
            t0 = loop.time()

            if self._simulator is not None and self.session.game_started:
                # Collect latest InputCommand per slot
                async with self.session._lock:
                    inputs: dict[int, InputCommand] = {}
                    for cp in self.session.players.values():
                        if cp.latest_input is not None:
                            inputs[cp.slot] = cp.latest_input

                # Advance simulation
                try:
                    self._simulator.step(inputs, TICK_INTERVAL)
                    self.session.frame += 1
                    _ticks += 1
                except Exception as exc:
                    log.error("[SIM] step() error at frame %d: %s", self.session.frame, exc,
                              exc_info=True)

                # Build and broadcast WorldSnapshot
                try:
                    snap = self._simulator.get_snapshot(self.session.frame)
                    await self.session.broadcast(
                        MessageType.WORLD_STATE, snap.to_dict()
                    )
                except Exception as exc:
                    log.error("[SIM] get_snapshot/broadcast error: %s", exc, exc_info=True)

                if _ticks % (TICK_RATE * 5) == 0:  # every 5 s
                    log.debug("[SIM] tick=%d frame=%d  players=%d",
                              _ticks, self.session.frame, len(self.session.players))

            elapsed = loop.time() - t0
            sleep_for = TICK_INTERVAL - elapsed
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)
            else:
                _behind_count += 1
                if _behind_count % 60 == 0:
                    log.warning("[SIM] loop behind by %.1f ms (frame=%d)",
                                -sleep_for * 1000, self.session.frame)
                await asyncio.sleep(0)  # yield to event loop

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_client, self.host, self.port
        )
        addrs = [str(s.getsockname()) for s in self._server.sockets]
        log.info("Server listening on %s  seed=%d  max_players=%d",
                 addrs, self.session.seed, self.session.max_players)
        print(f"[NET] Server listening on {self.host}:{self.port}  seed={self.session.seed}")

        # Start the proactive simulation loop task
        self._sim_task = asyncio.create_task(self._simulation_loop())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._sim_task:
            self._sim_task.cancel()
            try:
                await self._sim_task
            except asyncio.CancelledError:
                pass
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
            await self.session.start_game(server=self)

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
                _inputs_processed += 1
                if _inputs_processed % 300 == 0:   # ~5 s at 60 Hz
                    log.debug("Input: %d processed for %s  server_frame=%d",
                              _inputs_processed, player.player_id, self.session.frame)

                # Phase 1/2.5 fallback: broadcast a MultiplayerSnapshot only
                # when the authoritative simulator is not yet running.
                if self._simulator is None:
                    self.session.frame += 1
                    snapshot = self.session.build_snapshot()
                    await self.session.broadcast(
                        MessageType.SERVER_STATE, snapshot.to_dict()
                    )

            elif msg.type == MessageType.ENTITY_EVENT:
                # Phase 2.5: relay world-state mutation to all other clients so
                # each simulation applies the same pickup/kill/trigger event.
                # This becomes a no-op once Phase 3 WorldSnapshot is authoritative.
                etype = msg.payload.get("etype", "?")
                eid = msg.payload.get("entity_id", "?")
                log.debug("ENTITY_EVENT from %s (slot %d): etype=%s entity_id=%s",
                          player.player_id, player.slot, etype, eid)
                if self._simulator is None:
                    # Only relay during Phase 2.5 — WorldSnapshot covers this in Phase 3
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
    world_shape: str = "snake",
    world_rooms: int = 8,
    world_hub_id: str = "central_hub",
) -> None:
    """
    Start the game server and run until cancelled.
    Intended to be called via asyncio.run() in a daemon thread.
    """
    server = GameServer(
        host=host, port=port, seed=seed, max_players=max_players,
        world_shape=world_shape, world_rooms=world_rooms,
        world_hub_id=world_hub_id,
    )
    await server.start()
    await server.serve_forever()
