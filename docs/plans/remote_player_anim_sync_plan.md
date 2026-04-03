# Plan: Remote Player Animation Sync & Responsiveness Fix

**Branch:** fix/remote-player-anim-sync
**Target tag:** v0.9.14
**Status:** COMPLETE

## Problem Summary

Remote player ghosts suffer two linked issues:
1. **Animation out of sync** — `_infer_anim_state()` derives animation from velocity only, producing
   at most 6 states. The 20 states that require flags (dash, attack, hurt, crouch, wall_hang,
   teleport, ninjutsu, throw, slash, etc.) are invisible to observers.
2. **Ghost position stutter** — `interpolated_pos()` defaults to `tick_ms=16.67` (60 Hz) but the
   server broadcasts at 20 Hz (50 ms). Ghost snaps to new position in 16 ms then freezes for 33 ms
   before the next update.

## Root Causes (confirmed)

| # | File | Line(s) | Issue |
|---|---|---|---|
| RC1 | `network/snapshots.py` | 46-79 | `PlayerState` has no `anim_state` field |
| RC2 | `game/game_simulator.py` | 207-225 | `get_snapshot()` computes pos/vel/health only — discards full player state |
| RC3 | `entities/remote_player.py` | 85-105 | `_infer_anim_state()` velocity-only heuristic; 20 states never reachable |
| RC4 | `entities/remote_player.py` | 107-119 | `interpolated_pos()` hardcoded `tick_ms=16.67`; actual broadcast = 50 ms |
| RC5 | `demo_game.py` | 1941, 2009 | `apply_state()` calls never pass animation state |

## Fix Phases

### Phase 1 — Protocol: add `anim_state` to `PlayerState` ✅ DONE
- Add `anim_state: str = ""` field to `PlayerState` in `network/snapshots.py`
- Update `to_dict()` and `from_dict()` to serialize/deserialize it
- Backward-compatible: empty string = "use inference" for old servers

### Phase 2 — Shared animation resolver ✅ DONE
- Extract `get_player_render_state()` from `demo_game.py` into `entities/player_render_state.py`
- Import it back into `demo_game.py` (no logic change for local player)
- Import it into `game/game_simulator.py` and call it in `get_snapshot()`

### Phase 3 — Phase 1/2.5 relay path ✅ DONE
- Add `anim_state` to `send_input()` payload in `network/client.py`
- Store it in `ConnectedPlayer` in `network/server.py`
- Include it in `build_snapshot()` in `network/server.py`

### Phase 4 — RemotePlayer: use anim_state + adaptive interpolation ✅ DONE
- Accept `anim_state` param in `apply_state()`, use it when non-empty
- Track actual inter-update interval for adaptive `interpolated_pos()`
- Guard non-looping animations against premature interruption

### Phase 5 — Wire demo_game.py call sites ✅ DONE
- Pass `anim_state=_ps.anim_state` at both `apply_state()` calls (lines 1941, 2009)

### Phase 6 — Tag and release ✅ DONE
- Bump version to 0.9.14
- Tag v0.9.14, push branch + tag

## Decisions Made

- `anim_state` defaults to `""` in protocol for backward-compat with older servers/clients
- `_infer_anim_state()` kept as fallback when `anim_state` is empty
- `interpolated_pos()` now self-calibrates using tracked inter-update interval (no hardcoded constant)
- Non-looping animation guard uses `anim_sm.finished` — doesn't interrupt attacks/hurt mid-play
- `compute_anim_state()` lives in new module `entities/player_render_state.py` to avoid circular imports
  (demo_game.py → entities, game_simulator.py → entities; both safe)
