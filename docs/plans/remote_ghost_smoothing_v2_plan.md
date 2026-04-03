# Plan: Remote Ghost Smoothing + Animation Fixes v2

**Branch:** fix/remote-ghost-smoothing-v2
**Target tag:** v0.9.16
**Status:** COMPLETE

## Problem Summary (post v0.9.15)

Three distinct issues remain after the v0.9.14 anim_state protocol work:

| # | Symptom | Root cause |
|---|---|---|
| 1 | Ghost "teleports" across distances | `interpolated_pos()` clamps t=1.0 → ghost freezes for tail of 50ms window; then jumps accumulated distance |
| 2 | Attack/dash animations not visible on ghost | Server's `compute_anim_state()` always sees `attack_stage=0` (managed client-side in demo_game.py); Phase 3 WorldSnapshot overrides correct client-reported anim_state with wrong server-computed one |
| 3 | Running animation not shown | Pre-v0.9.14: `_infer_anim_state` returned "run" at speed>5.0. Post-v0.9.14: server sends "slow_walk" for all non-ALT movement. `compute_anim_state` requires ALT (`is_running=True`) to return "run" — regression from users' prior expectation |

## Root Cause Detail

### RC1: Ghost freeze/teleport
- Server broadcasts at 20 Hz (50ms). Ghost interpolates prev→x over `update_interval_ms` (EMA ≈ 50ms).
- When `elapsed > expected_ms`, `t = min(1.0, elapsed/expected) = 1.0` → ghost frozen at `x`.
- Jitter causes 10-30ms late packets. Ghost freezes for that gap, then snaps to new position.
- At `vx=8px/frame × 0.6 frames ≈ 5px` of missed movement per update → visible stutter.

### RC2: Attack animations
- `attack_stage` set only in `demo_game.py:2159` via KEYDOWN edge detection.
- Server sim (`game_simulator.py`) has no attack-stage tracking; `p.state.attack_stage` always 0.
- `compute_anim_state(p)` on server: `attack_stage=0` → never returns slash1/2/3.
- Phase 3 WorldSnapshot `anim_state` (server-computed "slow_walk") overrides the client's INPUT-reported `anim_state` ("slash1", "dash", etc.) stored in `ConnectedPlayer.anim_state`.

### RC3: Running animation regression
- `compute_anim_state` path: `if is_running and vx > 0.5 → "run"` else `"slow_walk"`.
- `_infer_anim_state` (old fallback) path: `if speed > 5.0 → "run"`.
- With server-provided anim_state active (v0.9.14), `_infer_anim_state` is bypassed.
- Server correctly sends "slow_walk" per game design (no ALT pressed), but users expect fast-movement = "run".

## Fix Phases

### Phase 1 — Velocity extrapolation in `interpolated_pos()` ✅ DONE
- `entities/remote_player.py`: when `elapsed > update_interval_ms`, extrapolate X using vx
  (px/frame × frames elapsed beyond expected).
- Keep Y at last known position (avoid gravity drift artifacts).
- Cap extrapolation at 3 frames (~50ms) to prevent extreme divergence on long gaps.
- Formula: `extra_frames = (elapsed - expected_ms) / 16.667; ix = x + vx * clamp(extra_frames, 0, 3)`

### Phase 2 — Server WorldSnapshot: trust client anim_state for action states ✅ DONE
- `network/server.py` `_zone_simulation_loop`: after `get_snapshot()`, patch each player's
  `anim_state` in `snap_dict` with the client's INPUT-reported `anim_state` (from
  `ConnectedPlayer.anim_state`) if that state is a non-movement action state.
- Defined `_ACTION_ANIM_STATES`: dash, slash1/2/3, slash_air, throw_*, teleport,
  ninjutsu_*, hurt, hurt2, attack.
- Server remains authoritative for position/health/physics; action animations are
  client-reported (client always knows its own attack stage accurately).

### Phase 3 — Speed-threshold "run" detection in `compute_anim_state()` ✅ DONE
- `entities/player_render_state.py`: restore speed-based "run" detection that was
  previously provided by `_infer_anim_state`.
- `abs(vx) > 5.0 → "run"` (regardless of ALT/is_running), matching the threshold
  used by `_infer_anim_state` for backward visual compatibility.
- Adds "walk" state for moderate speed (0.5–5.0), "slow_walk" only for very slow/stealth.

### Phase 4 — Version bump, tag v0.9.16 ✅ DONE

## Decisions Made

- Action anim_state override is client-trusted (not server-authoritative). Rationale:
  attack_stage is entirely client-managed in demo_game.py; no server attack logic exists.
  Adding server-side attack_stage tracking is a larger refactor (Milestone 3 of the guidelines).
- Velocity extrapolation is X-only to avoid gravity drift. Y frozen at server target avoids
  the ghost floating upward or downward during the inter-packet gap.
- "run" threshold set to 5.0 (matching _infer_anim_state) rather than MAX_RUN_SPEED (8.0)
  to trigger early enough for smooth transition from walk to run.
