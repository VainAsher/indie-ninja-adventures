# UAT Suite — v0.7.x (2026-03-28)

This is the canonical UAT suite for the current build. It supersedes `docs/reviews/2026-03-25/UAT_SUITE.md` (historical).

---

## Package Contents

- `ninja_dash.exe`
- `UAT_SUITE.md`

## Preflight Checklist

- Unzip to a local writable folder (not a network or read-only path).
- Keep the EXE and this document in the same folder.
- `user_data/` will be created next to the EXE on first run.
- **Pause OneDrive sync** before extracting — OneDrive file locks can interfere with logging.

## How to Run

- Double-click `ninja_dash.exe` for normal launch.
- For tests requiring command-line flags, open Command Prompt in the EXE folder.

## Controls (Quick Reference)

| Action | Keys |
| --- | --- |
| Move | Arrow keys / WASD |
| Jump | Space / W / Up |
| Dash | Shift |
| Run | Alt (hold) |
| Crouch | S / Down (hold) |
| Attack | J |
| Shuriken | K (aim with Up/Down for diagonals) |
| Teleport | F |
| Ninjutsu | L or Q (hold for stance, release to cast) |
| Inventory | I |
| Map | M |
| Minimap | Tab |
| Camera mode | C (cycles world / room / free) |
| Pause | ESC |

## Result Codes

| Code | Meaning |
| --- | --- |
| PASS | Works as described |
| FAIL | Does not work; add repro steps |
| BLOCKED | Cannot test; add reason |
| NA | Not applicable to this build |
| XFAIL | Known failure; expected to fail until milestone ships |

---

## Tester Summary

Tester Name:
Date:
Build ID or File Name:
OS Version:
CPU / GPU / RAM:
Display Resolution:
Run Location Path:

| Result | Count |
| --- | --- |
| PASS | |
| FAIL | |
| BLOCKED | |
| NA | |
| XFAIL | |

---

## Test Cases

### Startup and Boot

| ID | Area | Objective | Steps | Expected | Priority | Expectation | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UAT-BOOT-001 | Startup | Launch to menu, not directly into gameplay | Run `ninja_dash.exe` | Main menu appears; no gameplay running | P0 | PASS | | |
| UAT-BOOT-002 | Mode Flow | Start campaign from menu | Menu → New Game → Campaign → Select mission | Gameplay starts in chosen mission | P0 | PASS | | |
| UAT-BOOT-003 | Production Build | EXE loads all assets | Launch EXE and start a mission | Game boots, assets load, no missing-asset errors | P1 | PASS | | |

### Movement and Input

| ID | Area | Objective | Steps | Expected | Priority | Expectation | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UAT-INPUT-001 | Movement | Walk, run, crouch speed modifiers feel distinct | Move left/right; hold run key; crouch and move | Speed differences are perceptible; no jitter | P0 | PASS | | |
| UAT-INPUT-002 | Jumping | All jump types trigger reliably | Ground jump, double jump, wall jump, coyote jump, buffered jump | Each type works; coyote allows jump just after leaving edge | P0 | PASS | | |
| UAT-INPUT-003 | Wall Slide | Wall friction gives controlled descent | Jump into wall and hold toward it | Player slides down slowly; no sticking or snapping | P1 | PASS | | |

### Animation — Phase 0 Fixes

| ID | Area | Objective | Steps | Expected | Priority | Expectation | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UAT-ANIM-001 | Hurt Animation | Hurt loops while player is invincible | Take damage from enemy; watch sprite | Hurt animation loops for the full invincibility duration; does not freeze on last frame | P0 | PASS | | |
| UAT-ANIM-002 | Jump / Fall Frames | Ascending shows jump frame; descending shows fall frame | Jump over a gap; observe frame change at apex | Frame 1 (ascending pose) during upward travel; frame 0 (falling pose) after apex | P0 | PASS | | |
| UAT-ANIM-003 | Attack Sprite Flip | No sprite flip during attack combos | Face right; walk left while attacking | Sprite does not flip during the 3-hit combo | P0 | PASS | | |

### Combat

| ID | Area | Objective | Steps | Expected | Priority | Expectation | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UAT-COMBAT-001 | Melee | 3-hit combo and hitboxes work | Attack enemy repeatedly | Enemy takes damage and dies; combo timing is consistent | P0 | PASS | | |
| UAT-COMBAT-002 | Damage and I-frames | Player damage, invincibility, and knockback | Let enemy hit player | HP decreases; invincibility flash plays; knockback applied | P0 | PASS | | |

### Ranged and Abilities

