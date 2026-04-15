# Shadow Ascent - Launcher-Only Playtest Pack
## End-to-End UX Validation for Solo and Multiplayer

**Target build:** `v0.11.44`
**Last updated:** `2026-04-15 14:37:00 +01:00`
**Audience:** Testers with `launcher.exe` only, no IDE, no terminal setup
**Primary goal:** Verify user experience, progression reliability, and Flow baseline before P1 tuning

---

## 1. Scope and intent

This document is the canonical launcher-only playtest pack for Shadow Ascent.

Use it to answer three release questions:

1. Can a new player install and play without hidden setup knowledge?
2. Do core systems behave consistently enough to start P1 balancing and tuning?
3. Are findings captured in a form that maps directly to design goals in `docs/GDD.md`?

This pack assumes the tester starts from launcher only.

---

## 2. Tester profile and assumptions

- Tester has `launcher.exe` and game files in one folder.
- Tester has no repo access and no command line requirements.
- Tester may have never seen controls, lore, or system terminology before.

If a tester cannot progress without external help, capture that as onboarding friction.

---

## 3. Quick start from launcher.exe

1. Open `launcher.exe`.
2. On Play tab:
- For solo baseline: click `Play` and choose `SOLO` in mode select.
- For localhost multiplayer baseline: click `Start Server`, then `Host + Play`.
- For remote multiplayer baseline: click `Join` and enter `host:port`.
3. Confirm game reaches Main Menu, then Mode Select, then in-game HUD.
4. Run test packs in order from Section 7.

---

## 4. Control reference for first-time testers

Use this as the default expected keyboard map.

| Action | Input |
|---|---|
| Move / Aim / Crouch direction | `Arrow Keys` |
| Run modifier | `Left Shift` |
| Jump | `Z` |
| Dash | `C` |
| Melee attack | `X` |
| Guard / Parry | `S` |
| Switch Yin/Yang | `A` |
| Traversal Art | `D` |
| Thrown Tool | `F` |
| Echo Art | `R` |
| Interact | `E` |
| Mission board overlay | `O` |
| Inventory | `I` |
| Consumable | `Q` |
| Quick map | `Tab` (tap) |
| Full map | `Tab` (hold) |
| Pause/back | `Esc` |
| Hitbox overlay | `H` |
| Controls overlay | `F1` |
| Runtime debug overlay | `F3` |

If control understanding is poor, tag finding with `UX-CONTROLS`.

---

## 5. Lore primer for playtest context

Give testers this short framing before first run:

- You are the Hollowed Ninja reclaiming balance.
- In Act I, the Siren is the explicit first quest giver and mission handoff NPC.
- The game expresses identity through movement, stance pressure, and recovery loops.
- Hub progression and scripted loss are intended narrative beats, not random failures.
- Yin, Yang, Lantern, and Flow are intended to be felt in play, not explained by long text.
- Early mission worlds are intentionally compact (4-9 rooms) for onboarding readability.

Do not preload mechanical spoilers beyond this.

---

## 6. Current runtime instrumentation audit

### 6.1 Logging status

| Area | Current status | Notes |
|---|---|---|
| Client log file | Working | `user_data/logs/client.log` rolling daily |
| Server log file | Working | `user_data/logs/server.log` rolling daily |
| Mission event logging | Working | Mission start/progress/complete, onboarding dialogue events, and room transitions include hub/room/position context |
| Structured event IDs | Working | Runtime traces use stable prefixes: `[Playtest][Stance]`, `[Playtest][Flow]`, `[Playtest][Lantern]`, `[Playtest][Room]`, `[Playtest][Boss]`, `[Playtest][Player]` |
| Correlation/session IDs | Working | Client sends `session_id` in `CLIENT_HELLO`; server logs join/travel/disconnect with `player_id` + `session_id` |

### 6.2 Debug tooling status

| Tool | Current status | Access |
|---|---|---|
| Hitbox overlay | Working | Press `H` in-game |
| Controls overlay | Working | Press `F1` in-game |
| Runtime telemetry panel | Working | Press `F3` in-game |
| Launcher log viewer | Working | Launcher `Dev Tools` tab |
| Deep simulation inspector | Missing | No dedicated in-game dev console yet |

### 6.3 Player settings status

| Area | Current status | Gap |
|---|---|---|
| Launcher settings (JVM, paths, update behavior) | Working | Launcher-level only |
| In-game key rebinding | Missing | Input bindings remain hardcoded in client |
| In-game graphics/audio settings UI | Missing | No full settings menu path in Java client |
| Per-profile gameplay settings | Missing/partial | Profiles exist in launcher; gameplay settings not fully wired |

Conclusion: P0 playtest logging/debug coverage is now full for mission/stance/flow/lantern/boss/user-session tracing.

---

## 7. End-to-end test packs

## Pack A: First-run solo onboarding (45 to 60 min)

**Goal:** Validate a brand-new player path from launcher to first meaningful progression.

### Steps

1. Start from launcher and enter `SOLO`.
2. Find and interact with the Siren (`!` marker) and start first trial (or press `O`).
3. Confirm onboarding toasts appear (`F1`, mission board, tracker/map cue sequence).
4. Open inventory once (`I`) and map once (`Tab` tap/hold behavior).
5. Trigger at least one mission objective interaction and confirm tracker updates.
6. Trigger at least one failure/death and recover.

### Record

- `time_to_first_movement_confidence`
- `time_to_first_combat_confidence`
- `first_confusion_point`
- `first_rage_point_or_none`
- `onboarding_clarity_score_1_5`

### Expected

- Player can progress without external docs.
- Siren-first mission handoff is readable in under 30 seconds from spawn.
- UI does not block basic understanding.
- Death and retry feel readable, not random.

---

## Pack B: Save/load and continuity (20 to 30 min)

**Goal:** Verify persistence integrity for active progression.

### Steps

1. In solo, advance at least one mission objective.
2. Exit to launcher.
3. Relaunch and re-enter same mode.
4. Confirm mission/story context, position, and inventory continuity.
5. Repeat with a second quit/relaunch cycle.

### Record

- `save_load_confidence_score_1_5`
- `state_fields_lost_or_reset`
- `any_wrong_respawn_or_wrong_hub`

### Expected

- No critical progression fields lost.
- Re-entry context is coherent.

---

## Pack C: Multiplayer launcher path (30 to 45 min)

**Goal:** Validate host/join lifecycle, combat readability, and sync confidence.

### Steps

1. Host starts `Start Server` then `Host + Play`.
2. Joiner connects via `Join`.
3. Both players enter combat and move across rooms.
4. Verify both can see enemy pressure and updates consistently.
5. Disconnect/reconnect one client and verify session continuity.

### Record

- `join_success_time`
- `desync_symptoms`
- `reconnect_behavior`
- `multiplayer_readability_score_1_5`

### Expected

- Joining works without manual network troubleshooting.
- Reconnect does not corrupt active session behavior.

---

## Pack D: Combat and systems clarity baseline (40 to 60 min)

**Goal:** Establish P1-ready baseline for enemy fairness and systems readability.

### Focus checks

- Slime attack reach and visual alignment.
- Skeleton shield bearer pressure and block readability.
- Archer spacing and projectile readability.
- Yin/Yang/Lantern/Flow clarity from player perspective.

### Record

- `enemy_fairness_scores_by_type_1_5`
- `systems_clarity_score_1_5`
- `flow_understanding_yes_no`
- `top_3_tuning_requests`

### Expected

- Most failures can be explained by player action, not hidden behavior.
- Systems changes are visible enough to describe in plain language.

---

## 8. What to capture for every issue

For every bug, frustration point, or balance note capture:

1. Build version (`v0.11.44` or newer).
2. Mode (`SOLO`, `CAMPAIGN`, `HOST`, `JOIN`).
3. Area context (`hub`, `room grid`, enemy type, mission id).
4. Exact player-visible behavior.
5. Expected behavior in plain language.
6. Severity (`blocker`, `high`, `medium`, `low`).
7. Log snippet and screenshot/video if possible.

---

## 9. Logs and debug collection guide

## 9.1 File locations

Default game data root (launcher-managed):

