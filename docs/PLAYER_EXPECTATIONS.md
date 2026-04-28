---
doc_type: playtest_contract
status: living
owner: qa-team
last_updated: 2026-04-28
version_anchor: v0.13.0
---
# Shadow Ascent - Playtest Pack

## Controlled Act I Vertical Slice — Lantern Heights First Session

**Target build:** `v0.13.0`
**Last updated:** `2026-04-28`
**Audience:** Internal QA and controlled first-session testers
**Primary goal:** Prove the G0 golden route (Act I Lantern Dawn) is playable, emotionally legible, and stable

> **External testers: read [docs/PLAYABLE_TRUTH.md](PLAYABLE_TRUTH.md) first.**
> That document has the approved G0 route, what feedback is in scope, and what to ignore.
> This document is the full internal QA reference.

---

## 1. Scope and intent

This document is the canonical playtest reference for Shadow Ascent v0.13.0.

Current scope: **Act I Lantern Dawn vertical slice only.**

The approved test route (G0) covers the first 20–30 minutes: spawn in Lantern Heights,
meet Yin and Yang as companions, greet the core NPC cast, complete one social and one
movement objective, meet Linzi, accept her first mission, return to see one subtle hub
change, then save/load to confirm state persists.

Use this document to answer:

1. Can a new player reach the end of the G0 route without external help?
2. Does Lantern Heights feel like a home, not a menu?
3. Do Yin and Yang feel like companions, not meters?
4. Does Linzi feel flattering and useful before she feels dangerous?
5. Is at least one hub/social change visible without debug tools?

**External tester path:** follow [docs/PLAYABLE_TRUTH.md](PLAYABLE_TRUTH.md) only.
**Internal QA path:** this full document.

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

   - For solo campaign baseline: click `Play` and choose `CAMPAIGN` in mode select.
   - For developer/debug baseline: choose `DEVELOPER` in mode select (all systems, no story pressure).
   - For localhost multiplayer baseline: click `Start Server`, then `Host + Play`.
   - For remote multiplayer baseline: click `Join` and enter `host:port`.

3. Confirm game reaches Main Menu, then Mode Select, then in-game HUD.
4. Run test packs in order from Section 7.

> **v0.11.65 note:** Sandbox mode has been retired. Mode select now shows CAMPAIGN, ARCADE (in development), and DEVELOPER. CAMPAIGN is the primary tester path.

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
| Debug ability toggle (solo only) | `F9` |

Notes:
- These are default bindings. Testers can override them via `user_data/settings/settings.json` under `keybindings`.
- `F1` controls overlay now renders the active live bindings, not only defaults.
- `F9` is an internal debug shortcut (solo only). It cycles all abilities granted → all cleared. Useful for testing locked portals without level grinding. **Do not share this key with external testers unless explicitly running a debug session.**

If control understanding is poor, tag finding with `UX-CONTROLS`.

---

## 5. Lore primer for playtest context

Give testers this short framing before first run. Do not preload spoilers beyond this.

- You are Aen of the Lantern Clan — newly ranked, not yet hollowed.
- Lantern Heights is your home. The people here know you and care about you.
- Two spirit companions orbit you: **Yin** (silver, gentle) and **Yang** (gold, bold). They are yours. They matter.
- **Instructor Tai** greets you at the start. Follow his prompt.
- The village has friends: **Samson** (loyal sparring partner), **Sophia** (cartographer, careful), **Marcel** (practical, blunt), **Hazel** (warm, lantern-weaver).
- **Linzi** appears near the mission board. She is beautiful and perceptive. She says you are different. Note your first impression — do not second-guess it.
- The village will feel subtly different after you accept Linzi's first mission. Notice what changed.
- Yin and Yang may react to things before Aen does. Pay attention to them.
- The game expresses feeling through movement and social presence — not through long text.

---

## 6. Current runtime instrumentation audit

### 6.1 Logging status

| Area | Current status | Notes |
|---|---|---|
| Client log file | Working | `user_data/logs/client.log` rolling daily |
| Server log file | Working | `user_data/logs/server.log` rolling daily |
| Mission event logging | Working | Mission start/progress/exit-unlock/complete/fail/restore, onboarding dialogue events, and room transitions include hub/room/position context |
| Structured event IDs | Working | Runtime traces use stable prefixes: `[Playtest][Stance]`, `[Playtest][Flow]`, `[Playtest][Lantern]`, `[Playtest][Room]`, `[Playtest][Boss]`, `[Playtest][Player]`, `[Playtest][Interaction]`, `[Playtest][NPC]`, `[Playtest][Trial]`, `[Playtest][Echo]`, `[Playtest][Portal]` |
| Portal travel logging | Working | `[Playtest][Portal]` traces emit on both gate denial (`solo portal denied hub=X requiredAbility=Y`) and successful transition (`solo portal travel A → B seed=N`) |
| Echo puzzle logging | Working | `[Playtest][Echo]` traces emit on trigger activation, echo spawn/skip outcome, and `echo_door_*` unlock outcomes |
| Correlation/session IDs | Working | Client sends `session_id` in `CLIENT_HELLO`; server logs join/travel/disconnect with `player_id` + `session_id` |
| Controls baseline evidence | Working | Startup log emits `[Playtest][Controls] preset=GDD-10.3.13 ...` for each launched session |
| Scripted loss traceability | Working | Client network/runtime logs emit `[Net] SCRIPTED_LOSS received` plus `[Playtest][ScriptedLoss] received/continue` context |

