# UAT Suite (2026-03-25)

This document is intended to be bundled with the production EXE for testers. It includes setup steps, controls, and result recording.

**Package Contents**
- `ninja_dash.exe`
- `UAT_SUITE.md`

**Preflight Checklist**
- Unzip the package to a local writable folder (not a read-only or network path).
- Keep the EXE and this document in the same folder.
- Expect `user_data/` to be created next to the EXE on first run.

**How To Run**
- Double-click `ninja_dash.exe` to launch normally.
- For tests that require command-line flags, open Command Prompt in the EXE folder and run commands like `ninja_dash.exe --record uat_record`.

**Controls (Quick Reference)**
- Move: Arrow keys or WASD
- Jump: Space, W, or Up
- Dash: Shift
- Run: Alt
- Crouch: S or Down (hold)
- Attack: J
- Shuriken: K (aim with Up or Down for diagonals)
- Teleport: F
- Ninjutsu: L or Q (hold for stance, release to cast)
- Inventory: I
- Map: M
- Minimap: Tab
- Camera mode: C
- Pause: ESC

**Result Recording**
- Use Result values: PASS, FAIL, BLOCKED, NA, or XFAIL.
- Add short notes for any FAIL or BLOCKED result, including repro steps.
- Logs are written to `user_data/logs/` next to the EXE.

**Tester Summary**
Tester Name: 
Date: 
Build ID or File Name: 
OS Version: 
CPU/GPU/RAM: 
Display Resolution: 
Run Location Path: 

| Result | Count |
| --- | --- |
| PASS | |
| FAIL | |
| BLOCKED | |
| NA | |
| XFAIL | |

**Test Cases**

| ID | Area | Objective | Steps | Expected Result | Priority | Expectation | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UAT-BOOT-001 | Startup | Launch to menu, not directly into a level | Run `ninja_dash.exe` | Main menu appears, no gameplay running | P0 | PASS |  |  |
| UAT-BOOT-002 | Mode Flow | Start campaign mission from menu | Menu > New Game > Campaign > Select mission | Gameplay starts in chosen mission | P0 | PASS |  |  |
| UAT-BOOT-003 | Production Build | EXE runs and loads assets | Launch EXE and start a mission | Game boots, assets load, no missing data | P1 | PASS |  |  |
| UAT-INPUT-001 | Movement | Walk, run, crouch speed modifiers | Move left/right, hold run key, crouch hold | Speed changes feel distinct, no jitter | P0 | PASS |  |  |
| UAT-INPUT-002 | Jumping | Jump types and buffers work | Ground jump, double jump, wall jump, coyote, buffer | All jump types trigger reliably | P0 | PASS |  |  |
| UAT-INPUT-003 | Wall Slide | Wall slide or wall friction feels consistent | Jump into wall and hold toward wall | Controlled descent without sticking or jitter | P1 | PASS |  |  |
| UAT-COMBAT-001 | Melee | 3-hit combo and hitboxes | Attack enemy repeatedly | Enemy takes damage and dies; combo timing consistent | P0 | PASS |  |  |
| UAT-COMBAT-002 | Damage/iframes | Player damage, invincibility, knockback | Let enemy hit player | HP decreases, invincibility flash, knockback | P0 | PASS |  |  |
| UAT-RANGED-001 | Shuriken | Projectile visible with collision box | Throw shuriken at enemy | Shuriken sprite visible, collision box aligns, ammo decrements | P1 | PASS |  |  |
| UAT-ABILITY-001 | Teleport | Teleport phase and cooldown | Trigger teleport ability | Phase cursor appears, teleport resolves, cooldown respected | P1 | PASS |  |  |
| UAT-ABILITY-002 | Ninjutsu | Ninjutsu casting and effect | Trigger ninjutsu | Casting and effect visible, cooldown respected | P2 | PASS |  |  |
| UAT-CAMERA-001 | Camera | Camera modes and smoothing | Press C to cycle camera modes | Modes change as expected, follow remains stable | P0 | PASS |  |  |
| UAT-CAMERA-002 | Full Map | Map overlay size and centering | Press M | Large centered map (~85% screen) renders correctly | P1 | PASS |  |  |
| UAT-UI-001 | Pause Menu | Pause/resume flow | Press ESC to pause, resume, quit to menu | Game pauses, resumes, and returns to menu | P0 | PASS |  |  |
| UAT-UI-002 | Settings | Live settings toggles | Open Settings, toggle screenshake/particles/smoothing/FPS | Changes apply immediately and persist | P1 | PASS |  |  |
| UAT-UI-003 | Inventory | Navigation and equip/use | Open inventory, move selection, equip/unequip, use consumable | Selection moves, equip/unequip works, consumable heals | P0 | PASS |  |  |
| UAT-UI-004 | Mission Menu | Playtest mission selection | Open mission menu, select playtest mission | Mission loads without crash | P0 | PASS |  |  |
| UAT-NPC-001 | Dialogue | NPC interaction flow | Interact with NPC | Dialogue UI opens and advances choices | P1 | PASS |  |  |
| UAT-SHOP-001 | Shop | Trading flow | Open shop NPC, buy item | Currency changes, item added to inventory | P1 | PASS |  |  |
| UAT-SAVE-001 | Save/Load | Persistence across sessions | Change inventory/settings, exit, relaunch | Data persists from save | P0 | PASS |  |  |
| UAT-REPLAY-001 | Replay | Record and replay stability | Run `ninja_dash.exe --record uat_record` then `ninja_dash.exe --replay uat_record` | Playback works, no metadata crash | P1 | PASS |  |  |
| UAT-BOSS-001 | Bosses | Confirm boss encounters | Start any boss mission | Expected fail: no boss spawns (gap to fix) | P2 | XFAIL |  |  |
| UAT-AUDIO-001 | Audio | Confirm audio system status | Adjust audio settings and trigger actions | Expected fail: no sounds (system missing) | P2 | XFAIL |  |  |

**Notes**
- If a test fails, capture logs from `user_data/logs/` and add repro steps in the Notes column.
- If an expected fail unexpectedly passes, mark PASS and note the behavior.

**Feedback**
What felt good or fun:

What felt confusing or frustrating:

Top 3 issues to fix first:
1.
2.
3.

Additional comments:
