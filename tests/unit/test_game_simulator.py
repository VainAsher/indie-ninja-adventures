"""
tests/unit/test_game_simulator.py

Unit tests for game/game_simulator.py — GameSimulator tick stepping,
snapshot generation, and Phase 3b server-side combat integration.

Uses lightweight stubs for Player, EnemyManager and PickupManager so no
world generation or asset loading is required.  pygame is initialised in
headless (dummy driver) mode.
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
from network.snapshots import WorldSnapshot


# ── stubs ─────────────────────────────────────────────────────────────────────

class _FakePhysics:
    def __init__(self, x=100.0, y=100.0):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.width = 28
        self.height = 56
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
    def __init__(self, slot: int, hp: int = 5):
        self.player_id = slot
        self.physics = _FakePhysics()
        self.health_state = _FakeHealthState(hp)
        self.facing = 1
        self.is_dashing = False


class _FakePlayer:
    def __init__(self, slot: int, hp: int = 5):
        self.player_id = slot
        self.state = _FakePlayerState(slot, hp)

    def process_input(self, _keys) -> None:
        pass


class _FakeEnemyManager:
    def __init__(self):
        self.enemies = {}

    def update(self, **kwargs) -> None:
        pass

    def check_arrow_player_collision(self, *args, **kwargs):
        pass


class _FakePickupManager:
    def update(self, dt: float) -> None:
        pass

    def get_alive_pickups(self):
        return []

    def check_collections(self, *args, **kwargs) -> None:
        pass


class _FakeHazardManager:
    pass


def _make_simulator(
    slots: "dict[int, _FakePlayer] | None" = None,
    combat_mechanics=None,
    handle_platforms: bool = False,
) -> GameSimulator:
    """Factory: build a GameSimulator with stub dependencies."""
    if slots is None:
        slots = {0: _FakePlayer(0)}

    core = {
        "bus": EventBus(),
        "logger": GameLogger(),
    }
    game_clock = GameClock(core["bus"], logger=core["logger"].get_logger("clock"))

    return GameSimulator(
        bus=core["bus"],
        game_clock=game_clock,
        collision_system=MagicMock(),
        players=slots,
        enemy_manager=_FakeEnemyManager(),
        pickup_manager=_FakePickupManager(),
        hazard_manager=_FakeHazardManager(),
        dynamic_platforms=[],
        static_platforms=[],
        megamap=None,
        seed=42,
        handle_platforms=handle_platforms,
        combat_mechanics=combat_mechanics,
    )


# ── constructor ───────────────────────────────────────────────────────────────

def test_simulator_combat_mechanics_default_to_empty_dict():
    sim = _make_simulator()
    assert sim.combat_mechanics == {}


def test_simulator_stores_combat_mechanics():
    mock = MagicMock()
    sim = _make_simulator(combat_mechanics={0: mock})
    assert sim.combat_mechanics[0] is mock


# ── step — basic ──────────────────────────────────────────────────────────────

def test_step_advances_without_error():
    sim = _make_simulator()
    sim.step({}, 1 / 60)  # must not raise


def test_step_all_dead_players_returns_early():
    dead = _FakePlayer(0, hp=0)
    sim = _make_simulator(slots={0: dead})
    # Should not raise even when every player is dead (early-return branch)
    sim.step({}, 1 / 60)


# ── get_snapshot ──────────────────────────────────────────────────────────────

def test_get_snapshot_returns_world_snapshot():
    sim = _make_simulator()
    sim.step({}, 1 / 60)
    snap = sim.get_snapshot(1)
    assert isinstance(snap, WorldSnapshot)


def test_get_snapshot_frame_matches_argument():
    sim = _make_simulator()
    snap = sim.get_snapshot(77)
    assert snap.frame == 77


def test_get_snapshot_seed_matches_constructor():
    sim = _make_simulator()
    snap = sim.get_snapshot(1)
    assert snap.seed == 42


def test_get_snapshot_includes_all_player_slots():
    players = {0: _FakePlayer(0), 1: _FakePlayer(1)}
    sim = _make_simulator(slots=players)
    snap = sim.get_snapshot(1)
    assert len(snap.players) == 2
    slots_in_snap = {p.slot for p in snap.players}
    assert slots_in_snap == {0, 1}


def test_get_snapshot_player_health_reflects_state():
    p = _FakePlayer(0)
    p.state.health_state.current_hp = 2
    sim = _make_simulator(slots={0: p})
    snap = sim.get_snapshot(1)
    assert snap.players[0].health == 2


def test_get_snapshot_dead_player_is_dead_true():
    p = _FakePlayer(0, hp=0)
    sim = _make_simulator(slots={0: p})
    snap = sim.get_snapshot(1)
    assert snap.players[0].is_dead is True


# ── Phase 3b: combat mechanics integration ────────────────────────────────────

def test_no_combat_mechanics_leaves_health_unchanged():
    sim = _make_simulator(combat_mechanics=None)
    sim.step({}, 1 / 60)
    assert sim.players[0].state.health_state.current_hp == 5


def test_combat_mechanic_called_for_alive_slot():
    mock_cm = MagicMock()
    mock_cm.check_enemy_collisions.return_value = 0  # no damage this tick
    sim = _make_simulator(combat_mechanics={0: mock_cm})
    sim.step({}, 1 / 60)
    mock_cm.check_enemy_collisions.assert_called_once()


def test_combat_mechanic_damage_reduces_hp():
    mock_cm = MagicMock()
    mock_cm.check_enemy_collisions.return_value = 2  # 2 damage
    sim = _make_simulator(combat_mechanics={0: mock_cm})
    sim.step({}, 1 / 60)
    assert sim.players[0].state.health_state.current_hp == 3  # 5 - 2


def test_combat_mechanic_skipped_for_dead_player():
    dead = _FakePlayer(0, hp=0)
    mock_cm = MagicMock()
    sim = _make_simulator(slots={0: dead}, combat_mechanics={0: mock_cm})
    sim.step({}, 1 / 60)
    mock_cm.check_enemy_collisions.assert_not_called()


def test_combat_mechanic_only_called_for_registered_slots():
    p0 = _FakePlayer(0)
    p1 = _FakePlayer(1)
    mock_cm0 = MagicMock()
    mock_cm0.check_enemy_collisions.return_value = 0
    # slot 1 has no mechanic
    sim = _make_simulator(slots={0: p0, 1: p1}, combat_mechanics={0: mock_cm0})
    sim.step({}, 1 / 60)
    mock_cm0.check_enemy_collisions.assert_called_once()


def test_combat_damage_reflected_in_snapshot():
    """Full chain: damage in step() → snapshot reports reduced HP."""
    mock_cm = MagicMock()
    mock_cm.check_enemy_collisions.return_value = 1
    sim = _make_simulator(combat_mechanics={0: mock_cm})
    sim.step({}, 1 / 60)
    snap = sim.get_snapshot(1)
    assert snap.players[0].health == 4  # 5 - 1
