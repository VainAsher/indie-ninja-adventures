---
doc_type: plan
status: implementing
owner: core-team
last_updated: 2026-05-03
version_anchor: v0.13.31
---

# PLAN — Procedural Generation Lab

Standalone Java prototype proving a layered, intent-driven procedural generation
system for story-scoped metroidvania worlds, regions, dungeons, rooms, and validated
traversal. Implemented as a separate Gradle module (`java/procgen-lab/`) with no
dependency on the live game modules.

**Design doc:** See the full PDD shared in session (pasted inline by user 2026-05-03).
**Package root:** `com.indieniinja.procgen`
**Room dimensions:** 128×128 tiles (16×16 zones × 8×8 stamp) — aligned to live game.

---

## Decisions on record

| Decision | Choice | Reason |
|----------|--------|--------|
| Package root | `com.indieniinja.procgen` | Match existing repo convention (double `i`) |
| Room tile dimensions | 128×128 | Align to live game `RoomGenerator` output size |
| Zone grid | 16×16 zones | 128 / 8 = 16 both axes |
| General alignment | Match live game conventions where integration is plausible | User directive |

---

## Slices

### S1 — Gradle skeleton + core data model ✅
*Spec §7, §8, §9*

- [x] `java/procgen-lab/build.gradle.kts` — new module, no game deps
- [x] `java/settings.gradle.kts` — add `:procgen-lab`
- [x] `model/` package: `Tile`, `GenConfig`, `ZoneCell` + all enums
- [x] `intent/` package: `WorldIntent`, `RegionIntent`, `DungeonIntent`, `RoomIntent`
- [x] `Main.java` skeleton
- [x] `GenConfigTest` — constants sanity, room dimensions

---

### S2 — Macro planners (WorldPlan, RegionPlan, DungeonPlan, RoomGraph) ✅

*Spec §10, §11, §12*

- [x] `macro/WorldPlanner` + `WorldPlan`
- [x] `macro/RegionPlanner` + `RegionPlan`
- [x] `model/MapNode` + `MapNodeType`
- [x] `dungeon/DungeonPlanner` + `DungeonPlan`
- [x] `dungeon/RoomNode` + `RoomGraph`
- [x] Tests: DungeonPlannerTest (≥8 rooms, treasure/boss/exit exist) — 10 tests pass

---

### S3 — Room generation passes 1–6 (fill → tile stamp) ✅

*Spec §13, §14.1–14.6, §15, §16*

- [x] `passes/SolidFillPass`
- [x] `passes/CarvePass` (+ `TraversalGoal` constants)
- [x] `passes/DoorPass`
- [x] `passes/SurfaceClassificationPass`
- [x] `passes/FillVariantPass` + `rules/FillVariantRule` interface + 6 rule implementations
- [x] `passes/TileStampPass` + `stamps/Stamp` interface + 9 stamp implementations
- [x] `room/GeneratedRoom` + `room/RoomGenerationReport` + `room/RoomGenerator` (passes 7–10 stubbed)
- [x] Tests: SolidFillPassTest, CarvePassTest, DoorPassTest, TileStampPassTest, RoomGeneratorPassOrderTest — 23 tests pass

---

### S4 — Passes 7–10 + traversal validation + regeneration ✅

*Spec §14.7–14.9, §17, §18*

- [x] `passes/TraversalFeaturePass`
- [x] `passes/GameplayFeaturePass`
- [x] `passes/DecorationPass`
- [x] `room/RoomGenerator` (orchestrates all passes)
- [x] `validation/TraversalValidator` + `ValidationResult`
- [x] Regeneration loop (20 retries, derived seeds)
- [x] Tests: TraversalValidatorTest (dash room pass/fail) — 51 tests pass

---

### S5 — Swing UI skeleton + one-room tile view ✅

*Spec §20.1–20.5, §20.11 UI Phase 1–2*

- [x] `ui/ProcgenLabFrame`
- [x] `ui/ToolBarPanel` (seed field, regenerate, new seed, view mode combo)
- [x] `ui/RenderPanel` (tile view, 4px-per-tile color palette)
- [x] `ui/LogPanel` (monospace pass log + error list)
- [x] `ui/UiController` (seed state, regenerate, change listeners)
- [x] `ui/ViewMode` enum (TILES, ZONES, SURFACE, VARIANT, VALIDATION)
- [x] `runLab` Gradle task wired — opens the lab window
- [x] 51 tests still pass

