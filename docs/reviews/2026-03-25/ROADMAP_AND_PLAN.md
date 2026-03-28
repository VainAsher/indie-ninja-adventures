# Roadmap And Plan (2026-03-25)

This roadmap reflects the current codebase (v0.7.x) and the gaps identified in the deep dive. It is structured around stabilizing the playable loop, then expanding content and polish.

**Baseline (Now)**
- Core systems, procedural world, enemies, missions, inventory/trading, dialogue, and menu flows are implemented and wired.
- Boss encounters, ability gates, audio, and input remapping are not wired.
- Documentation is out of date versus the codebase.

**Milestone 0: Stabilization And Verification (2 weeks)**
Goal: Produce a reliable, verified playable loop with accurate documentation.

Deliverables
- Run the UAT suite and mark pass/fail results.
- Fix any P0 and P1 issues found (camera shake tuning, inventory flow, replay stability, map overlay).
- Align docs with reality (missions count, wall slide status, boss integration status).
- Add a build note or preflight check to prevent locked-file build failures.

Exit Criteria
- All P0 UATs pass.
- `docs/ROADMAP.md` and `docs/SYSTEM_OVERVIEW.md` updated to match actual systems.

**Milestone 1: Progression And Encounters (3-4 weeks)**
Goal: Make progression mechanics and boss encounters playable.

Deliverables
- Wire `entities/boss_manager.py` into the main loop and mission flow.
- Add boss missions in `data/missions.json` and objective tracking hooks.
- Integrate ability gates into level generation or hub transitions.
- Add basic boss visuals and collision feedback.

Exit Criteria
- Boss mission UAT passes with at least one boss encounter.
- Ability gate UAT passes with at least one gate type in a mission.

**Milestone 2: Presentation And Feedback (4-6 weeks)**
Goal: Improve visual clarity, feedback, and player experience.

Deliverables
- Expand sprite usage beyond rectangles for enemies and NPCs.
- Add particle and hit feedback for combat and collisions.
- Implement audio playback and wire volume settings.
- Add debug toggle for hitboxes and shuriken collision visuals.

Exit Criteria
- Combat feedback is clear (hit flashes, hit sounds, damage numbers if desired).
- Audio settings are functional and persistent.

**Milestone 3: Controls And Accessibility (4+ weeks)**
Goal: Modernize input and settings.

Deliverables
- Wire key binding settings into input handling.
- Add gamepad support.
- Expose accessibility toggles (text size, screen shake, high contrast).

Exit Criteria
- Input remapping UAT passes.
- Gamepad can complete a mission without keyboard.

**Backlog (Later)**
- Multiplayer foundation and netcode.
- Modding UI and editor.
- Advanced world variety and boss patterns.
- Performance optimizations and profiling passes.

**Immediate Next Actions (This Week)**
1. Run UAT suite and record results in `docs/reviews/2026-03-25/UAT_SUITE.md`.
2. Fix P0 failures and update `docs/reviews/2026-03-25/ISSUES_AND_RISKS.md`.
3. Update `docs/ROADMAP.md` and `docs/SYSTEM_OVERVIEW.md` based on this review.