### 6.2 Debug tooling status

| Tool | Current status | Access |
|---|---|---|
| Hitbox overlay | Working | Press `H` in-game |
| Controls overlay | Working | Press `F1` in-game |
| Runtime telemetry panel | Working | Press `F3` in-game |
| Debug ability toggle | Working (v0.11.65) | Press `F9` in-game (solo only) — cycles all abilities on/off |
| Launcher log viewer | Working | Launcher `Dev Tools` tab |
| Deep simulation inspector | Missing | No dedicated in-game dev console yet |

### 6.3 Player settings status

| Area | Current status | Gap |
|---|---|---|
| Launcher settings (JVM, paths, update behavior) | Working | Launcher-level only |
| Runtime keybinding overrides (`settings.json`) | Working/partial | `keybindings` block now drives live input/hotkeys; full in-game keybinding menu UI still pending |
| In-game graphics/audio settings UI | Missing | No full settings menu path in Java client |
| Per-profile gameplay settings | Missing/partial | Profiles exist in launcher; gameplay settings not fully wired |

Conclusion: P0 playtest logging/debug coverage is now full for mission/stance/flow/lantern/boss/scripted-loss/user-session tracing.

---

## 7. End-to-end test packs

## Pack A: First-run solo onboarding (45 to 60 min)

**Goal:** Validate a brand-new player path from launcher to first meaningful progression.

### Steps

1. Start from launcher and enter `SOLO`.
2. Find and interact with the Siren (`!` marker) and start first trial (or press `O`).
3. Confirm onboarding toasts appear (`F1`, mission board, tracker/map cue sequence).
4. Open inventory once (`I`) and validate map modes:
   - `Tab` tap toggles quick map.
   - `Tab` hold opens full map and closes when key is released.
   - verify map header text shows the tap/hold key guidance.
5. Trigger at least one mission objective interaction and confirm tracker updates.
   - expectation: objective interactions now show a short explicit player animation cue (`lever`/`button`) instead of silent state change.
6. Trigger at least one failure/death and recover.

`v0.11.65` expectation:
- In `demo_coin_run`, each collected coin should increment mission progress (`collect_items_coin`) and unlock exit at 5/5.

### Record

- `time_to_first_movement_confidence`
- `time_to_first_combat_confidence`
- `first_confusion_point`
- `first_rage_point_or_none`
- `onboarding_clarity_score_1_5`

### Expected

- Player can progress without external docs.
- Siren-first mission handoff is readable in under 30 seconds from spawn.
- Map quick/full behavior is visibly different in size and key guidance text.
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
- NPC visual scale vs interact/collision hitbox alignment (use `H` overlay to verify).
- **Veil Maiden boss pattern (if reached):** Can the tester identify which enemy is the real Veil Maiden vs illusion copies? Note how many attempts before they understand the invincibility mechanic. Tag findings `BAL-BOSS-VEIL`.
- **Music cross-fade:** Does zone music change feel smooth or jarring on hub transitions? Silence is acceptable (no audio assets present yet); cross-fade without audio is a silent no-op. Note any incorrect behaviour as `TECH-AUDIO`.

### Record

- `enemy_fairness_scores_by_type_1_5`
- `systems_clarity_score_1_5`
- `flow_understanding_yes_no`
- `top_3_tuning_requests`
- `veil_maiden_illusion_clarity_yes_no` (if reached)
- `music_transition_feel_smooth_jarring_absent`

### Expected

- Most failures can be explained by player action, not hidden behavior.
- Systems changes are visible enough to describe in plain language.
- NPC sprite size and debug hitbox should feel proportionate in live gameplay.

---

## Pack E: NPC quest chain readability (20 to 30 min)

**Goal:** Verify that Lantern NPC dialogue trees are readable and quest handoffs are clear.

### Steps

1. In solo, find and speak to **Samson** in the hub. Complete or decline his first quest offer.
2. Find and speak to **Hazel**. Accept her gathering request.
3. Find and speak to **Sophia**. Note her tone and the clarity of her map-shard request.
4. If Act 1 progresses far enough, trigger **Sophia's farewell** and confirm the letter reward lands in inventory.
5. Encounter at least one **shadow-echo fragment** in a dark zone (Hollow Depths or equivalent). Note emotional tone.
6. Find and speak to **Linzi** in the early hub. Note your immediate impression of the character before knowing her role.

### Record

- `npc_dialogue_clarity_score_1_5`
- `samson_tone_felt_accurate_yes_no`
- `sophia_farewell_readable_yes_no`
- `shadow_echo_tone_condemning_or_mourning` (expected: mourning)
- `linzi_first_impression` (free text — trust/suspicion/neutral)
- `quest_objective_legible_without_explanation_yes_no`

### Expected

- Quest objectives are readable without external explanation.
- Shadow-echo dialogue reads as grief, not accusation.
- Linzi's early warmth is noticeable before any reveal context is given.
- NPC disappearance (Sophia leaving the hub mid-story) feels intentional, not like a bug.

---

## Pack G: Portal travel and hub navigation — v0.11.65 focus (20 to 30 min)

**Goal:** Verify that portal travel is fully stable after the v0.11.65 blocker fixes: no self-loops, world regenerates correctly, camera snaps to spawn, stance animation shows in all movement states (not only attack). This is the highest-priority test target for this week's external playtest.

### What changed in v0.11.65 (fixes for playtest blockers)

- **Start-room portal self-loop removed:** pressing `E` near spawn no longer shows "ENTERING: CENTRAL HUB" and reloads the same hub. Only exit-room portals are active.
- **World now renders after portal travel:** megamap rebuilds and camera snaps to the new spawn point immediately on arrival. The previous bug (blank world, player off-screen) is resolved.
- **Stance posture in all movement states:** Yin/Yang armed posture is now visible in idle, walk, jump, and crouch — not only during attack animations. This was the v0.11.64 regression.
- **No spurious ability toasts after travel:** abilities restored post-travel no longer fire "new unlock" notifications.
- **F9 debug shortcut (internal only):** press `F9` in solo to grant all abilities instantly for locked-portal testing. Toggle again to clear. Do not include in external tester instructions unless running a debug session.

### Steps

1. **Open portal (no ability required):**
   - Launch CAMPAIGN from the launcher. From spawn, explore the start room — confirm there is **no portal prompt near spawn**. Portals are only in exit rooms.
   - Reach an exit room, locate a portal (glowing `E`-interact prompt), press `E`.
   - Expected: `ENTERING: <HUB NAME>` toast appears. World visibly regenerates. Player spawns in the new hub with health and inventory intact. Camera is centred on the player — not at world origin.
   - Tag any blank world, off-screen spawn, or wrong hub name as `UX-HUB` P0.

2. **Locked portal gate:**
   - Without the `dash` ability, locate and press `E` on a `cave_hub` portal.
   - Expected: `PORTAL LOCKED: REQUIRES DASH` toast. No zone transition occurs.
   - To test this quickly without grinding: press `F9` to grant all abilities, travel through, then press `F9` again to clear abilities and verify the lock reappears on the next locked portal.
   - Tag absent toast or unintended transit as `UX-HUB` P1.

3. **Stance posture readability — all movement states:**
   - Press `A` to switch between Yin and Yang.
   - In **Yin**: player sprite should show unarmed/empty-hands posture while idle, walking, jumping, crouching, and attacking.
   - In **Yang**: player sprite should show sword/armed posture in **all** of those states — not only when swinging.
   - Specifically test idle and walking — these were the broken states in v0.11.64.
   - Tag any state that stays unarmed in Yang (or armed in Yin) as `TECH-ANIM`.

4. **Post-travel ability toasts:**
   - Travel through a portal successfully.
   - On arrival, confirm the HUD does **not** show a burst of "new ability unlocked" toasts for abilities you already had.
   - One toast for a genuinely new unlock is correct. Multiple toasts for already-known abilities is the bug.
   - Tag spurious toasts as `TECH-ANIM` or `UX-HUB`.

5. **Minimap compass:**
   - With an active mission objective (check mission tracker `O`), open quick map (`Tab` tap).
   - Move to a room far from the objective — the objective should be outside the minimap zoom window.
   - Expected: a coloured directional arrow appears on the minimap panel border pointing toward the objective room (gold = reach/waypoint, red = switch, cyan = exit).
   - Confirm the arrow disappears when you enter the objective's room.
   - Tag absence of arrows as `UX-MAP`.

### Record

- `start_room_portal_absent_yes_no` (should be yes — no portal at spawn)
- `portal_travel_success_yes_no`
- `world_rendered_after_travel_yes_no`
- `camera_on_player_after_travel_yes_no`
- `portal_lock_toast_visible_yes_no`
- `player_state_preserved_after_travel_yes_no` (health, inventory intact)
- `yin_posture_idle_walk_readable_yes_no`
- `yang_posture_idle_walk_readable_yes_no`
- `spurious_ability_toasts_after_travel_yes_no` (should be no)
- `compass_arrow_visible_yes_no`
- `any_crash_or_softlock_on_portal_travel`

