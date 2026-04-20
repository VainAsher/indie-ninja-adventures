---
doc_type: playtest_handover
status: active
owner: core-team
version: v0.11.69
date: 2026-04-20
audience: internal playtesters, QA lead
---

# Playtest Handover — Shadow Ascent v0.11.69

**Date:** 2026-04-20
**Version:** v0.11.69
**Platform:** Windows desktop
**Launcher:** `launcher.exe` (always the entry point — never run JARs directly)
**Primary test target:** Campaign mode, solo play

This document hands off the current build for structured playtesting. Read it in full before starting.

---

## 1. How to launch

1. Open `launcher.exe` from your install folder (e.g., `C:\...\Fresh Test\`)
2. On the **Play** tab, click **Check for Updates** — confirm you are running **v0.11.69** before starting
3. Choose your path:
   - **Solo campaign baseline:** click `Play` → choose `CAMPAIGN`
   - **Debug/developer baseline:** click `Play` → choose `DEVELOPER` (all systems unlocked, no story pressure)
   - **Multiplayer baseline:** click `Start Server`, then `Host + Play` (localhost) or `Join` (remote)
4. At the slot select screen, choose **Slot 1** for a new game

> If the slot screen does not appear, you may be running an older JAR. Re-run the launcher update check.

---

## 2. What is working in v0.11.69

### Core systems — stable

| System | Status |
|---|---|
| Physics (move, jump, dash, crouch, wall-climb, swim) | Stable |
| Combat (melee, guard/parry, enemy AI, hitboxes) | Stable — balanced in v0.11.63 |
| Portal travel (ability gates, zone migration, state preservation) | Stable since v0.11.65 |
| Save / load (3 slots, checksums, legacy migration) | Stable since v0.11.68 |
| Mission lifecycle (trigger, progress, completion, failure, restore) | Stable |
| Stance posture (Yin unarmed / Yang armed in all movement states) | Stable since v0.11.65 |
| Minimap (zoom/pan, room labels, compass, objective markers) | Stable |
| Solo/multiplayer campaign parity | Stable since v0.11.64 |
| Replay playback (`-Dninja.replayPath`) | Stable |
| Replay recording (`.ndjson`) | Active |

### New in this build

| Feature | Notes |
|---|---|
| 3-slot save selection | Slot screen appears between Main Menu and Mode Select |
| SHA-256 save integrity | Corrupt saves detected on load; fresh-start fallback fires cleanly |
| Lantern NPC dialogue chains | Samson, Sophia, Marcel, Hazel, Linzi — all with full branching trees |
| Veil Maiden boss pattern | Illusion/clone phase — clarity intentionally under test |
| Zone music cross-fade | `MusicManager` wired; silent (no audio assets yet) |
| Trial rooms | `TRIAL` room type on minimap — higher difficulty, quest-reward gates |
| In-game dev console | Press **F10** (or backtick) — Campaign and Developer modes only |
| Content hot-reload | `reload_content` and `reload_anims` commands in dev console |

---

## 3. Controls reference

| Action | Default key |
|---|---|
| Move / Aim / Crouch direction | Arrow Keys |
| Run modifier | Left Shift |
| Jump | Z |
| Dash | C |
| Melee attack | X |
| Guard / Parry | S |
| Switch Yin ↔ Yang | A |
| Traversal Art | D |
| Thrown Tool | F |
| Echo Art | R |
| Interact | E |
| Mission board overlay | O |
| Inventory | I |
| Consumable | Q |
| Quick map (tap) | Tab |
| Full map (hold) | Tab (hold) |
| Direct stance hot-swap | 1 (Yin) / 2 (Yang) |
| Pause / back | Esc |

**Debug keys (testers only — do not share with external testers):**

| Key | Action |
|---|---|
| H | Hitbox overlay |
| F1 | Live controls overlay |
| F3 | Runtime debug panel |
| F9 | Cycle all abilities on / off (solo only) |
| F10 (or backtick) | Open/close in-game dev console |

> Controls can be overridden in `user_data/settings/settings.json` under `keybindings`.

---

## 4. What is NOT in scope for this playtest

Do not report the following as bugs — they are known gaps, not regressions:

| Area | Status |
|---|---|
| Audio / music | System wired, no audio assets yet. Silence is expected. |
| In-game settings menu (graphics/audio) | Not built — configure via launcher only |
| Arcade mode | In development — do not test |
| Full keybinding UI | Not built — edit `settings.json` manually |
| External multiplayer (NAT traversal) | Not tested — localhost only |
| Boss encounters beyond Veil Maiden | Not yet authored |
| Full Act 1 narrative completion | Acts exist as stubs; Act I is the test scope |

---

## 5. Logging and evidence capture

All playtest sessions automatically write log files:

| Log | Location |
|---|---|
| Client log | `user_data/logs/client.log` |
| Server log | `user_data/logs/server.log` |
| Replay recording | `user_data/replays/` (NDJSON, one per session) |

**Structured log events to watch for:**

- `[Playtest][Portal]` — portal travel (gate denial and successful transition)
- `[Playtest][Stance]` — stance switch events
- `[Playtest][Mission]` — mission start/progress/complete/fail
- `[Playtest][Boss]` — boss phase transitions
- `[Playtest][Interaction]` — lever, button, pickup animations
- `[Playtest][NPC]` — NPC dialogue interactions
- `[Playtest][Trial]` — trial room entry and completion
- `[Playtest][Player]` — death, respawn, ability acquisition

Launcher Dev Tools tab shows live log output during play.

---

## 6. Priority test targets (run in this order)

### P0 — Must pass before anything else matters

**G1: Hub onboarding**
1. Launch CAMPAIGN from launcher
2. Main Menu → Slot Select → Mode Select → in-game HUD loads
3. Siren dialogue triggers and first objective appears in mission tracker
4. Pass: HUD present, tracker shows objective, no crash or softlock

**G5: Portal travel — full 6-item checklist**
1. From spawn — confirm **no portal prompt near start room** (exit rooms only)
2. Reach exit room, press E on portal — confirm `ENTERING: <HUB>` toast
3. World renders, camera centred on player (not at world origin)
4. Press E on a locked portal without ability — confirm lock toast, no travel
5. After successful travel — confirm **no spurious "new ability" toasts**
6. Player health and inventory intact on arrival
7. Pass: all six items green. Tag any failure `UX-HUB P0`.

**G6: Save / quit / reload**
1. Progress at least one mission objective
2. Quit via launcher
3. Relaunch — confirm same slot, same hub, same inventory
4. Pass: persistence round-trip clean. Tag any regression `SAVE-REGRESSION`.

### P1 — High-priority validation

**G4: Stance posture in all movement states**
1. Switch to Yang — verify armed/sword posture in idle, walk, jump, crouch, attack
2. Switch to Yin — verify unarmed posture in all five states
3. Pass: both stances correct in all five states. Tag any failure `TECH-ANIM`.

**G2: First mission (coin run)**
1. Enter `demo_coin_run` world
2. Collect 5 coins — progress increments each time
3. 5/5 — exit unlocks and is reachable
4. Pass: mission completes cleanly

**G3: Movement mastery**
1. Walk, run, crouch-walk, jump, wall-jump, dash
2. Each responsive — no clip, float, or judder
3. Wall-climb (Yin) and ledge-hang must not slide
4. Pass: all six movement states readable and stable

### P2 — Important but not blocking

**Pack D: Combat feel**
- Slime, skeleton, archer pressure and fairness
- Veil Maiden boss — can tester identify real vs illusion? How many attempts? Record as `BAL-BOSS-VEIL`
- Yin/Yang/Lantern/Flow legibility

**Pack E: NPC dialogue**
- Samson, Hazel, Sophia, Linzi first impressions
- Shadow-echo tone (should feel mourning, not accusatory)
- Quest objectives legible without external explanation

---

## 7. What to capture and report back

For each session, report:

```
Version: v0.11.69
Mode: CAMPAIGN / DEVELOPER / MULTIPLAYER
Session duration:
Slot used: 1 / 2 / 3

--- P0 Goldens ---
G1 Hub onboarding: PASS / FAIL (note first failure point)
G5 Portal travel: PASS / FAIL (note which of 6 items failed)
G6 Save/reload:   PASS / FAIL

--- P1 Goldens ---
G4 Stance posture: PASS / FAIL (note which state failed)
G2 Coin run:       PASS / FAIL
G3 Movement:       PASS / FAIL

--- Feeling and friction ---
Time to first movement confidence:
Time to first combat confidence:
First confusion point:
First frustration point (or none):
Onboarding clarity (1–5):

--- NPC / Narrative ---
Siren quest clarity (1–5):
Shadow-echo tone: mourning / accusatory / neutral (expected: mourning)
Linzi first impression: trusted / suspicious / neutral
Any NPC disappearance that felt like a bug (should feel intentional):

--- Boss ---
Veil Maiden illusion clarity: yes / no / not reached
Attempts before mechanic understood:

--- Top 3 findings ---
1.
2.
3.

--- Logs ---
Attach: user_data/logs/client.log
Attach: user_data/replays/ (most recent session)
```

Submit findings to the [feedback repo](https://github.com/VainAsher/indie-ninja-feedback) or share directly with the dev team.

---

## 8. Known issues (do not re-report)

| Issue | Status |
|---|---|
| Music is silent | Expected — no audio assets yet |
| `ARCADE` mode not playable | Placeholder only — skip it |
| Dev console backtick may not open on some keyboards | Use **F10** instead — fully functional |
| No in-game graphics/audio settings screen | Known gap — configure via launcher |
| NPC scale may feel slightly large in some rooms | Being monitored — use H overlay to verify hitbox proportions |

---

## 9. Build verification

Before starting, confirm the build is correct:

1. Launcher title bar or About tab shows **v0.11.69**
2. Slot select screen appears between Main Menu and Mode Select
3. F10 opens the dev console in Campaign mode
4. `user_data/logs/client.log` is being written during play

If any of these fail, do not start test packs — contact the dev team.

---

*Handover prepared: 2026-04-20 | Next expected build: tbd based on playtest feedback*