- `user_data/logs/client.log`
- `user_data/logs/server.log`
- `user_data/saves/savegame.json`
- `user_data/settings/settings.json`
- `user_data/replays/*.ndjson`

If tester changed game directory in launcher Settings, use that configured folder's `user_data` tree.

## 9.2 How to access logs from launcher

1. Open launcher.
2. Go to `Dev Tools` tab.
3. Use Log viewer dropdown.
4. Filter by level and text.
5. Copy relevant lines into report.

## 9.3 In-game debug screens

- `H`: Hitbox overlay.
- `F1`: Controls overlay.
- `F3`: Runtime telemetry panel.

When reporting spatial bugs include telemetry values:

- `snapshot.hub`
- `snapshot.room`
- `local.pos`
- `local.player_id`
- `session_id` (client + server correlation)

## 9.4 Recommended report attachments

- One screenshot showing issue and HUD.
- One short log snippet (10 to 40 lines).
- Optional short clip for timing/readability issues.

---

## 10. Identity and persistence note (important)

Older builds could make identity diagnosis ambiguous when sessions were mixed.

Expected behavior after the current fix:

- Launcher profile now provides stable player identity for Java client sessions.
- Client also supports persisted fallback identity at `user_data/profiles/client_identity.json`.
- Every network session now has a generated `session_id` echoed across client/server logs.

Validation check:

1. Connect twice from same launcher profile.
2. Confirm `server.log` shows same `player_id` value both sessions.
3. Confirm each connect/disconnect also includes a `session_id` so one run can be traced end-to-end.

If UUID changes across relaunch with same profile, report as `TECH-STABILITY` blocker.

---

## 11. Feedback IDs for triage

| ID | Area |
|---|---|
| `UX-LAUNCH` | Launcher and startup flow |
| `UX-CONTROLS` | Controls discoverability and comfort |
| `UX-MOVE` | Movement responsiveness and consistency |
| `UX-COMBAT` | Combat readability and fairness |
| `UX-SYSTEMS` | Yin/Yang/Lantern/Flow understanding |
| `UX-PROGRESSION` | Mission and save continuity |
| `UX-NARRATIVE` | Story/hub emotional pacing |
| `BAL-ENEMY` | Enemy and boss tuning |
| `BAL-DIFFICULTY` | Difficulty curve and spikes |
| `TECH-STABILITY` | Crashes, softlocks, desync, persistence faults |
| `TECH-LOGGING` | Missing or unclear diagnostics |
| `TECH-SETTINGS` | Settings feature gaps or nonfunctional options |

---

## 12. Templates

## Session summary template

```md
### Session Summary
Build: v0.11.44
Mode: SOLO / HOST / JOIN
Duration: XX min

Top positives:
1.
2.
3.

Top issues:
1.
2.
3.

Most severe issue:

Overall readiness for P1 tuning (1-5):

IDs: UX-___ / BAL-___ / TECH-___
```

## Bug template

```md
### Bug
Build: v0.11.44
Mode: SOLO / HOST / JOIN
Severity: blocker / high / medium / low

Steps:
1.
2.
3.

Expected:
Observed:

Telemetry:
- hub:
- room:
- pos:
- player_id:

Logs:
[paste 10-40 lines]

ID: TECH-STABILITY / UX-___ / BAL-___
```

## Balance note template

```md
### Balance Observation
Enemy/System:
Context (hub/room/mission):

What felt unfair or unclear:
What felt good:
Proposed adjustment:

Confidence: low / medium / high
ID: BAL-ENEMY / BAL-DIFFICULTY / UX-SYSTEMS
```

---

## 13. Exit criteria for P0-10 handoff to P1

The playtest pack phase is complete when all are true:

1. Solo and multiplayer launcher paths are validated by at least 3 sessions each.
2. No open blocker in `TECH-STABILITY`.
3. Every high-severity issue has owner and next action.
4. Flow baseline feedback exists with repeatable evidence.
5. Balance backlog is prioritized for P1 (`enemy`, `movement`, `systems`, `progression`).

---

## 14. Maintainer note

Update this file every release candidate with:

- current build version
- known instrumentation changes
- test pack changes
- newly discovered must-test regressions

This document is a release artifact, not just internal notes.
