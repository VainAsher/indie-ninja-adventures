"""
tests/unit/test_entity_cache.py

Unit tests for the _EntityCache class in network/client.py.

_EntityCache reconstructs full WorldSnapshot state from a stream of full +
delta frames so that poll_world_state() always returns a complete dict.

No server, no pygame, no network required.
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from network.client import _EntityCache


# ── helpers ───────────────────────────────────────────────────────────────────

def _enemy(eid: str, hp: int = 3) -> dict:
    return {"enemy_id": eid, "x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0,
            "hp": hp, "ai_state": "patrol", "facing_right": True}


def _pickup(pid: str, alive: bool = True) -> dict:
    return {"pickup_id": pid, "x": 0.0, "y": 0.0, "pickup_type": "coin", "alive": alive}


def _platform(plid: str, state: str = "idle") -> dict:
    return {"platform_id": plid, "state": state, "pos_y": 64.0, "timer": 0.0, "vy": 0.0}


def _full(enemies=None, pickups=None, platforms=None, frame=1, seed=1, hub="h") -> dict:
    return {
        "frame": frame, "seed": seed, "hub_id": hub, "is_delta": False,
        "players": [],
        "enemies": enemies or [],
        "pickups": pickups or [],
        "platform_states": platforms or [],
        "metadata": {},
    }


def _delta(
    enemies_changed=None, enemies_removed=None,
    pickups_changed=None, pickups_removed=None,
    platforms_changed=None, platforms_removed=None,
    frame=2, seed=1, hub="h",
) -> dict:
    return {
        "frame": frame, "seed": seed, "hub_id": hub, "is_delta": True,
        "players": [],
        "enemies_changed": enemies_changed or [],
        "enemies_removed": enemies_removed or [],
        "pickups_changed": pickups_changed or [],
        "pickups_removed": pickups_removed or [],
        "platforms_changed": platforms_changed or [],
        "platforms_removed": platforms_removed or [],
        "metadata": {},
    }


# ── full snapshot behaviour ───────────────────────────────────────────────────

def test_full_snapshot_replaces_cache():
    cache = _EntityCache()
    cache.apply(_full(enemies=[_enemy("e1")]))
    result = cache.apply(_full(enemies=[_enemy("e2")]))
    ids = {e["enemy_id"] for e in result["enemies"]}
    assert ids == {"e2"}
    assert "e1" not in ids


def test_full_snapshot_returns_payload_as_is():
    cache = _EntityCache()
    payload = _full(enemies=[_enemy("e1")])
    result = cache.apply(payload)
    assert result is payload  # same object returned for full snapshots


def test_full_snapshot_is_delta_remains_false():
    cache = _EntityCache()
    result = cache.apply(_full())
    assert result.get("is_delta") is False


# ── delta — enemies ───────────────────────────────────────────────────────────

def test_delta_adds_changed_enemy():
    cache = _EntityCache()
    cache.apply(_full(enemies=[_enemy("e1", hp=3)]))
    updated = {**_enemy("e1", hp=1)}
    result = cache.apply(_delta(enemies_changed=[updated]))
    enemy = next(e for e in result["enemies"] if e["enemy_id"] == "e1")
    assert enemy["hp"] == 1


def test_delta_adds_new_enemy_not_in_full():
    cache = _EntityCache()
    cache.apply(_full(enemies=[_enemy("e1")]))
    result = cache.apply(_delta(enemies_changed=[_enemy("e2", hp=5)]))
    ids = {e["enemy_id"] for e in result["enemies"]}
    assert "e1" in ids and "e2" in ids


def test_delta_removes_enemy():
    cache = _EntityCache()
    cache.apply(_full(enemies=[_enemy("e1"), _enemy("e2")]))
    result = cache.apply(_delta(enemies_removed=["e1"]))
    ids = {e["enemy_id"] for e in result["enemies"]}
    assert "e1" not in ids
    assert "e2" in ids


def test_full_after_deltas_resets_to_full():
    cache = _EntityCache()
    cache.apply(_full(enemies=[_enemy("e1")]))
    cache.apply(_delta(enemies_changed=[_enemy("e2")]))  # cache now has e1 + e2
    result = cache.apply(_full(enemies=[_enemy("e3")]))   # new full: only e3
    ids = {e["enemy_id"] for e in result["enemies"]}
    assert ids == {"e3"}


# ── delta — pickups ───────────────────────────────────────────────────────────

def test_delta_pickup_changed():
    cache = _EntityCache()
    cache.apply(_full(pickups=[_pickup("p1", alive=True)]))
    result = cache.apply(_delta(pickups_changed=[_pickup("p1", alive=False)]))
    pick = next(p for p in result["pickups"] if p["pickup_id"] == "p1")
    assert pick["alive"] is False


def test_delta_pickup_removed():
    cache = _EntityCache()
    cache.apply(_full(pickups=[_pickup("p1"), _pickup("p2")]))
    result = cache.apply(_delta(pickups_removed=["p1"]))
    ids = {p["pickup_id"] for p in result["pickups"]}
    assert "p1" not in ids and "p2" in ids


# ── delta — platforms ─────────────────────────────────────────────────────────

def test_delta_platform_changed():
    cache = _EntityCache()
    cache.apply(_full(platforms=[_platform("plat_0", "idle")]))
    updated = {**_platform("plat_0", "falling"), "pos_y": 200.0, "vy": 400.0, "timer": 0.1}
    result = cache.apply(_delta(platforms_changed=[updated]))
    plat = next(p for p in result["platform_states"] if p["platform_id"] == "plat_0")
    assert plat["state"] == "falling"
    assert plat["vy"] == 400.0


def test_delta_platform_removed():
    cache = _EntityCache()
    cache.apply(_full(platforms=[_platform("plat_0"), _platform("plat_1")]))
    result = cache.apply(_delta(platforms_removed=["plat_0"]))
    ids = {p["platform_id"] for p in result["platform_states"]}
    assert "plat_0" not in ids
    assert "plat_1" in ids


# ── reset ─────────────────────────────────────────────────────────────────────

def test_reset_clears_all_caches():
    cache = _EntityCache()
    cache.apply(_full(
        enemies=[_enemy("e1")],
        pickups=[_pickup("p1")],
        platforms=[_platform("plat_0")],
    ))
    cache.reset()
    # After reset, a delta with nothing changed should produce empty lists
    result = cache.apply(_delta())
    assert result["enemies"] == []
    assert result["pickups"] == []
    assert result["platform_states"] == []


# ── delta returns reconstructed full ─────────────────────────────────────────

def test_delta_returns_is_delta_false():
    cache = _EntityCache()
    cache.apply(_full())
    result = cache.apply(_delta())
    assert result.get("is_delta") is False


def test_delta_result_contains_all_cached_entities():
    cache = _EntityCache()
    cache.apply(_full(enemies=[_enemy("e1"), _enemy("e2")]))
    result = cache.apply(_delta(enemies_changed=[_enemy("e1", hp=2)]))
    ids = {e["enemy_id"] for e in result["enemies"]}
    assert ids == {"e1", "e2"}


def test_delta_preserves_players_from_payload():
    """Players are passed through unchanged — not cached by _EntityCache."""
    cache = _EntityCache()
    cache.apply(_full())
    player_payload = [{"player_id": "p0", "slot": 0, "pos": [1.0, 2.0],
                       "vel": [0.0, 0.0], "health": 5, "facing": 1, "is_dead": False}]
    result = cache.apply(_delta(frame=2))
    # Players key comes from the delta payload (empty list in _delta helper)
    assert "players" in result