### Expected

- No portal near the start room. Portals are exit-room only.
- Portal travel completes without crash, blank world, or off-screen spawn.
- Player state (health, inventory, abilities) is preserved across hub transition.
- Locked portal shows toast only — no transition.
- Yin shows unarmed posture in all states. Yang shows armed posture in all states including idle and walk.
- No ability toasts for already-held abilities on arrival.
- Compass arrow appears within 1–2 seconds of the objective leaving the minimap window.

### Known limitations (do not file as bugs)

- Hub worlds are procedurally generated — room layout differs between visits. This is correct.
- Not all hubs are reachable without the required ability. Central Hub and Forest Hub are always open.
- ARCADE mode is in development and does not yet have hub travel.

---

## Pack F: Trial room entry and completion (25 to 35 min)

**Goal:** Verify trial rooms are discoverable, readable as optional challenge areas, and completable.

### Steps

1. Unlock a trial room (requires completing a prerequisite quest — e.g., `hazel_q2` or `samson_q2`).
2. Locate the trial on the minimap (`TRIAL` label).
3. Enter the trial room and observe: does the room lock on entry? Is the objective clear?
4. Attempt the trial. Note difficulty, hazard readability, and whether the par-time feels fair.
5. Complete or fail the trial and confirm reward/outcome feedback.
6. Verify the proof token appears in inventory on success.

### Record

- `trial_room_discoverable_yes_no`
- `trial_lock_on_entry_clear_yes_no`
- `trial_objective_clear_yes_no`
- `trial_difficulty_score_1_5`
- `proof_token_received_yes_no`
- `top_friction_point`

### Expected

- Trial rooms are visually distinct from standard rooms.
- Room lock on entry is visible — tester should not feel trapped unexpectedly.
- Proof token reward is legible and lands correctly in inventory.
- Trial failure should not permanently block quest progression.

---

## 8. What to capture for every issue

For every bug, frustration point, or balance note capture:

1. Build version (`v0.11.60` or newer).
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
| `UX-NPC` | NPC dialogue clarity, quest handoff readability, character tone |
| `UX-AUDIO` | Music cross-fade transitions, SFX presence or absence |
| `UX-HUB` | Portal travel readability, hub transition feel, locked-portal messaging |
| `TECH-ANIM` | Wrong stance sprite, posture flicker, incorrect animation prefix routing |
| `UX-MAP` | Minimap compass arrow missing, wrong direction, wrong colour coding |
| `BAL-ENEMY` | Enemy and boss tuning |
| `BAL-BOSS-VEIL` | Veil Maiden illusion mechanic clarity and difficulty |
| `BAL-TRIAL` | Trial room difficulty, hazard legibility, reward balance |
| `BAL-DIFFICULTY` | Difficulty curve and spikes |
| `TECH-STABILITY` | Crashes, softlocks, desync, persistence faults |
| `TECH-LOGGING` | Missing or unclear diagnostics |
| `TECH-SETTINGS` | Settings feature gaps or nonfunctional options |
| `TECH-AUDIO` | Incorrect music state, missing cross-fade, audio errors in log |

---

## 12. Templates

## Session summary template

```md
### Session Summary
Build: v0.11.65
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
Build: v0.11.65
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
6. At least one NPC quest chain (Pack E) completed and `UX-NPC` findings filed.
7. At least one trial room (Pack F) completed and `BAL-TRIAL` findings filed.
8. Veil Maiden illusion mechanic legibility note filed under `BAL-BOSS-VEIL` (even if not reached in every session).
9. Music cross-fade behaviour noted for at least one hub transition (`UX-AUDIO` or `TECH-AUDIO`).
10. **v0.11.65 gate:** Pack G step 1 — portal travel completes with world rendered and camera on player. No blank world. `UX-HUB` filed or marked clean.
11. **v0.11.65 gate:** Pack G step 3 — Yang stance shows armed posture in idle and walk states (not only attack). `TECH-ANIM` filed or marked clean.
12. **v0.11.65 gate:** Pack G step 2 — locked portal denial observed; no start-room portal present. `UX-HUB` filed or marked clean.
13. **v0.11.65 gate:** Pack G step 4 — no spurious ability toasts on portal arrival. `UX-HUB` or `TECH-ANIM` filed or marked clean.
14. **v0.11.65 gate:** Minimap compass arrows observed during at least one off-screen objective — `UX-MAP` filed or marked clean.

---

## 14. Maintainer note

Update this file every release candidate with:

- current build version
- known instrumentation changes
- test pack changes
- newly discovered must-test regressions

This document is a release artifact, not just internal notes.
