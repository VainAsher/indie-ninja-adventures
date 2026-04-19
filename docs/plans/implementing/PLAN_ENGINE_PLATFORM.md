---
doc_type: plan
status: implementing
owner: core-team
last_updated: 2026-04-19
version_anchor: v0.11.66
---
# PLAN — Engine Platform Implementation
## Shadow Ascent → Reusable 2D Game Engine
**Created:** 2026-04-18 | **Codebase baseline:** v0.11.66 | **Plan type:** Additive (no existing systems removed or rewritten)

---

## How to Read This Plan

Each task: what to build, files, interface contract, acceptance criteria, effort estimate.
Commit format: `type(plan_id=ENG-XX scope=<layer> risk=<low|med|high>): description`

---

## Phase Dependency Map

```
A1 (ContentLoader/Defs)
  └─→ A2 (EnemyRegistry)        ─┐
  └─→ A3 (RoomTypeRegistry)      ├─→ C1 (:shadowascent module)
  └─→ A4 (GameConfig)            │       └─→ C2 (EntityTypeRegistry)
  └─→ A5 (Animation Manifest)    │               └─→ C3 (:engine artifact)
                                  │
B1 (Tiled Integration)   ────────┘
B2 (Yarn Spinner)
B3 (Dev Console)         ─→ A5 (hot-reload needs manifest)
B4 (Asset Pipeline)      ─→ A5 (pipeline produces manifest inputs)

D1 (Save Multi-Slot)     — independent
D2 (Perf Regression CI)  — independent
D3 (Save Checksums)      — independent
D4 (Java in CI)          — independent, first D task
```

---

## PHASE A — Content Definition Foundation

### A1 — Entity Definition JSON Format + ContentLoader
**Task ID:** ENG-A1 | **Effort:** 5 team-days | **Dependencies:** None

- [x] All enemy definitions in `data/entities/enemies/*.json`
- [x] All NPC definitions in `data/entities/npcs/*.json`
- [x] All room type definitions in `data/entities/rooms/types/*.json`
- [x] JSON schemas in `data/schemas/`
- [x] `ContentLoader.java` — loads + validates all defs
- [x] `ContentRegistry.java` — typed lookup API
- [x] `EnemyDefinition.java`, `NpcDefinition.java`, `RoomTypeDefinition.java` records
- [x] Server startup wires `ContentLoader.loadAll()`
- [x] `json-schema-validator` added to `:core/build.gradle.kts`
- [x] `ContentLoaderTest`, `ContentRegistryTest` pass

### A2 — EnemyDefinitionRegistry (Replaces buildEnemy() Switch)
**Task ID:** ENG-A2 | **Effort:** 3 team-days | **Dependencies:** A1

- [x] `GameSimulator.buildEnemy()` switch replaced with `contentRegistry.getEnemy()`
- [x] `EntityRenderer.enemySize()` / `enemyPhysicsH()` switches replaced
- [x] `EnemyAiProfile` enum defined (STANDARD, AERIAL, RANGED)
- [x] All existing `GameSimulatorTest` still pass

### A3 — RoomTypeRegistry (Replaces ZonePlanner/RoomGenerator Switches)
**Task ID:** ENG-A3 | **Effort:** 4 team-days | **Dependencies:** A1

- [x] `ZonePlanner` room type switch replaced with `contentRegistry.getRoomType()`
- [x] `RoomGenerator.decorateRoom()` consumes `RoomTypeDefinition`
- [x] `RoomType` enum `id()` method added
- [x] `WorldGraphGenerationTest` and `WorldGraphTest` still pass

### A4 — GameConfig Class
**Task ID:** ENG-A4 | **Effort:** 2 team-days | **Dependencies:** None

- [x] `GameConfig.java` created with all balance constants
- [x] `SimPlayer`, `SimEnemy`, `GameSimulator` reference `GameConfig` constants
- [x] All existing tests still pass

### A5 — Animation Manifest Format + Loader
**Task ID:** ENG-A5 | **Effort:** 5 team-days | **Dependencies:** None

- [x] `assets/animations/manifest.json` covers all entities
- [x] `AnimationRegistry` loads from manifest
- [x] `inheritsFrom` inheritance works
- [ ] `tools/validate_animation_manifest.py` zero errors
- [x] Hot-reload stub in `AnimationRegistry.reload()`

---

## PHASE B — Authoring Tools

### B1 — Tiled Map Editor Integration
**Task ID:** ENG-B1 | **Effort:** 6 team-days | **Dependencies:** A1, A3

