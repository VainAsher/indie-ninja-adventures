"""
tests/integration/test_network_multiplayer.py

Integration regression tests for the multiplayer sync pipeline:

  GameSimulator.get_snapshot()  →  WorldSnapshot.to_dict()  →  _EntityCache.apply()

Tests verify that the data visible to demo_game.py (after delta reconstruction)
is coherent with the server simulation state — covering the scenarios that
caused regressions in v0.9.0–v0.9.2:

  * Player visibility (both slots appear in every snapshot)
  * Remote player health sync (Phase 3b)
  * Enemy state propagation
  * _EntityCache full + delta reconstruction end-to-end

No running server, no pygame display, no network I/O.
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pygame

pygame.init()

from core import EventBus, GameClock, GameLogger
from game.game_simulator import GameSimulator
from game.health_system import HealthState
from network.client import _EntityCache
from network.snapshots import WorldSnapshot, EnemyState, PickupState

# ── shared stubs (mirrored from test_game_simulator.py — no conftest needed) ──


class _FakePhysics:
    def __init__(self, x=0.0, y=0.0):
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.width, self.height = 28, 56
        self.on_ground = True


class _FakeHealthState:
    def __init__(self, hp: int = 5):
        self.current_hp = hp
        self.max_hp = hp
        self.invincibility_frames = 0

    def take_damage(self, damage: int, defense: int = 0) -> bool:
        effective = max(1, damage - defense)
        self.current_hp = max(0, self.current_hp - effective)
        return self.current_hp == 0

    def is_invincible(self) -> bool:
        return self.invincibility_frames > 0


class _FakePlayerState:
    def __init__(self, slot, hp=5):
        self.player_id = slot
        self.physics = _FakePhysics()
        self.health_state = _FakeHealthState(hp)
        self.facing = 1
        self.is_dashing = False


class _FakePlayer:
    def __init__(self, slot, hp=5):
        self.player_id = slot
        self.state = _FakePlayerState(slot, hp)

    def process_input(self, _k):
        pass


class _FakeEnemyManager:
    def __init__(self, enemies=None):
        self.enemies = enemies or {}

    def update(self, **kw):
        pass

    def check_arrow_player_collision(self, *a, **kw):
        pass


class _FakePickupManager:
    def update(self, dt):
        pass

    def get_alive_pickups(self):
        return []

    def check_collections(self, *a, **kw):
        pass


def _make_sim(players=None, enemy_manager=None, combat_mechanics=None):
    if players is None:
        players = {0: _FakePlayer(0)}
    bus = EventBus()
    logger = GameLogger()
    clock = GameClock(bus, logger=logger.get_logger("clock"))
    return GameSimulator(
        bus=bus,
        game_clock=clock,
        collision_system=MagicMock(),
        players=players,
        enemy_manager=enemy_manager or _FakeEnemyManager(),
        pickup_manager=_FakePickupManager(),
        hazard_manager=MagicMock(),
        dynamic_platforms=[],
        static_platforms=[],
        megamap=None,
        seed=1,
        handle_platforms=False,
        combat_mechanics=combat_mechanics,
    )


# ── player visibility ─────────────────────────────────────────────────────────


def test_single_player_appears_in_snapshot():
    sim = _make_sim()
    snap = sim.get_snapshot(1)
    assert len(snap.players) == 1
    assert snap.players[0].slot == 0


def test_two_players_both_visible_in_snapshot():
    players = {0: _FakePlayer(0), 1: _FakePlayer(1)}
    sim = _make_sim(players=players)
    snap = sim.get_snapshot(1)
    assert len(snap.players) == 2
    slots = {p.slot for p in snap.players}
    assert slots == {0, 1}


def test_dead_player_flagged_is_dead():
    dead = _FakePlayer(0, hp=0)
    sim = _make_sim(players={0: dead})
    snap = sim.get_snapshot(1)
    assert snap.players[0].is_dead is True


def test_alive_player_not_flagged_dead():
    sim = _make_sim()
    snap = sim.get_snapshot(1)
    assert snap.players[0].is_dead is False


# ── Phase 3b: health sync ─────────────────────────────────────────────────────


def test_player_health_in_snapshot_matches_state():
    p = _FakePlayer(0)
    p.state.health_state.current_hp = 3
    sim = _make_sim(players={0: p})
    snap = sim.get_snapshot(1)
    assert snap.players[0].health == 3


def test_combat_damage_propagates_to_snapshot():
    """Phase 3b regression: damage applied in step() is visible in snapshot."""
    mock_cm = MagicMock()
    mock_cm.check_enemy_collisions.return_value = 2  # 2 HP damage
    sim = _make_sim(combat_mechanics={0: mock_cm})
    sim.step({}, 1 / 60)
    snap = sim.get_snapshot(1)
    assert snap.players[0].health == 3  # 5 − 2


def test_no_combat_mechanics_health_unchanged_after_step():
    sim = _make_sim(combat_mechanics=None)
    sim.step({}, 1 / 60)
    snap = sim.get_snapshot(1)
    assert snap.players[0].health == 5


# ── enemy state in snapshot ───────────────────────────────────────────────────


def test_enemy_state_reflected_in_snapshot():
    """Enemies present in EnemyManager appear in the WorldSnapshot."""
    from game.game_simulator import GameSimulator

    class _EnemyWithState:
        def __init__(self):
            class _Phys:
                x, y, vx, vy = 200.0, 300.0, 0.0, 0.0

            class _Health:
                current_hp = 3

            class _AIState:
                value = "patrol"

            self.physics = _Phys()
            self.health_state = _Health()
            self.ai_state = _AIState()
            self.facing_right = True

    em = _FakeEnemyManager(enemies={"goblin_0": _EnemyWithState()})
    sim = _make_sim(enemy_manager=em)
    snap = sim.get_snapshot(1)
    assert len(snap.enemies) == 1
    assert snap.enemies[0].enemy_id == "goblin_0"
    assert snap.enemies[0].x == 200.0
    assert snap.enemies[0].hp == 3


# ── _EntityCache full + delta end-to-end ──────────────────────────────────────


def _ws_dict(enemies=None, pickups=None, frame=1, hub="test") -> dict:
    """Build a WorldSnapshot dict as the server would broadcast."""
    players = [
        {
            "player_id": "0",
            "slot": 0,
            "pos": [10.0, 20.0],
            "vel": [0.0, 0.0],
            "health": 5,
            "facing": 1,
            "is_dead": False,
        },
        {
            "player_id": "1",
            "slot": 1,
            "pos": [50.0, 20.0],
            "vel": [0.0, 0.0],
            "health": 5,
            "facing": 1,
            "is_dead": False,
        },
    ]
    return {
        "frame": frame,
        "seed": 1,
        "hub_id": hub,
        "is_delta": False,
        "players": players,
        "enemies": enemies or [],
        "pickups": pickups or [],
        "platform_states": [],
        "metadata": {},
    }


def test_entity_cache_reconstructs_full_state():
    cache = _EntityCache()
    enemies = [
        {
            "enemy_id": "e0",
            "x": 0.0,
            "y": 0.0,
            "vx": 0.0,
            "vy": 0.0,
            "hp": 3,
            "ai_state": "patrol",
            "facing_right": True,
        },
    ]
    result = cache.apply(_ws_dict(enemies=enemies))
    ws = WorldSnapshot.from_dict(result)
    assert len(ws.enemies) == 1
    assert ws.enemies[0].enemy_id == "e0"


def test_entity_cache_delta_enemy_update_reflected():
    cache = _EntityCache()
    enemies = [
        {
            "enemy_id": "e0",
            "x": 0.0,
            "y": 0.0,
            "vx": 0.0,
            "vy": 0.0,
            "hp": 3,
            "ai_state": "patrol",
            "facing_right": True,
        },
    ]
    cache.apply(_ws_dict(enemies=enemies, frame=1))

    # Send a delta reducing e0 HP to 1
    delta = {
        "frame": 2,
        "seed": 1,
        "hub_id": "test",
        "is_delta": True,
        "players": [],
        "enemies_changed": [
            {
                "enemy_id": "e0",
                "x": 0.0,
                "y": 0.0,
                "vx": 0.0,
                "vy": 0.0,
                "hp": 1,
                "ai_state": "chase",
                "facing_right": True,
            },
        ],
        "enemies_removed": [],
        "pickups_changed": [],
        "pickups_removed": [],
        "platforms_changed": [],
        "platforms_removed": [],
        "metadata": {},
    }
    result = cache.apply(delta)
    ws = WorldSnapshot.from_dict(result)
    assert ws.enemies[0].hp == 1
    assert ws.enemies[0].ai_state == "chase"


def test_entity_cache_delta_enemy_removal():
    cache = _EntityCache()
    enemies = [
        {
            "enemy_id": "e0",
            "x": 0.0,
            "y": 0.0,
            "vx": 0.0,
            "vy": 0.0,
            "hp": 3,
            "ai_state": "patrol",
            "facing_right": True,
        },
        {
            "enemy_id": "e1",
            "x": 100.0,
            "y": 0.0,
            "vx": 0.0,
            "vy": 0.0,
            "hp": 2,
            "ai_state": "idle",
            "facing_right": False,
        },
    ]
    cache.apply(_ws_dict(enemies=enemies, frame=1))

    delta = {
        "frame": 2,
        "seed": 1,
        "hub_id": "test",
        "is_delta": True,
        "players": [],
        "enemies_changed": [],
        "enemies_removed": ["e0"],  # e0 was killed
        "pickups_changed": [],
        "pickups_removed": [],
        "platforms_changed": [],
        "platforms_removed": [],
        "metadata": {},
    }
    result = cache.apply(delta)
    ws = WorldSnapshot.from_dict(result)
    ids = {e.enemy_id for e in ws.enemies}
    assert "e0" not in ids
    assert "e1" in ids


def test_two_player_slots_both_in_reconstructed_snapshot():
    """Regression: both player slots must survive the cache round-trip."""
    cache = _EntityCache()
    result = cache.apply(_ws_dict(frame=1))
    ws = WorldSnapshot.from_dict(result)
    assert len(ws.players) == 2
    slots = {p.slot for p in ws.players}
    assert slots == {0, 1}


def test_hub_id_preserved_through_cache():
    cache = _EntityCache()
    result = cache.apply(_ws_dict(hub="forest_region", frame=1))
    assert result["hub_id"] == "forest_region"
