---
doc_type: playable_truth
status: living
owner: qa-team
last_updated: 2026-04-29
version_anchor: v0.13.4
---

# Playable Truth

**Shadow Ascent: The Hollowed Ninja** — honest state of what is playable right now.

Read this before running any test. Read this before sending any feedback. Read this before judging the game.

---

## Current build

Version: **v0.13.4**
Platform: Windows desktop — launcher install only
Audience: Internal QA and controlled first-session testers
Mode: Campaign (solo, no server required)

---

## The one approved test route (G0 — Act I Lantern Dawn)

This is the only route we are currently asking testers to run.

```
1.  Launch from launcher.exe — click Play, choose CAMPAIGN
2.  Spawn in Lantern Heights at dawn
3.  Observe Yin (silver) and Yang (gold) orbiting Aen
4.  Read the opening prompt from Instructor Tai
5.  Greet the village NPCs: Samson, Sophia, Marcel, Hazel
6.  Complete the social grounding objective (village welcome)
7.  Complete the sparring objective with Samson
8.  Find Linzi near the mission board at twilight
9.  Accept Linzi's first mission — feel the praise, not the threat
10. Complete or begin Linzi's mission
11. Return to Lantern Heights
12. Notice one subtle change in the hub (an NPC moved, a lantern dimmed,
    a line of dialogue shifted in tone)
13. Save and quit
14. Relaunch — confirm Lantern Heights state and progress persisted
```

**Pass criteria:** No crash. No softlock. No dead-end objective. Player understands
Lantern Heights as home. Player sees Yin and Yang as companions. Player notices
Linzi as useful and flattering, not yet threatening.

**If any step is broken, that is the feedback we want.**

---

## What is working well enough to judge

| System | Status | Notes |
| ------ | ------ | ----- |
| Core movement (walk, jump, crouch, dash) | Tunable | Physics feel is solid; dash distance may still need tuning |
| Basic combat (attack, knockdown, kill) | Tunable | Unarmed vs armed distinction works; combo depth is post-Act I |
| Hub navigation | Working | Lantern Heights layout is authored; NPCs are placed |
| NPC interaction + dialogue | Working | Samson, Sophia, Marcel, Hazel, Linzi dialogue authored and routing |
| Social missions (greet, spar, help) | Working | Act I objective sequence authored |
| Linzi's first mission | Working | Praise-first framing; no villain flags yet |
| Hub change after Linzi's influence | Working | One subtle NPC/environment shift after Linzi mission accepted |
| Yin and Yang companion orbs | Working | Visible as silver/gold orbiting companions beside Aen |
| Save and load | Working | Hub state, story flags, and mission progress persist |
| Controls (keyboard) | Working | Move, jump, attack, interact, map |

---

## What is implemented but not yet tuned for Act I

These exist in the codebase and may be visible but should not be the focus of feedback yet.

| System | State | Why not tuned yet |
| ------ | ----- | ----------------- |
| Stance system (Yin passive / Yang aggressive) | Present but subtle in Act I | Stance identity is a post-hollowing reveal; Act I keeps it light |
| Lantern vignette | Present | Vignette at low Lantern values; Aen starts with high Lantern in Act I |
| Flow mastery state | Triggered by balanced combat | Works but not yet explained to the player in Act I |
| Minimap | Working | May be disabled or simplified in first-session route |
| Save slot select | Working | Default to slot 1 for Act I testing |

---

## What is scaffolded or experimental (do not test, do not judge)

These exist in the codebase for future acts. They should not appear in the G0 route.

| System | State |
| ------ | ----- |
| Boss AI (Siren, Echo Warden, Time Leech, Memory Eater) | Implemented; not triggered in Act I |
| Echo Art / SimEcho / EchoRecorder | Implemented; deferred until post-hollowing |
| Traversal Art (wall climb, grapple, teleport, phase step) | Partially implemented; hidden in Act I |
| Proof token mechanic (TOKEN_GATE, Labyrinth Court) | Scaffolded; not placed in Act I rooms |
| Hub 2 (Chasm of Still Shadows) | Defined; not accessible from Act I route |
| Full HubStateMachine arc (CORRUPTED, EMPTY) | Defined; not triggered in Act I |
| Advanced Yin/Yang meter tuning | Present; post-hollowing context needed first |

---

## What is frozen (do not report feature requests for these)

The following are intentionally frozen for the duration of Act I development.
Existing code remains but no new work will be done here.

| Area | Freeze reason |
| ---- | ------------- |
| Arcade mode | Frozen; not a current product direction |
| Sandbox mode | Removed from mode select |
| Co-op / multiplayer expansion | Frozen beyond regression safety |
| New procedural biome variety | Frozen unless it directly improves Act I readability |
| New crafting / economy depth | Frozen |
| New boss roster | Frozen |
| New replay features | Frozen beyond debug/regression support |
| Proof Tokens / Labyrinth Court | Deferred to post-hollowing |
| Ember Monastery systems | Deferred to post-hollowing |
| Winding Skyroad systems | Deferred to post-hollowing |

---

## What feedback we want right now

Focus all feedback on the G0 route above.

**High-value questions:**
- Did you understand where to go within 30 seconds of spawning?
- Did Yin and Yang feel like companions or like meters?
- Did Lantern Heights feel like a home or a loading screen?
- Did Linzi feel useful and flattering before she felt suspicious?
- Did you notice anything change in the hub after Linzi's influence?
- Did you complete the route without reading external instructions?
- Where did you feel confused, stuck, or bored?
- Did you want to continue after finishing the route?

---

## What feedback is out of scope right now

Do not report these yet — they belong to later development phases.

- Boss difficulty or balance
- Post-Act I traversal abilities
- Arcade or roguelike mode design
- Multiplayer / co-op balance
- Economy or crafting design
- Full Yin/Yang meter tuning
- Echo Art puzzle design
- Late-game narrative pacing

---

## Internal QA vs external tester instructions

**External testers:** Follow the G0 route above only. Do not enable debug overlays.
Controls: WASD / arrows to move, Space/Up to jump, X or Z to attack, E to interact,
Tab for map, Escape to pause.

**Internal QA:** The full keyboard reference and debug overlays (F1, F3, H, backtick)
remain available. See `docs/PLAYER_EXPECTATIONS.md` for the full QA control reference.
Use DEVELOPER mode for system-level testing. Use CAMPAIGN for Act I route testing.

---

## What to do if something breaks

1. Note the exact step in the G0 route where it broke.
2. Note what you did immediately before it broke.
3. Note any on-screen message, freeze, or unexpected behaviour.
4. Report to: `VainAsher/indie-ninja-feedback` (GitHub issues).

---

*Linked from: README.md, PLAYER_EXPECTATIONS.md, CURRENT_STATE.md*
*Canonical docs index: docs/INDEX.md*
