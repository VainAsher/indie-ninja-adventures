# Development Roadmap

Vain Asher Gaming's: Indie Ninja Adventures

Last Updated: 2026-03-30 | Version: 0.8.0 | Status: Milestones 0–2 complete; M3 partial; Phase 3a complete

---

## Vision

A fast-paced, skill-based 2D ninja platformer with:

- Tight, responsive controls and deep movement mechanics
- Story-driven campaign with progression, NPCs, and ability unlocks
- Procedural world generation across 7 biome themes
- Deterministic physics supporting replay and — ultimately — networking
- Online multiplayer distributed via a custom launcher

The launcher end goal: players download and verify client, server, and mod bundles from GitHub, with version parity enforced so mismatched builds cannot connect.

---

## Current State (v0.7.x)

The codebase has grown from ~50 files (Dec 2025) to 120+ files. Most systems described as "next steps" in the original Dec 2025 handover are now implemented and wired.

### What works

| System | Status |
| --- | --- |
| Core infrastructure (event bus, clock, state, entity system, mod system) | Done |
| Collision + physics (AABB, swept, platforms, corners) | Done |
| Player mechanics (movement, jump, dash, crouch, wall slide, combat, shuriken, teleport, ninjutsu) | Done |
| Procedural world generation — 7 biomes (dungeon, cave, building, forest, town, sewer, hollow) | Done |
| Enemies (goblin, bat, slime, skeleton, wolf) + enemy AI | Done |
| Hazards (spikes, lava, poison, void) | Done |
| Campaign system (6 regions, 30 missions, ability gates, NPC dialogue) | Done |
| Mission objectives + objective tracker + exit unlock | Done |
| Inventory, trading, loot systems | Done |
| Story manager + dialogue system + cutscene manager | Done |
| Save system (JSON persistence) | Done |
| Animation state machine (sprite sheets, autotiling) | Done |
| HUD (health, objectives, minimap, full map overlay) | Done |
| Victory screen, pause menu, settings menu | Done |
| Input pipeline (command pattern, record/replay) | Done |
| Camera (world clamp, room clamp, free; letterboxing) | Done |
| Particle system (dust, dash, impact) | Done |

### Recently completed (2026-03-28)

| System | Status |
| --- | --- |
| Boss encounters | ✅ BossManager wired; 6 boss missions in campaign; gate enforcement active |
| Audio SFX | ✅ AudioManager + pygame.mixer wired; 12 SFX events hooked throughout game loop |
| Key binding settings | ✅ Settings strings → pygame constants → Player.set_key_bindings() live |
| Ability gate enforcement | ✅ sync_player_abilities() + _rebuild_hub_gates() wired |
| Fullscreen toggle | ✅ camera.handle_resize() called post-toggle (crash fixed) |
| Portal height gating | ✅ Forest portal at floor level (basic jump); Town portal elevated (double_jump) |

### Still not implemented

| System | Status |
| --- | --- |
| Boss AI behaviour | Framework + 6 types exist; no AI patterns, no phase transitions |
| Music / BGM | AudioManager supports it; not implemented |
| Gamepad support | Not started |

---

## Milestone 0: Stabilization ✅ COMPLETE

All six Phase 0 bugs fixed. Docs aligned to v0.7.x reality.

| Bug | Fix |
| --- | --- |
| Sprite flip during attack combos | Wall inversion guarded behind attack-state check |
| Hurt animation freezes on last frame | `loop=True` (matches i-frame duration) |
| Jump/fall frame indices swapped | Corrected in animation system |
| Victory screen never triggers | `level_complete = True` on mission completion |
| Respawn without full health | `player.damage.respawn()` inside `regenerate_hub_for_respawn()` |
| Completing missions doesn't unlock further missions | `mission_def.unlock_abilities` written on completion |

**Outstanding M0 item**: UAT result columns in `UAT_SUITE.md` still blank. Run a manual playtest pass to fill them in.

---

## Milestone 1: Progression and Encounters ✅ COMPLETE

BossManager wired into game loop. 6 boss missions added to `data/missions.json`. `_rebuild_hub_gates()` enforces ability gates in hub portals. `sync_player_abilities()` restricts mechanics to earned abilities on campaign start and each unlock.

**Outstanding M1 item**: Boss AI behaviour not implemented. Boss spawns in boss missions but has no attack patterns or phase transitions. The `entities/boss_ai.py` framework exists and needs implementation.

---

## Milestone 2: Audio and Presentation ✅ COMPLETE (SFX)

`audio/audio_manager.py` wraps `pygame.mixer`. 12 SFX events wired throughout game loop (combat, movement, pickups, UI). SFX Volume cycling in SettingsMenu persists via `GameSettings.save()`. 12 placeholder WAV files in `assets/audio/sfx/` (replace with real audio).

**Outstanding M2 item**: Music / BGM not implemented. The AudioManager has capacity for it; needs BGM files and loop wiring.

---

## Milestone 3: Controls and Accessibility 🔶 PARTIAL

Key bindings, fullscreen, sfx_volume, and show_hitboxes all wired via `apply_runtime_settings()`. Settings persist.

**Outstanding M3 items**:

- Gamepad support (pygame.joystick not integrated)
- Accessibility toggles (text size, high contrast, reduce motion)

---

## Infrastructure (v0.8.0) ✅ COMPLETE

4-repo pipeline architecture and structured feedback workloop. See [docs/workflow/](workflow/) for
sprint, branching, and release processes.

| Repo | Status |
|------|--------|
| `VainAsher/indie-ninja-launcher` (public) | Scaffold ready — create repo |
| `VainAsher/indie-ninja-adventures` (private) | Active — this repo |
| `VainAsher/indie-ninja-feedback` (public) | Scaffold ready — create repo |
| `VainAsher/indie-ninja-pipeline` (private) | Scaffold ready — create repo |

One-time setup: see "One-Time Setup Actions" section in `docs/repo-scaffolds/pipeline-repo/README.md`.

---

## Long-Horizon Goals

### Multiplayer (Phase 3b+)

- Phase 3b: Client-side prediction + server reconciliation
- Phase 3c: Lag compensation, rollback netcode
- Co-op and versus modes
- Version parity enforcement (mismatched builds cannot connect)

### Custom Launcher (v1.x)

- Mod browser, installation, and activation
- Platform targets: Windows primary; macOS/Linux stretch
- Launcher repo: `VainAsher/indie-ninja-launcher`

### Advanced Features (Backlog)

- In-game level editor
- Procedural daily challenges with seeds and leaderboards
- Ghost replay recording/playback for speedrunning
- Advanced world variety and boss patterns

---

## Testing and QA

See `tests/` for the current test suite.

### Running Tests

```bash
python -m pytest tests/ -q          # all tests
python -m pytest tests/unit/ -q     # unit tests only
python -m pytest tests/ -x -q       # stop on first failure
```

### UAT Coverage (to be written in Milestone 0 Phase 1)

- Campaign loop: mission start → complete → victory screen → hub return
- Mission unlock chain: complete `forest_1` → `double_jump` unlocked → `forest_2` available
- Respawn: die in mission → return to hub with full health
- Animation: hurt loops during i-frames, jump/fall frames correct, no flip during attack
- Boss encounter: XFAIL (pending Milestone 1)
- Ability gate: XFAIL (pending Milestone 1)
- SFX on hit/death/pickup: XFAIL (pending Milestone 2)

---

## Technical Notes

### Build

```bash
# Windows production build (from build/ directory)
python build.py
```

**Preflight**: Close OneDrive sync and pause antivirus before building. Both can lock the output EXE and cause PyInstaller to fail with a permissions error.

### Key Entry Points

| File | Purpose |
| --- | --- |
| [demo_game.py](../demo_game.py) | Main executable |
| [game/game_initialization.py](../game/game_initialization.py) | All managers wired here |
| [data/missions.json](../data/missions.json) | Mission definitions |
| [assets/biomes/](../assets/biomes/) | Tile assets per biome |

---

## Risk Register

| Risk | Severity | Status |
| --- | --- | --- |
| Boss AI not implemented | HIGH | Active — framework exists; needs AI patterns |
| Music / BGM absent | MEDIUM | Active — AudioManager ready; needs BGM files |
| Gamepad not supported | MEDIUM | Active — no joystick integration |
| UAT results blank | MEDIUM | Active — needs manual playtest pass |
| Build lock (OneDrive/antivirus) | MEDIUM | Mitigated — preflight note in `build/` |
| Shuriken collision box always visible | LOW | Backlog |
| Raycast test known failure | LOW | Pre-existing; low impact |

---

Dependencies: pygame 2.6.1, Pillow, PyInstaller, Python 3.11+
