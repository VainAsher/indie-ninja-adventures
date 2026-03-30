"""
tests/unit/test_network_snapshots.py

Unit tests for network/snapshots.py — round-trip serialisation of every
dataclass (Snapshot, PlayerState, MultiplayerSnapshot, EnemyState,
PickupState, PlatformState, WorldSnapshot) and edge-case defaults.

Pure data: no pygame, no network, no server.
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from network.snapshots import (
    EnemyState,
    MultiplayerSnapshot,
    PickupState,
    PlatformState,
    PlayerState,
    Snapshot,
    WorldSnapshot,
)


# ── Snapshot (single-player replay) ──────────────────────────────────────────

def test_snapshot_roundtrip():
    snap = Snapshot(
        frame=10,
        seed=42,
        player_pos=(1.5, 2.5),
        player_vel=(-0.5, 3.0),
        metadata={"key": "value"},
    )
    d = snap.to_dict()
    recovered = Snapshot.from_dict(d)
    assert recovered.frame == 10
    assert recovered.seed == 42
    assert recovered.player_pos == (1.5, 2.5)
    assert recovered.player_vel == (-0.5, 3.0)
    assert recovered.metadata == {"key": "value"}


def test_snapshot_to_dict_key_order():
    snap = Snapshot(frame=1, seed=2, player_pos=(0, 0), player_vel=(0, 0), metadata={})
    keys = list(snap.to_dict().keys())
    assert keys == ["frame", "seed", "player_pos", "player_vel", "metadata"]


def test_snapshot_from_dict_missing_metadata_defaults_to_empty():
    d = {"frame": 5, "seed": 7, "player_pos": [0.0, 0.0], "player_vel": [0.0, 0.0]}
    snap = Snapshot.from_dict(d)
    assert snap.metadata == {}


# ── PlayerState ───────────────────────────────────────────────────────────────

def test_player_state_roundtrip_full():
    ps = PlayerState(
        player_id="p42",
        slot=1,
        pos=(10.0, 20.0),
        vel=(-1.0, 0.5),
        health=3,
        facing=-1,
        is_dead=True,
    )
    d = ps.to_dict()
    recovered = PlayerState.from_dict(d)
    assert recovered.player_id == "p42"
    assert recovered.slot == 1
    assert recovered.pos == (10.0, 20.0)
    assert recovered.vel == (-1.0, 0.5)
    assert recovered.health == 3
    assert recovered.facing == -1
    assert recovered.is_dead is True


def test_player_state_from_dict_defaults():
    # Minimal dict: missing facing and is_dead should use defaults
    d = {
        "player_id": "x",
        "slot": 0,
        "pos": [0.0, 0.0],
        "vel": [0.0, 0.0],
        "health": 5,
    }
    ps = PlayerState.from_dict(d)
    assert ps.facing == 1
    assert ps.is_dead is False


def test_player_state_pos_vel_are_tuples():
    ps = PlayerState(
        player_id="t", slot=0, pos=(1.0, 2.0), vel=(3.0, 4.0), health=5, facing=1
    )
    d = ps.to_dict()
    recovered = PlayerState.from_dict(d)
    assert isinstance(recovered.pos, tuple)
    assert isinstance(recovered.vel, tuple)


# ── MultiplayerSnapshot ───────────────────────────────────────────────────────

def test_multiplayer_snapshot_roundtrip_two_players():
    ps0 = PlayerState("h", 0, (0.0, 0.0), (0.0, 0.0), 5, facing=1)
    ps1 = PlayerState("j", 1, (100.0, 50.0), (1.0, 0.0), 4, facing=-1)
    snap = MultiplayerSnapshot(frame=5, seed=99, players=[ps0, ps1], metadata={})
    d = snap.to_dict()
    recovered = MultiplayerSnapshot.from_dict(d)
    assert recovered.frame == 5
    assert recovered.seed == 99
    assert len(recovered.players) == 2
    assert recovered.players[1].pos == (100.0, 50.0)
    assert recovered.players[1].facing == -1


def test_multiplayer_snapshot_empty_players():
    snap = MultiplayerSnapshot(frame=0, seed=1, players=[], metadata={})
    recovered = MultiplayerSnapshot.from_dict(snap.to_dict())
    assert recovered.players == []


# ── EnemyState ────────────────────────────────────────────────────────────────

def test_enemy_state_roundtrip():
    es = EnemyState(
        enemy_id="goblin_0",
        x=200.0, y=300.0,
        vx=1.5, vy=0.0,
        hp=3,
        ai_state="chase",
        facing_right=False,
    )
    recovered = EnemyState.from_dict(es.to_dict())
    assert recovered.enemy_id == "goblin_0"
    assert recovered.x == 200.0
    assert recovered.hp == 3
    assert recovered.ai_state == "chase"
    assert recovered.facing_right is False


def test_enemy_state_dead():
    es = EnemyState("e", 0.0, 0.0, 0.0, 0.0, hp=0, ai_state="dead", facing_right=True)
    recovered = EnemyState.from_dict(es.to_dict())
    assert recovered.hp == 0
    assert recovered.ai_state == "dead"


# ── PickupState ───────────────────────────────────────────────────────────────

def test_pickup_state_roundtrip():
    ps = PickupState(pickup_id="coin_1", x=50.0, y=80.0, pickup_type="coin", alive=True)
    recovered = PickupState.from_dict(ps.to_dict())
    assert recovered.pickup_id == "coin_1"
    assert recovered.x == 50.0
    assert recovered.pickup_type == "coin"
    assert recovered.alive is True


def test_pickup_state_not_alive():
    ps = PickupState("hp_5", 0.0, 0.0, "health", alive=False)
    recovered = PickupState.from_dict(ps.to_dict())
    assert recovered.alive is False


# ── PlatformState ─────────────────────────────────────────────────────────────

def test_platform_state_roundtrip():
    pls = PlatformState(
        platform_id="plat_32_64",
        state="falling",
        pos_y=128.5,
        timer=0.12,
        vy=250.0,
    )
    recovered = PlatformState.from_dict(pls.to_dict())
    assert recovered.platform_id == "plat_32_64"
    assert recovered.state == "falling"
    assert recovered.pos_y == 128.5
    assert recovered.timer == 0.12
    assert recovered.vy == 250.0


def test_platform_state_idle():
    pls = PlatformState("p", "idle", 64.0, 0.0, 0.0)
    recovered = PlatformState.from_dict(pls.to_dict())
    assert recovered.state == "idle"
    assert recovered.vy == 0.0


# ── WorldSnapshot ─────────────────────────────────────────────────────────────

def _make_world_snapshot() -> WorldSnapshot:
    players = [
        PlayerState("h", 0, (10.0, 20.0), (0.0, 0.0), 5, facing=1),
        PlayerState("j", 1, (50.0, 20.0), (1.0, 0.0), 4, facing=1),
    ]
    enemies = [
        EnemyState("goblin_0", 100.0, 200.0, 0.0, 0.0, 3, "patrol", True),
    ]
    pickups = [
        PickupState("coin_0", 120.0, 200.0, "coin", True),
    ]
    platforms = [
        PlatformState("plat_32_64", "idle", 64.0, 0.0, 0.0),
    ]
    return WorldSnapshot(
        frame=99,
        seed=12345,
        players=players,
        enemies=enemies,
        pickups=pickups,
        platform_states=platforms,
        metadata={"tick": 99},
        hub_id="forest_hub",
    )


def test_world_snapshot_roundtrip():
    ws = _make_world_snapshot()
    d = ws.to_dict()
    recovered = WorldSnapshot.from_dict(d)

    assert recovered.frame == 99
    assert recovered.seed == 12345
    assert recovered.hub_id == "forest_hub"
    assert len(recovered.players) == 2
    assert len(recovered.enemies) == 1
    assert len(recovered.pickups) == 1
    assert len(recovered.platform_states) == 1
    assert recovered.enemies[0].enemy_id == "goblin_0"
    assert recovered.pickups[0].pickup_type == "coin"
    assert recovered.platform_states[0].state == "idle"


def test_world_snapshot_empty_lists_when_keys_absent():
    d = {"frame": 0, "seed": 1, "players": [], "metadata": {}}
    recovered = WorldSnapshot.from_dict(d)
    assert recovered.enemies == []
    assert recovered.pickups == []
    assert recovered.platform_states == []


def test_world_snapshot_hub_id_defaults_to_empty_string():
    d = {"frame": 0, "seed": 1, "players": [], "metadata": {}}
    recovered = WorldSnapshot.from_dict(d)
    assert recovered.hub_id == ""


def test_world_snapshot_hub_id_preserved():
    ws = _make_world_snapshot()
    recovered = WorldSnapshot.from_dict(ws.to_dict())
    assert recovered.hub_id == "forest_hub"


def test_world_snapshot_player_health_preserved():
    ws = _make_world_snapshot()
    recovered = WorldSnapshot.from_dict(ws.to_dict())
    assert recovered.players[0].health == 5
    assert recovered.players[1].health == 4