| ID | Area | Objective | Steps | Expected | Priority | Expectation | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UAT-RANGED-001 | Shuriken | Projectile visible with collision | Throw shuriken at enemy | Shuriken sprite visible; collision aligns; ammo decrements | P1 | PASS | | |
| UAT-ABILITY-001 | Teleport | Phase cursor and cooldown | Trigger teleport | Phase cursor appears; teleport resolves; cooldown respected | P1 | PASS | | |
| UAT-ABILITY-002 | Ninjutsu | Casting and effect visible | Trigger ninjutsu (hold L/Q, release) | Casting visible; effect applies; cooldown respected | P2 | PASS | | |

### Campaign and Mission Flow — Phase 0 Fixes

| ID | Area | Objective | Steps | Expected | Priority | Expectation | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UAT-CAMP-001 | Victory Screen | Victory screen triggers on mission complete | Complete mission objectives; reach exit | Victory/level-complete screen appears before returning to hub | P0 | PASS | | |
| UAT-CAMP-002 | Hub Return | Player returns to hub after victory | Let victory screen play through | Player is back in hub world; no crash | P0 | PASS | | |
| UAT-CAMP-003 | Respawn Health | Player respawns with full health after death | Die in a mission | Returned to hub with full HP restored | P0 | PASS | | |
| UAT-CAMP-004 | Mission Unlock Chain | Completing a mission unlocks the next | Complete `forest_1` mission | `double_jump` ability unlocked; `forest_2` becomes available in mission menu | P0 | PASS | | |
| UAT-CAMP-005 | Ability Gate | Missions requiring abilities are locked | Check mission menu before completing prerequisite | Missions requiring unowned abilities are greyed out or show locked state | P1 | XFAIL | | Ability gate enforcement pending Milestone 1 |

### Camera and UI

| ID | Area | Objective | Steps | Expected | Priority | Expectation | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UAT-CAMERA-001 | Camera Modes | Cycle camera modes | Press C | Modes cycle (world → room → free); follow remains stable | P0 | PASS | | |
| UAT-CAMERA-002 | Full Map | Map overlay | Press M | Large map (~85% screen) renders correctly; player position shown | P1 | PASS | | |
| UAT-UI-001 | Pause | Pause and resume | ESC to pause; resume; quit to menu | Pauses, resumes, and returns to menu correctly | P0 | PASS | | |
| UAT-UI-002 | Settings | Live setting toggles | Toggle screenshake / particles / smoothing / FPS in Settings | Changes apply immediately; persist after restart | P1 | PASS | | |
| UAT-UI-003 | Inventory | Navigate and use items | Open inventory; move selection; equip/unequip; use consumable | Selection moves; equip works; consumable heals | P0 | PASS | | |
| UAT-UI-004 | Mission Menu | Browse and select missions | Open mission menu; select any available mission | Mission loads without crash | P0 | PASS | | |

### NPCs and Economy

| ID | Area | Objective | Steps | Expected | Priority | Expectation | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UAT-NPC-001 | Dialogue | NPC conversation | Interact with NPC | Dialogue UI opens; can advance choices | P1 | PASS | | |
| UAT-SHOP-001 | Trading | Buy item from shop | Open shop NPC; buy item | Currency changes; item added to inventory | P1 | PASS | | |

### Save and Replay

| ID | Area | Objective | Steps | Expected | Priority | Expectation | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UAT-SAVE-001 | Persistence | Data persists between sessions | Change inventory/settings; exit; relaunch | Data present from save | P0 | PASS | | |
| UAT-REPLAY-001 | Replay | Record and replay stability | `ninja_dash.exe --record uat_record` then `ninja_dash.exe --replay uat_record` | Playback works; no crash | P1 | PASS | | |

### Known Gaps (Expected Failures)

| ID | Area | Objective | Steps | Expected | Priority | Expectation | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UAT-BOSS-001 | Boss | Boss encounter runs | Start any boss mission | XFAIL: no boss spawns; not yet wired | P2 | XFAIL | | Pending Milestone 1 |
| UAT-AUDIO-001 | Audio | SFX plays on game events | Hit enemy; take damage; pick up item | XFAIL: no sounds | P2 | XFAIL | | Pending Milestone 2 |
| UAT-AUDIO-002 | Audio Settings | Volume controls affect playback | Adjust volume in settings | XFAIL: no audio system | P2 | XFAIL | | Pending Milestone 2 |

---

## Feedback

What felt good or fun:

What felt confusing or frustrating:

Top 3 issues to fix first:
1.
2.
3.

Additional comments:
