# Issues And Risks (2026-03-25)

This list is based on code review plus the recent playtest feedback in this thread. Items are grouped by severity and include evidence paths.

**Critical**
- None confirmed by code review in this pass.

**High**
- Boss encounters are not integrated into gameplay. The boss system exists in `entities/boss.py`, `entities/boss_ai.py`, and `entities/boss_manager.py`, but is not wired into `demo_game.py` or `game/game_initialization.py`. Missions also lack boss metadata in `data/missions.json`. Impact: no boss fights despite story and objective hooks.

**Medium**
- Ability gates are not integrated. `entities/ability_gate.py` is unused in the game loop and not referenced in world or level generation. Impact: progression gating not functional.
- Settings are only partially wired. `config/settings.py` contains key bindings, fullscreen, vsync, and show_hitboxes, but input and display code do not use them. Impact: settings menu cannot affect these options at runtime.
- Audio system is missing. No sound playback code was found in the runtime path. Impact: silent game despite settings fields.
- Documentation is materially out of date. `docs/ROADMAP.md`, `docs/SYSTEM_OVERVIEW.md`, and `docs/FEATURES_V0_7.md` conflict with code (missions count, wall slide status, boss AI integration). Impact: confusion for contributors and planning.
- Wall slide status inconsistency. Docs state disabled, but `mechanics/wall_slide.py` is active by default and invoked in `entities/player.py`. Impact: unclear intended behavior and tuning conflicts with fallback wall friction.
- Production build can fail if output files are locked (access denied). The build log in this thread shows `dist` cleanup failing. Impact: build pipeline intermittently blocked when exe is running or files are locked by OneDrive or antivirus.

**Low**
- Raycast test was previously known to fail per `docs/PHASE_3-6_COMPLETION_SUMMARY.md`. Impact: test signal noise and potential collision regression risk.
- Shuriken collision box is always visible. Rendering is now on by default in `demo_game.py`, which is useful for debugging but might be undesirable in normal play.

**Needs Verification (recent fixes)**
- Camera shake intensity and decay are still perceived as intrusive. Code was tuned, but requires playtest validation in `systems/camera_system.py` and `game/game_initialization.py`.
- Inventory navigation and equip/use flow were rewired in `ui/inventory_ui.py` and `demo_game.py`; verify controller feel and item effects.
- Game state order now starts in menu by default; verify that no modes bypass the menu unintentionally in `demo_game.py`.
- Full map overlay sizing and centering updated in `demo_game.py`; verify layout at common resolutions.
- Playtest crash from `update_replay_metadata` call was fixed in `demo_game.py`; confirm no crash in playtest flow.

**Risks**
- Onefile PyInstaller resource access relies on `get_resource_path`. Any remaining hardcoded paths (if introduced later) may break packaged builds.
- Input remapping and gamepad support are not present, which may block accessibility goals.
