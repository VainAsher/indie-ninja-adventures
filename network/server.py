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
import socket
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional

from .commands import InputCommand
from .protocol import MessageType, encode_message, read_message, write_encoded, write_message
from .snapshots import MultiplayerSnapshot, PlayerState

log = logging.getLogger("ninja_dash.network.server")

MAX_PLAYERS = 4
SERVER_VERSION = "2.0.0"
TICK_RATE = 60  # simulation ticks per second (physics accuracy)
TICK_INTERVAL = 1.0 / TICK_RATE
BROADCAST_EVERY_N_TICKS = 3  # broadcast WORLD_STATE every 3rd sim tick (20 Hz)
# Full snapshots every 60 broadcasts = 60 × 3 ticks = 180 sim ticks ≈ 3 s
FULL_SNAPSHOT_INTERVAL = 60

# Animation states that the server simulator cannot compute because the
# underlying flags (attack_stage, is_dashing via DashMechanic, is_throwing,
# etc.) are driven client-side in demo_game.py.  When the client reports one
# of these, the server trusts it over its own server-computed anim_state.
# Movement/physics states are always server-authoritative (omit from this set).
_ACTION_ANIM_STATES: frozenset[str] = frozenset(
    {
        "dash",
        "slash1",
        "slash2",
        "slash3",
        "slash_air",
        "jump_slash",
        "attack",
        "throw_ground",
        "throw_crouch",
        "throw_air",
        "teleport",
        "ninjutsu_hand",
        "ninjutsu_summon",
        "hurt",
        "hurt2",
    }
)


def _dict_hash(d: dict) -> int:
    """Stable hash for a shallow entity dict (all values must be hashable primitives)."""
    return hash(tuple(sorted(d.items())))


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
    anim_state: str = ""  # last known animation state (Phase 1/2.5 relay only)
    frame: int = 0
    # Phase 4: which zone this player is currently in
    hub_id: str = "central_hub"


