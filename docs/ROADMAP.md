# Development Roadmap

Vain Asher Gaming's: Indie Ninja Adventures

Last Updated: 2026-03-28 | Version: 0.7.x | Status: Milestone 0 in progress

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

### What is not yet wired

| System | Status |
| --- | --- |
| Boss encounters | Code exists (`entities/boss_manager.py`); not wired into game loop or missions |
| Audio (SFX + music) | Not implemented |
| Key binding settings | Settings UI exists; wiring to input handler not implemented |
| Ability gate enforcement | Logic exists in `CampaignManager`; not enforced in hub transitions |

---

## Milestone 0: Stabilization (Current)

**Goal**: Reliable, verified playable loop with accurate documentation.

### Phase 0 — Bug Fixes (branch: fix/campaign-loop)

| Bug | Fix |
| --- | --- |
| Sprite flip during attack combos | Guard `on_wall` inversion behind attack-state check |
| Hurt animation freezes on last frame | Changed `hurt` animation to `loop=True` (matches i-frame duration) |
| Jump/fall frame indices swapped | Frame 0 = falling pose, frame 1 = ascending; corrected in animation system |
| Victory screen never triggers | `level_complete = True` + `victory_screen.reset()` now called on mission completion |
| Respawn without full health | `player.damage.respawn()` now called inside `regenerate_hub_for_respawn()` |
| Completing missions doesn't unlock further missions | `mission_def.unlock_abilities` now written to `campaign.unlocked_abilities` on completion |

### Phase 1 — Docs and UAT (branch: docs/m0-completion)

- [x] Rewrite `docs/HANDOVER.md` to v0.7.x reality
- [x] Rewrite `docs/ROADMAP.md` (this file)
- [ ] Update `docs/SYSTEM_OVERVIEW.md` to reflect current folder structure
- [ ] Fix wall slide status inconsistency across docs
- [ ] Add build preflight note to `build/` (warn about OneDrive/antivirus file locks)
- [ ] Create updated UAT suite (see [Testing and QA](#testing-and-qa))

Milestone 0 is done when:

- All P0 UATs pass
- Docs match actual systems
- Phase 0 bug fixes verified by playtesting

---

## Milestone 1: Progression and Encounters

**Goal**: Make boss encounters and ability gates playable.

What to build:

- Wire `entities/boss_manager.py` into the main game loop and mission flow
- Add boss missions in `data/missions.json` and objective tracking hooks
- Add basic boss visuals and collision feedback
- Enforce ability gates in hub transitions (require `unlocked_abilities` check)

Done when:

- At least one boss encounter is playable end-to-end via the mission system
- At least one ability gate blocks progression until the correct ability is unlocked

---

## Milestone 2: Audio and Presentation

**Goal**: Improve feedback, visual clarity, and add SFX audio.

What to build:

- Sound effect playback wired to game events (hit, death, pickup, mission complete)
- Volume settings functional and persistent via save system
- Expanded sprite usage for enemies and NPCs (move beyond rectangles)
- Combat feedback: hit flash, damage numbers (optional), particle polish
- Debug toggle for hitboxes and shuriken collision visuals

Note: music playback is deferred. SFX only for this milestone.

Done when:

- Combat feedback is clear (at minimum: hit sounds and screen flash)
- Audio volume settings persist between sessions

---

## Milestone 3: Controls and Accessibility

**Goal**: Modernize input and settings.

What to build:

- Wire key binding settings into input handler (settings UI already exists)
- Gamepad support
- Accessibility toggles (text size, screen shake, high contrast)

Done when:

- Input remapping works end-to-end
- Gamepad can complete a mission without keyboard

---

## Long-Horizon Goals

### Multiplayer

- Authoritative server / client prediction / lag compensation
- Co-op and versus modes
- Deterministic physics (already in place) enables replay-based networking

### Custom Launcher

- Downloads and verifies client, server, and mod bundles from GitHub
- Enforces version parity — mismatched builds cannot connect
- Supports mod browser, installation, and activation
- Platform targets: Windows primary; macOS/Linux stretch

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

| Risk | Severity | Mitigation |
| --- | --- | --- |
| Boss not wired into game loop | HIGH | Milestone 1 deliverable |
| Ability gates not enforced | MEDIUM | Milestone 1 deliverable |
| Audio not implemented | MEDIUM | Milestone 2 deliverable (SFX only) |
| Build lock (OneDrive/antivirus) | MEDIUM | Preflight note added to build/ |
| Wall slide docs inconsistency | LOW | Fixed in Milestone 0 Phase 1 |
| Raycast test coverage gap | LOW | Backlog |
| Shuriken always visible (no fire) | LOW | Backlog |

---

Dependencies: pygame 2.6.1, Pillow, PyInstaller, Python 3.11+