---

### S6 — Full view modes, hierarchy, inspector, validation overlay ✅

*Spec §20.6–20.9 UI Phase 3–6*

- [x] `ui/HierarchyPanel` (JTree world→region→dungeon→room, click selects room)
- [x] All zone/surface/variant/validation render modes in `RenderPanel`
- [x] `ui/InspectorPanel` (zone cell base/surface/variant/criticalPath detail)
- [x] `ui/SelectionModel` (zone click → inspector + selection overlay)
- [x] Validation overlay (unreachable traversable tiles highlighted red)
- [x] Mouse zone selection with yellow border overlay
- [x] `ValidationResult.reachable` grid populated by `TraversalValidator`
- [x] `RoomGenerationReport.validation` typed as `ValidationResult`
- [x] 51 tests still pass

---

### S7 — Map system + export UI ✅

*Spec §19, §20.10 UI Phase 7*

- [x] `map/WorldMapRenderer`
- [x] `map/RegionMapRenderer`
- [x] `map/DungeonMapRenderer` (with selected-room highlight)
- [x] `map/RoomMinimapRenderer` (1-px-per-tile minimap)
- [x] `ui/ExportDialog` (Tiled JSON + LDtk)
- [x] Export button in toolbar; dungeon map + minimap thumbnails in frame
- [x] 51 tests still pass

---

### S8 — Quest generation layer ✅

*Spec §21*

- [x] `model/` quest enums: `QuestType`, `QuestObjectiveType`, `QuestStatus`, `RewardType`
- [x] `quest/Quest` + `QuestObjective` + `QuestReward` + `QuestPlan`
- [x] `quest/QuestGenerator` — main/side/optional quests from DungeonPlan
- [x] `quest/QuestValidator` — objective room IDs verified against dungeon graph
- [x] `quest/FeatureRequest` wired into `GameplayFeaturePass` (overload) + `RoomGenerator`
- [x] `DungeonPlan.questPlan` typed as `QuestPlan` (was `Object` placeholder)
- [x] `UiController` generates and assigns `QuestPlan` on every regeneration
- [x] `QuestGeneratorTest` — 6 tests; total suite: 57 tests, all pass

---

### S9 — Runtime integration with live game ✅

*Runtime adoption: tile constant alignment + LevelLayout converter + feature flag*

- [x] `model/Tile` constants realigned to match live `WorldGenerator` (WATER=4, LAVA=5, LOCKED_DOOR=6, SPIKES=13, DOOR=14; CLIMBABLE=8 unchanged)
- [x] `:shadowascent/build.gradle.kts` — `implementation(project(":procgen-lab"))`
- [x] `LevelLayout.fromProcgenRoom(GeneratedRoom, long)` — full converter: 1:1 tile mapping (128×128 @ 32px), spawn extraction (PICKUP→PickupSpawn, ENEMY_SPAWN→EnemySpawn, BOSS_SPAWN→BossSpawn, SAVE_POINT→NPCSpawn), DOOR→AIR, SPIKES→LAVA
- [x] `LevelLayout.buildProcgenGrid(seed, cols, rows, neighborDirs, roomType)` — transposes procgen column-major grid to live row-major; maps wire roomType → RoomType enum
- [x] `LevelLayout.buildProceduralLayout` gated: `ninja.runtime.useProcgenRooms=true` routes tile grid through `buildProcgenGrid`; all spawn logic unchanged; kill-switch is flag=false
- [x] `ninja.runtime.useProcgenRooms` flag added to `PLAN_WORLDGEN_RUNTIME_ADOPTION.md` flag table
- [x] `LevelLayoutProcgenTest` — 4 tests: solidTilesHaveTileRects, tilePositionsUse32pxScale, waterTileUsesLiveWaterConstant, bossRoomProducesBossSpawn
- [x] 57 procgen-lab tests still pass after tile constant realignment

---

## Acceptance gates per slice

Each slice ships only when:
- [x] Compiles clean (`./gradlew :procgen-lab:build`)
- [x] Named tests pass (57 procgen-lab + 4 LevelLayoutProcgenTest, all green at S9 completion)
- [x] No class or method stubs left in completed scope