# ──────────────────────────────────────────────────────────────────────────────
# Zone instance
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class _ZoneInstance:
    """
    One active instanced zone on the server.

    Each zone runs its own GameSimulator at 60 Hz.  Multiple zones can be
    live simultaneously — one per hub/mission that has at least one player in
    it (plus a configurable idle-TTL before teardown).
    """

    hub_id: str
    seed: int
    shape: str
    rooms: int
    world_seed: int
    spawn_x: float = 100.0
    spawn_y: float = 100.0
    simulator: Optional[object] = None
    sim_task: Optional[asyncio.Task] = None
    frame: int = 0
    # Per-zone delta encoding state (not shared across zones)
    enemy_hashes: dict = field(default_factory=dict)
    pickup_hashes: dict = field(default_factory=dict)
    platform_hashes: dict = field(default_factory=dict)
    full_snap_countdown: int = 0
    # Zone membership — player_ids currently in this zone
    player_ids: set = field(default_factory=set)
    # Asyncio stop signal for this zone's simulation task
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    # Monotonic time when the last player left (for idle reaping)
    last_occupied_at: float = 0.0


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
            log.info(
                "Player joined: id=%s slot=%d  session=%d/%d",
                player.player_id,
                player.slot,
                len(self.players),
                self.max_players,
            )
            return True

    async def remove_player(self, player_id: str) -> None:
        async with self._lock:
            self.players.pop(player_id, None)
            log.info("Player left: id=%s  session=%d/%d", player_id, len(self.players), MAX_PLAYERS)

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
            if "anim_state" in payload:
                player.anim_state = str(payload["anim_state"])

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
                anim_state=p.anim_state,
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
        """
        Send a message to every connected player.

        The payload is JSON-encoded once then written concurrently to all
        clients, so a slow or lagging client cannot delay others.
        """
        async with self._lock:
            writers = [(p.player_id, p.writer) for p in self.players.values()]
        if not writers:
            return
        encoded = encode_message(msg_type, payload)

        async def _send_one(pid: str, writer: asyncio.StreamWriter) -> None:
            try:
                await write_encoded(writer, encoded)
            except Exception as exc:
                log.debug("Broadcast to %s failed: %s", pid, exc)

        await asyncio.gather(*(_send_one(pid, w) for pid, w in writers))

    async def broadcast_lobby_update(self) -> None:
        """Broadcast current lobby state to all connected players."""
        async with self._lock:
            players_info = [
                {"player_id": p.player_id, "slot": p.slot}
                for p in sorted(self.players.values(), key=lambda x: x.slot)
            ]
            count = len(self.players)
        await self.broadcast(
            MessageType.LOBBY_UPDATE,
            {
                "connected": count,
                "max": self.max_players,
                "players": players_info,
            },
        )

    async def start_game(self, server: "GameServer | None" = None) -> None:
        """Mark the session as started and notify all clients."""
        self.game_started = True
        player_ids = list(self.players.keys())
        log.info("GAME_START: seed=%d  players=%s", self.seed, player_ids)
        print(f"[NET] Game starting — seed={self.seed}")
        await self.broadcast(
            MessageType.GAME_START,
            {
                "seed": self.seed,
                "shape": getattr(server, "_world_shape", "snake") if server else "snake",
                "rooms": getattr(server, "_world_rooms", 8) if server else 8,
                "hub_id": (
                    getattr(server, "_world_hub_id", "central_hub") if server else "central_hub"
                ),
                "world_seed": getattr(server, "_world_seed", self.seed) if server else self.seed,
            },
        )
        # Phase 3/4: bootstrap the authoritative simulator for the initial zone.
        # Init is blocking (world gen) so run it in a thread to avoid stalling
        # the event loop.
        if server is not None:
            initial_zone = server._get_or_create_zone(
                getattr(server, "_world_hub_id", "central_hub")
            )
            loop = asyncio.get_event_loop()
            try:
                await loop.run_in_executor(None, lambda: server._init_zone_simulator(initial_zone))
                if initial_zone.sim_task is None:
                    initial_zone.sim_task = asyncio.create_task(
                        server._zone_simulation_loop(initial_zone)
                    )
            except Exception as exc:
                log.error(
                    "[SIM] Failed to initialise initial zone %s: %s",
                    initial_zone.hub_id,
                    exc,
                    exc_info=True,
                )


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
        world_seed: int = 0,
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
        # Base world_seed used by hub_manager for SeedDerivation — must be the
        # same on all clients, so the server broadcasts it in GAME_START.
        self._world_seed = world_seed if world_seed != 0 else seed

        # Phase 4: instanced zone registry.
        # Each entry is a _ZoneInstance with its own simulator and delta state.
        # Keyed by hub_id; populated lazily as players travel to new zones.
        self._zones: dict[str, _ZoneInstance] = {}
        # Backward-compat alias used by Phase 1/2.5 fallback in _client_loop
        self._simulator = None  # points to initial zone's simulator once started

        # HubManager for seed/shape derivation of non-initial zones (lazy-init)
        self._hub_manager = None

        # Background task for idle-zone reaping
        self._reap_task: Optional[asyncio.Task] = None

    # ── Simulator bootstrap ───────────────────────────────────────────────────

    def _init_zone_simulator(self, zone: "_ZoneInstance") -> None:
        """
        Initialise the headless GameSimulator for one zone.

        Runs pygame in dummy-video mode (already confirmed safe by --headless
        path in demo_game.py).  Generates the world from zone.seed/shape/rooms,
        creates one Player per configured slot, then wires everything into
        GameSimulator and stores it on zone.simulator.
        """
        import pygame

        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        if not pygame.get_init():
            pygame.init()

        seed = zone.seed
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
            shape=zone.shape,
            rooms=zone.rooms,
            collision_system=collision_system,
            enemy_manager=enemy_manager,
            pickup_manager=pickup_manager,
            hazard_manager=hazard_manager,
        )
        zone.spawn_x = float(spawn_x) if spawn_x else 100.0
        zone.spawn_y = float(spawn_y) if spawn_y else 100.0

        # Build dynamic/static platform lists from megamap tiles
        dynamic_platforms: list[dict] = []
        static_platforms: list = []
        if megamap and getattr(megamap, "tilemap", None):
            import pygame as _pg
            import random as _rnd
            from systems.room_generation import (
                TILE_PLATFORM,
                TILE_PLATFORM_FALLING,
                TILE_PLATFORM_MOVING,
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
                        dynamic_platforms.append(
                            {
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
                            }
                        )
                    elif tile_id == TILE_PLATFORM_MOVING:
                        rect = _pg.Rect(world_x, world_y, 32, 32)
                        _seed_p = seed ^ (tx * 73856093) ^ (ty * 19349663)
                        _rng = _rnd.Random(_seed_p)
                        dynamic_platforms.append(
                            {
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
                            }
                        )
            collision_system.update_platforms(
                static_platforms + [p["rect"] for p in dynamic_platforms if p["active"]]
            )

        # Create one Player per slot (all slots pre-created for the server simulation)
        from game.game_initialization import create_player

        sim_players: dict[int, object] = {}
        _sx = zone.spawn_x
        _sy = zone.spawn_y
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

        # Phase 3b: Create one CombatMechanic per slot for server-authoritative
        # damage calculation.  The server is headless so we skip CameraEffectsHandler
        # (screen shake is a client-only visual).
        from mechanics.combat_mechanic import CombatMechanic

        combat_mechanics: dict[int, object] = {
            slot: CombatMechanic(
                entity_id=slot,
                event_bus=bus,
                logger=logger.get_logger(f"combat_{slot}"),
            )
            for slot in range(max_slots)
        }

        # Reset clock so the first tick() call doesn't see accumulated wall time
        # from world generation and fire multiple TickEvents at once.
        game_clock.reset()

        from game.game_simulator import GameSimulator

        zone.simulator = GameSimulator(
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
            combat_mechanics=combat_mechanics,
        )
        # Keep backward-compat alias so Phase 1/2.5 fallback check still works
        if zone.hub_id == self._world_hub_id:
            self._simulator = zone.simulator
        log.info(
            "[SIM] Zone %s initialised  seed=%d  slots=%d  enemies=%d  pickups=%d",
            zone.hub_id,
            seed,
            max_slots,
            len(enemy_manager.enemies),
            len(pickup_manager.get_alive_pickups()),
        )

    # ── Delta encoding ────────────────────────────────────────────────────────

    def _build_world_state_payload(self, snap_dict: dict, zone: "_ZoneInstance") -> dict:
        """
        Build the WORLD_STATE wire payload for one zone tick.

        Sends a full snapshot every FULL_SNAPSHOT_INTERVAL frames; all frames
        in between are deltas containing only changed/removed entities.
        Players are always included. hub_id is injected into every payload.
        """
        hub_id = zone.hub_id

        if zone.full_snap_countdown <= 0:
            zone.full_snap_countdown = FULL_SNAPSHOT_INTERVAL
            zone.enemy_hashes = {e["enemy_id"]: _dict_hash(e) for e in snap_dict["enemies"]}
            zone.pickup_hashes = {p["pickup_id"]: _dict_hash(p) for p in snap_dict["pickups"]}
            zone.platform_hashes = {
                ps["platform_id"]: _dict_hash(ps) for ps in snap_dict["platform_states"]
            }
            snap_dict["is_delta"] = False
            snap_dict["hub_id"] = hub_id
            return snap_dict

        zone.full_snap_countdown -= 1

        # --- Enemies ---
        current_enemy_ids: set[str] = set()
        enemies_changed: list[dict] = []
        for e in snap_dict["enemies"]:
            eid = e["enemy_id"]
            current_enemy_ids.add(eid)
            h = _dict_hash(e)
            if zone.enemy_hashes.get(eid) != h:
                enemies_changed.append(e)
                zone.enemy_hashes[eid] = h
        enemies_removed = [eid for eid in zone.enemy_hashes if eid not in current_enemy_ids]
        for eid in enemies_removed:
            del zone.enemy_hashes[eid]

        # --- Pickups ---
        current_pickup_ids: set[str] = set()
        pickups_changed: list[dict] = []
        for p in snap_dict["pickups"]:
            pid = p["pickup_id"]
            current_pickup_ids.add(pid)
            h = _dict_hash(p)
            if zone.pickup_hashes.get(pid) != h:
                pickups_changed.append(p)
                zone.pickup_hashes[pid] = h
        pickups_removed = [pid for pid in zone.pickup_hashes if pid not in current_pickup_ids]
        for pid in pickups_removed:
            del zone.pickup_hashes[pid]

        # --- Platform states ---
        current_platform_ids: set[str] = set()
        platforms_changed: list[dict] = []
        for ps in snap_dict["platform_states"]:
            psid = ps["platform_id"]
            current_platform_ids.add(psid)
            h = _dict_hash(ps)
            if zone.platform_hashes.get(psid) != h:
                platforms_changed.append(ps)
                zone.platform_hashes[psid] = h
        platforms_removed = [
            psid for psid in zone.platform_hashes if psid not in current_platform_ids
        ]
        for psid in platforms_removed:
            del zone.platform_hashes[psid]

        return {
            "frame": snap_dict["frame"],
            "seed": snap_dict["seed"],
            "hub_id": hub_id,
            "is_delta": True,
            "players": snap_dict["players"],
            "enemies_changed": enemies_changed,
            "enemies_removed": enemies_removed,
            "pickups_changed": pickups_changed,
            "pickups_removed": pickups_removed,
            "platforms_changed": platforms_changed,
            "platforms_removed": platforms_removed,
            "metadata": snap_dict.get("metadata", {}),
        }

    def _build_player_only_payload(self, zone: "_ZoneInstance") -> dict:
        """
        Build a lightweight player-positions-only WORLD_STATE payload.

        Sent on every simulation tick so clients receive 60 Hz player
        corrections instead of 20 Hz.  Entity state is omitted — the client's
        _EntityCache reconstructs it from the most recent full/delta frame.
        This eliminates the 3-tick drift window that caused 3× over-travel.
        """
        player_dicts: list[dict] = []
        for slot in sorted(zone.simulator.players):
            p = zone.simulator.players[slot]
            phys = p.state.physics
            facing = int(p.state.facing)
            if facing == 0:
                facing = 1
            player_dicts.append(
                {
                    "player_id": str(p.player_id),
                    "slot": slot,
                    "pos": [phys.x, phys.y],
                    "vel": [phys.vx, phys.vy],
                    "health": int(p.state.health_state.current_hp),
                    "facing": facing,
                    "is_dead": p.state.health_state.current_hp <= 0,
                }
            )
        return {
            "frame": zone.frame,
            "seed": zone.seed,
            "hub_id": zone.hub_id,
            "is_delta": True,
            "players": player_dicts,
            "enemies_changed": [],
            "enemies_removed": [],
            "pickups_changed": [],
            "pickups_removed": [],
            "platforms_changed": [],
            "platforms_removed": [],
            "metadata": {},
        }

    # ── Zone helpers ──────────────────────────────────────────────────────────

    def _get_or_create_zone(self, hub_id: str) -> "_ZoneInstance":
        """Return the existing zone for hub_id, or create a new one."""
        if hub_id not in self._zones:
            # Always derive the zone seed the same way clients do in
            # regenerate_world_state() — which calls
            # SeedDerivation.derive_region_seed(hub_manager.world_seed, hub_id)
            # whenever hub_manager and hub_id are both set.  Using _world_seed
            # directly (as the initial-hub branch previously did) produced a
            # different numeric seed and caused divergent tile/collision layouts,
            # making all server-reported entity positions wrong in client space.
            from systems.seed_hierarchy import SeedDerivation

            seed = SeedDerivation.derive_region_seed(self._world_seed, hub_id)

            # Shape/rooms: start from host-supplied defaults for the initial hub,
            # plain defaults otherwise, then let hub_def override — matching the
            # shape/rooms override logic inside regenerate_world_state().
            if hub_id == self._world_hub_id:
                shape = self._world_shape
                rooms = self._world_rooms
            else:
                shape = "blob"
                rooms = 8

            if self._hub_manager is None:
                from game.hub_manager import HubManager

                self._hub_manager = HubManager(self._world_seed)
            hub_def = self._hub_manager.get_hub_definition(hub_id)
            if hub_def is not None:
                shape = hub_def.world_shape.value
                rooms = hub_def.room_count
            elif hub_id != self._world_hub_id:
                log.warning("[ZONE] No hub definition for %s — using defaults", hub_id)

            self._zones[hub_id] = _ZoneInstance(
                hub_id=hub_id,
                seed=seed,
                shape=shape,
                rooms=rooms,
                world_seed=self._world_seed,
            )
            log.info(
                "[ZONE] Created zone: hub_id=%s seed=%d shape=%s rooms=%d",
                hub_id,
                seed,
                shape,
                rooms,
            )
        return self._zones[hub_id]

    async def _broadcast_to_zone(self, zone: "_ZoneInstance", msg_type: str, payload: dict) -> None:
        """Send a message to every player currently in zone."""
        async with self.session._lock:
            writers = [
                (p.player_id, p.writer)
                for p in self.session.players.values()
                if p.hub_id == zone.hub_id
            ]
        if not writers:
            return
        encoded = encode_message(msg_type, payload)

        async def _send_one(pid: str, w: asyncio.StreamWriter) -> None:
            try:
                await write_encoded(w, encoded)
            except Exception as exc:
                log.debug("Zone broadcast to %s failed: %s", pid, exc)

        await asyncio.gather(*(_send_one(pid, w) for pid, w in writers))

    async def _handle_portal_travel(
        self, player: ConnectedPlayer, destination_id: str, portal_id: str
    ) -> None:
        """
        Move a player from their current zone to destination_id.

        Steps:
          1. Remove player from old zone membership.
          2. Get/create destination zone; init simulator if this is its first arrival.
          3. Update player.hub_id and add to new zone membership.
          4. Send WORLD_TRANSITION to the travelling player only.
          5. Notify old zone occupants of departure.
          6. Notify new zone occupants of arrival.
        """
        old_hub_id = player.hub_id
        new_hub_id = destination_id

        # 1. Leave old zone
        old_zone = self._zones.get(old_hub_id)
        if old_zone:
            old_zone.player_ids.discard(player.player_id)
            if not old_zone.player_ids:
                old_zone.last_occupied_at = asyncio.get_event_loop().time()

        # 2. Create/initialise destination zone
        new_zone = self._get_or_create_zone(new_hub_id)
        if new_zone.simulator is None and self.session.game_started:
            loop = asyncio.get_event_loop()
            try:
                await loop.run_in_executor(None, lambda: self._init_zone_simulator(new_zone))
            except Exception as exc:
                log.error("[ZONE] Failed to init zone %s: %s", new_hub_id, exc, exc_info=True)
                return
            if new_zone.sim_task is None:
                new_zone.sim_task = asyncio.create_task(self._zone_simulation_loop(new_zone))

        # 3. Join new zone
        player.hub_id = new_hub_id
        new_zone.player_ids.add(player.player_id)

        # 4. Send WORLD_TRANSITION to the travelling player
        try:
            await write_message(
                player.writer,
                MessageType.WORLD_TRANSITION,
                {
                    "hub_id": new_hub_id,
                    "seed": new_zone.seed,
                    "shape": new_zone.shape,
                    "rooms": new_zone.rooms,
                    "world_seed": new_zone.world_seed,
                    "spawn_x": new_zone.spawn_x,
                    "spawn_y": new_zone.spawn_y,
                },
            )
        except Exception as exc:
            log.warning("[ZONE] Could not send WORLD_TRANSITION to %s: %s", player.player_id, exc)

        # 5. Notify old zone occupants
        if old_zone:
            await self._broadcast_to_zone(
                old_zone,
                MessageType.ZONE_PRESENCE,
                {
                    "player_id": player.player_id,
                    "slot": player.slot,
                    "hub_id": old_hub_id,
                    "action": "departed",
                },
            )

        # 6. Notify new zone occupants (including the traveller themselves)
        await self._broadcast_to_zone(
            new_zone,
            MessageType.ZONE_PRESENCE,
            {
                "player_id": player.player_id,
                "slot": player.slot,
                "hub_id": new_hub_id,
                "action": "arrived",
            },
        )

        log.info(
            "[ZONE] Player %s (slot %d) travelled: %s → %s",
            player.player_id,
            player.slot,
            old_hub_id,
            new_hub_id,
        )

    # ── Simulation loop ───────────────────────────────────────────────────────

    async def _zone_simulation_loop(self, zone: "_ZoneInstance") -> None:
        """
        Proactive 60 Hz simulation loop for one zone.

        Collects InputCommands only from players in this zone, advances its
        GameSimulator, then broadcasts a delta-encoded WorldSnapshot to those
        same players. Drift correction keeps the loop tight.
        """
        loop = asyncio.get_event_loop()
        _ticks = 0
        _behind_count = 0

        while not zone.stop_event.is_set() and not self._stop_event.is_set():
            t0 = loop.time()

            if zone.simulator is not None and self.session.game_started:
                # Inputs only from players in this zone
                async with self.session._lock:
                    inputs: dict[int, InputCommand] = {
                        cp.slot: cp.latest_input
                        for cp in self.session.players.values()
                        if cp.hub_id == zone.hub_id and cp.latest_input is not None
                    }

                try:
                    zone.simulator.step(inputs, TICK_INTERVAL)
                    zone.frame += 1
                    _ticks += 1
                except Exception as exc:
                    log.error(
                        "[ZONE:%s] step() error at frame %d: %s",
                        zone.hub_id,
                        zone.frame,
                        exc,
                        exc_info=True,
                    )

                # Broadcast WORLD_STATE at 20 Hz (every BROADCAST_EVERY_N_TICKS).
                # Player movement is client-authoritative (v0.9.11), so broadcast
                # rate no longer affects remote player responsiveness — it only
                # drives the ghost and health sync.  20 Hz is sufficient for both.
                # 60 Hz broadcasts (v0.9.10) were reverted because the extra
                # recv_loop wake-ups created GIL contention on the remote client,
                # slowing their game loop and causing multi-tick physics steps
                # (GameClock accumulator pattern), which produced 2-3× movement
                # exaggeration — the "exaggerated input / no fine control" symptom.
                if _ticks % BROADCAST_EVERY_N_TICKS == 0:
                    try:
                        snap = zone.simulator.get_snapshot(zone.frame)
                        snap_dict = snap.to_dict()
                        snap_dict["hub_id"] = zone.hub_id

                        # Patch anim_state for action states that the server sim
                        # cannot compute (attack_stage, is_dashing, etc. are
                        # managed client-side in demo_game.py).  Use the client's
                        # INPUT-reported anim_state (stored in ConnectedPlayer)
                        # whenever it is a non-movement action state.  Movement
                        # states (idle/walk/run/jump/fall/…) remain server-computed
                        # so they stay accurate to the server-authoritative position.
                        async with self.session._lock:
                            _client_anim: dict[int, str] = {
                                cp.slot: cp.anim_state
                                for cp in self.session.players.values()
                                if cp.hub_id == zone.hub_id
                            }
                        for _ps_dict in snap_dict.get("players", []):
                            _client_state = _client_anim.get(_ps_dict["slot"], "")
                            if _client_state in _ACTION_ANIM_STATES:
                                _ps_dict["anim_state"] = _client_state

                        payload = self._build_world_state_payload(snap_dict, zone)
                        await self._broadcast_to_zone(zone, MessageType.WORLD_STATE, payload)
                    except Exception as exc:
                        log.error(
                            "[ZONE:%s] snapshot/broadcast error: %s",
                            zone.hub_id,
                            exc,
                            exc_info=True,
                        )

                if _ticks % (TICK_RATE * 5) == 0:
                    log.debug(
                        "[ZONE:%s] tick=%d frame=%d  zone_players=%d",
                        zone.hub_id,
                        _ticks,
                        zone.frame,
                        len(zone.player_ids),
                    )

            elapsed = loop.time() - t0
            sleep_for = TICK_INTERVAL - elapsed
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)
            else:
                _behind_count += 1
                if _behind_count % 60 == 0:
                    log.warning(
                        "[ZONE:%s] loop behind by %.1f ms (frame=%d)",
                        zone.hub_id,
                        -sleep_for * 1000,
                        zone.frame,
                    )
                await asyncio.sleep(0)

    async def _reap_idle_zones(self) -> None:
        """Periodically tear down zones that have been empty for IDLE_TTL seconds."""
        IDLE_TTL = 120.0
        while not self._stop_event.is_set():
            await asyncio.sleep(30)
            now = asyncio.get_event_loop().time()
            for hub_id in list(self._zones):
                if hub_id == self._world_hub_id:
                    continue  # never reap the initial hub
                zone = self._zones[hub_id]
                if zone.player_ids:
                    zone.last_occupied_at = now
                    continue
                if now - zone.last_occupied_at > IDLE_TTL:
                    zone.stop_event.set()
                    if zone.sim_task:
                        zone.sim_task.cancel()
                        try:
                            await zone.sim_task
                        except asyncio.CancelledError:
                            pass
                    del self._zones[hub_id]
                    log.info("[ZONE] Reaped idle zone: %s", hub_id)

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle_client, self.host, self.port)
        addrs = [str(s.getsockname()) for s in self._server.sockets]
        log.info(
            "Server listening on %s  seed=%d  max_players=%d",
            addrs,
            self.session.seed,
            self.session.max_players,
        )
        print(f"[NET] Server listening on {self.host}:{self.port}  seed={self.session.seed}")

        # Pre-register the initial zone (no simulator yet — started on first GAME_START)
        self._get_or_create_zone(self._world_hub_id)
        self._reap_task = asyncio.create_task(self._reap_idle_zones())
        # Keep _sim_task as a backward-compat alias for the initial zone task
        self._sim_task = None

    async def stop(self) -> None:
        self._stop_event.set()
        # Cancel reaper
        if self._reap_task:
            self._reap_task.cancel()
            try:
                await self._reap_task
            except asyncio.CancelledError:
                pass
        # Cancel all zone simulation tasks
        for zone in list(self._zones.values()):
            zone.stop_event.set()
            if zone.sim_task:
                zone.sim_task.cancel()
                try:
                    await zone.sim_task
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
        # Disable Nagle's algorithm so small INPUT packets are sent immediately
        # rather than being buffered for up to 40ms waiting for ACK / MSS.
        _sock = writer.transport.get_extra_info("socket")
        if _sock is not None:
            try:
                _sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except OSError:
                pass
        log.info("Incoming connection from %s", addr)

        if self.session.is_full:
            mp = self.session.max_players
            log.warning("Rejecting %s — session full (%d/%d)", addr, mp, mp)
            await write_message(
                writer,
                MessageType.ERROR,
                {
                    "code": "session_full",
                    "message": f"Server is full (max {mp} players).",
                },
            )
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
            await write_message(
                writer,
                MessageType.ERROR,
                {
                    "code": "expected_hello",
                    "message": "Expected client_hello as first message.",
                },
            )
            writer.close()
            return

        client_version = hello.payload.get("version", "")
        log.debug(
            "CLIENT_HELLO from %s: id=%s version=%s",
            addr,
            hello.payload.get("player_id", "?"),
            client_version,
        )
        if client_version != SERVER_VERSION:
            log.warning(
                "Version mismatch from %s: client=%s server=%s (continuing — Phase 1 lenient)",
                addr,
                client_version,
                SERVER_VERSION,
            )

        player_id = hello.payload.get("player_id") or str(uuid.uuid4())[:8]
        slot = self.session.next_slot()
        player = ConnectedPlayer(
            player_id=player_id,
            slot=slot,
            reader=reader,
            writer=writer,
            hub_id=self._world_hub_id,
        )

        if not await self.session.add_player(player):
            await write_message(
                writer,
                MessageType.ERROR,
                {
                    "code": "session_full",
                    "message": "Session filled up between check and join.",
                },
            )
            writer.close()
            return

        # Register player in the initial zone
        initial_zone = self._zones.get(self._world_hub_id)
        if initial_zone is not None:
            initial_zone.player_ids.add(player_id)

        # Send server hello
        await write_message(
            writer,
            MessageType.SERVER_HELLO,
            {
                "player_id": player_id,
                "slot": slot,
                "frame": self.session.frame,
                "seed": self.session.seed,
                "max_players": self.session.max_players,
            },
        )

        # Notify other players and broadcast updated lobby state
        await self.session.broadcast(
            MessageType.PLAYER_JOIN,
            {
                "player_id": player_id,
                "slot": slot,
            },
        )
        await self.session.broadcast_lobby_update()

        # Auto-start when lobby is full
        if not self.session.game_started and self.session.is_full:
            await self.session.start_game(server=self)

        log.info(
            "SERVER_HELLO sent to %s: id=%s slot=%d seed=%d",
            addr,
            player_id,
            slot,
            self.session.seed,
        )

        # Main client loop
        try:
            await self._client_loop(player)
        except (asyncio.IncompleteReadError, ConnectionResetError):
            log.info("Client %s (slot %d) disconnected from %s", player_id, slot, addr)
        except Exception as exc:
            log.error("Client loop error for %s (slot %d): %s", player_id, slot, exc, exc_info=True)
        finally:
            # Remove from zone membership before session cleanup
            zone = self._zones.get(player.hub_id)
            if zone:
                zone.player_ids.discard(player_id)
                if not zone.player_ids:
                    zone.last_occupied_at = asyncio.get_event_loop().time()
                # Notify remaining zone occupants of departure
                await self._broadcast_to_zone(
                    zone,
                    MessageType.ZONE_PRESENCE,
                    {
                        "player_id": player_id,
                        "slot": slot,
                        "hub_id": player.hub_id,
                        "action": "departed",
                    },
                )
            await self.session.remove_player(player_id)
            await self.session.broadcast(
                MessageType.PLAYER_LEAVE,
                {
                    "player_id": player_id,
                    "slot": slot,
                },
            )
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
                if _inputs_processed % 300 == 0:  # ~5 s at 60 Hz
                    log.debug(
                        "Input: %d processed for %s  server_frame=%d",
                        _inputs_processed,
                        player.player_id,
                        self.session.frame,
                    )

                # Phase 1/2.5 fallback: broadcast a MultiplayerSnapshot only
                # when the authoritative simulator is not yet running.
                if self._simulator is None:
                    self.session.frame += 1
                    snapshot = self.session.build_snapshot()
                    await self.session.broadcast(MessageType.SERVER_STATE, snapshot.to_dict())

            elif msg.type == MessageType.ENTITY_EVENT:
                # Phase 2.5: relay world-state mutation to all other clients so
                # each simulation applies the same pickup/kill/trigger event.
                # This becomes a no-op once Phase 3 WorldSnapshot is authoritative.
                etype = msg.payload.get("etype", "?")
                eid = msg.payload.get("entity_id", "?")
                log.debug(
                    "ENTITY_EVENT from %s (slot %d): etype=%s entity_id=%s",
                    player.player_id,
                    player.slot,
                    etype,
                    eid,
                )
                if self._simulator is None:
                    # Only relay during Phase 2.5 — WorldSnapshot covers this in Phase 3
                    payload_with_source = dict(msg.payload)
                    payload_with_source.setdefault("slot", player.slot)
                    await self.session.broadcast(MessageType.ENTITY_EVENT, payload_with_source)

            elif msg.type == MessageType.PORTAL_TRAVEL:
                # Phase 4: player used a portal — move them to the destination zone.
                destination_id = msg.payload.get("destination_id", "")
                portal_id = msg.payload.get("portal_id", "")
                if destination_id:
                    await self._handle_portal_travel(player, destination_id, portal_id)
                else:
                    log.warning("PORTAL_TRAVEL from %s missing destination_id", player.player_id)

            else:
                log.debug(
                    "Unexpected message type '%s' from %s (slot %d)",
                    msg.type,
                    player.player_id,
                    player.slot,
                )


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
    world_seed: int = 0,
) -> None:
    """
    Start the game server and run until cancelled.
    Intended to be called via asyncio.run() in a daemon thread.
    """
    server = GameServer(
        host=host,
        port=port,
        seed=seed,
        max_players=max_players,
        world_shape=world_shape,
        world_rooms=world_rooms,
        world_hub_id=world_hub_id,
        world_seed=world_seed,
    )
    await server.start()
    await server.serve_forever()
