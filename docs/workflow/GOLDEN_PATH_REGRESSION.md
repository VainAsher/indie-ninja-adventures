---
doc_type: workflow
status: living
owner: qa-team
last_updated: 2026-04-18
version_anchor: v0.11.65
---

# Golden Path Regression

Reference documents:

- [BUG_REPRO_REPLAY_WORKFLOW.md](BUG_REPRO_REPLAY_WORKFLOW.md)
- [DAILY_SMOKE_WORKFLOW.md](DAILY_SMOKE_WORKFLOW.md)
- [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)

Canonical regression workflow for the smallest set of routes that must always remain valid.

## Rules

1. Golden paths must represent player-visible truth, not only subsystem truth.
2. Each golden path should be short enough to run routinely.
3. Goldens should prefer captured replays or scripted routes where possible.
4. Release candidates should not ship with a failing golden path.

## Golden Set (v0.11.65+)

Run each golden in order. A failure in any earlier golden does not skip later ones — record all failures independently.

### G1 — Hub Onboarding

1. `python launcher/launcher.py` → Play tab → CAMPAIGN
2. Confirm: Main Menu loads → Mode Select → in-game HUD
3. Siren dialogue triggers and first objective appears in mission tracker
4. Pass: HUD present, tracker shows objective, no crash or softlock

### G2 — First Mission (coin run)

1. Enter `demo_coin_run` world
2. Collect 5 coins — mission progress increments each time
3. Reach 5/5 — exit unlocks and is reachable
4. Pass: mission completes cleanly, exit traversable

### G3 — Movement Mastery

1. Perform: walk, run, crouch walk, jump, wall jump, dash
2. Each must be responsive and not clip, float, or judder
3. Verify `gravityFrozen` works: wall-climb and ledge-hang should not slide
4. Pass: all six movement states readable and stable

### G4 — Stance Posture in All Movement States

1. Press `A` to switch to **Yang** stance
2. Verify Yang shows **armed/sword posture** in: **idle, walk, jump, crouch, attack**
3. Press `A` to switch to **Yin** stance
4. Verify Yin shows **unarmed posture** in: **idle, walk, jump, crouch, attack**
5. Pass: both stances correct in **all five movement states**, not only during attack
6. Fail condition: any state that shows wrong posture — tag `TECH-ANIM`

### G5 — Hub Portal Travel (full checklist)

1. From spawn, confirm **no portal prompt near the start room** (exit-rooms only)
2. Reach an exit room, press `E` on portal — confirm `ENTERING: <HUB NAME>` toast
3. Confirm: world renders, camera is centred on player (not at world origin)
4. Press `E` on a **locked** portal without required ability — confirm lock toast, no travel
5. After successful travel, confirm **no spurious "new ability" toasts** for existing abilities
6. Confirm player health and inventory are intact on arrival
7. Pass: all six checks green — tag any failure as `UX-HUB` P0/P1

### G6 — Save / Quit / Reload

1. Play a session, acquire an item or ability
2. Quit via launcher
3. Relaunch — confirm progress is intact (same hub, same inventory)
4. Pass: persistence round-trip clean

### G7 — Replay Playback

1. Launch with `-Dninja.replayPath=<known good .ndjson>` via launcher Dev Tools
2. Confirm replay plays back deterministically to completion
3. Pass: no desync, playback completes, no save written

### G8 — Network Connect / Drop

1. Start server, connect second client, confirm sync
2. Drop second client — confirm server recovers, first client continues
3. Pass: no crash, no desync persisted

### Known-Regression Smoke Pairs

Run these any time the named system was touched that session:

| System touched | Must verify |
| --- | --- |
| `EntityRenderer` / stance / animation | G4 in full — all five states, both stances |
| `GameScreen.pollZoneTransition` / `handleSoloPortalTravel` | G5 in full — all six checklist items |
| `PhysicsSystem` / `gravityFrozen` | G3 wall-climb and ledge-hang |
| `SimPlayer` / abilities / `prevLocalAbilities` | G5 step 5 (no spurious toasts) |
| `LevelLayout` / room placement | G5 step 1 (no start-room portal) |
| Persistence / `HikariCP` / save shape | G6 |

## Canonical Loop

1. Select the current golden set.
2. Run each route or replay.
3. Record pass/fail and first failure point.
4. Fix any regression before release.
5. Update the golden inventory only when the core player path changes materially.

## Golden Record Minimum

- Golden ID
- Build/version
- Route or replay file
- Expected result
- Pass/fail
- First failure point
- Owner follow-up

## Done Criteria

- [ ] Core goldens executed
- [ ] Failures recorded with replay/log reference
- [ ] Release blocked on unresolved P0/P1 golden failures
- [ ] Golden inventory updated when onboarding, routing, or runtime contracts change

## Failure Path

If a golden path fails:

1. Treat the build as non-shippable until classified.
2. Link the failure to a bug ID or loop note.
3. Preserve the failing replay/log set.
4. Re-run the full golden set after the fix if the failure touched shared systems.

## Related Workflows

- [DAILY_SMOKE_WORKFLOW.md](DAILY_SMOKE_WORKFLOW.md)
- [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)