- [x] `TmxRoomLoader.java` created
- [x] 4 initial template `.tmx` files authored
- [x] `RoomGenerator` falls back gracefully when template absent
- [x] `docs/dev/TILED_SETUP.md` written
- [x] `tools/validate_room_templates.py` created

### B2 — Yarn Spinner Dialogue Integration
**Task ID:** ENG-B2 | **Effort:** 6 team-days | **Dependencies:** None

- [x] `tools/dialogues_json_to_yarn.py` converter written
- [x] All dialogue trees converted to `.yarn` format
- [x] `DialogueManager` loads compiled Yarn output
- [x] Siren dialogue tree behavior identical before/after

### B3 — In-Game Developer Console
**Task ID:** ENG-B3 | **Effort:** 5 team-days | **Dependencies:** A4, A5

- [x] `DevConsole.java` created with backtick toggle
- [x] All required commands implemented
- [x] Hot-reload wired to `ContentLoader` and `AnimationRegistry`
- [x] Invisible and no-op in release builds (`-Prelease`)
- [x] Does not appear in multiplayer mode

### B4 — Gradle Asset Pipeline Task
**Task ID:** ENG-B4 | **Effort:** 4 team-days | **Dependencies:** A5

- [x] `assets/asset_manifest.json` created
- [x] `buildAssets` Gradle task registered
- [x] `tools/asset_pipeline.py` orchestrator written
- [ ] CI uploads asset pipeline report artifact

---

## PHASE C — Engine Module Extraction

### C1 — :shadowascent Module
**Task ID:** ENG-C1 | **Effort:** 8 team-days | **Dependencies:** A1, A2, A3

- [x] `java/shadowascent/` module created
- [x] Game-specific sim/world classes moved
- [x] `:core` compiles independently of `:shadowascent`
- [x] `settings.gradle.kts` declares `:shadowascent`
- [x] All existing tests pass after move

### C2 — EntityTypeRegistry
**Task ID:** ENG-C2 | **Effort:** 4 team-days | **Dependencies:** C1

- [x] `EntityTypeRegistry.java` in `:core`
- [x] `ShadowAscentEntityTypeBootstrap` in `:shadowascent`
- [ ] All entity creation in sim goes through registry

### C3 — :engine Artifact Publication
**Task ID:** ENG-C3 | **Effort:** 2 team-days | **Dependencies:** C1, C2

- [x] `maven-publish` plugin configured in `:core/build.gradle.kts`
- [ ] Artifact publishes to GitHub Packages

---

## PHASE D — Hardening

### D4 — Java Tests in CI (First D Task)
**Task ID:** ENG-D4 | **Effort:** 1 team-day | **Dependencies:** None

- [ ] `.github/workflows/ci.yml` runs `./gradlew test`
- [ ] Test results uploaded as artifact

### D1 — Save Multi-Slot
**Task ID:** ENG-D1 | **Effort:** 3 team-days | **Dependencies:** None (independent)

- [ ] Save slot selection UI exists
- [ ] Multiple named save slots supported
- [ ] Schema migration from single-slot

### D2 — Perf Regression CI
**Task ID:** ENG-D2 | **Effort:** 2 team-days | **Dependencies:** None

- [ ] Benchmark baseline recorded
- [ ] CI fails if tick duration regresses > 10%

### D3 — Save Checksums
**Task ID:** ENG-D3 | **Effort:** 2 team-days | **Dependencies:** None

- [ ] Save file checksum written on save
- [ ] Checksum validated on load — corrupt file detected with clear error

---

## Completed Tasks

- **ENG-A1** — Content definition JSON format + ContentLoader (2026-04-19)
- **ENG-A2** — EnemyDefinitionRegistry (2026-04-19)
- **ENG-A3** — RoomTypeRegistry (2026-04-19)
- **ENG-A4** — GameConfig class (2026-04-19)
- **ENG-A5** — Animation manifest format + loader (2026-04-19) *(validate_animation_manifest.py pending)*
- **ENG-B1** — Tiled map editor integration (2026-04-19)
- **ENG-B2** — Yarn Spinner dialogue integration (2026-04-19)
- **ENG-B3** — In-game developer console (2026-04-19)
- **ENG-B4** — Gradle asset pipeline task (2026-04-19) *(CI artifact upload pending)*
- **ENG-C1** — :shadowascent module extraction (2026-04-19)
- **ENG-C2** — EntityTypeRegistry + ShadowAscentEntityTypeBootstrap (2026-04-19)
- **ENG-C3** — maven-publish configured (2026-04-19) *(publish verified pending CI credentials)*
