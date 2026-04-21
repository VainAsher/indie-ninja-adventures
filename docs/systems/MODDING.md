---
doc_type: system_doc
status: living
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Modding Status (Java)

## Scope

Current Java extensibility state and what is or is not supported for runtime modding.

## Current status

There is no Java runtime mod loader equivalent to the legacy Python mod system.

## Available extension seams (internal/developer use)

- `java/core/src/main/java/com/indieniinja/core/EntityTypeRegistry.java`
- `java/core/src/main/java/com/indieniinja/content/ContentRegistry.java`
- `java/core/src/main/java/com/indieniinja/content/ContentLoader.java`
- `java/shadowascent/src/main/java/com/indieniinja/world/postprocess/*`

These are code/content extension points for engine/game modules, not end-user hot-load mods.

## Method-level call graphs

- Content bootstrap graph:
  - `NinjaGameServer` startup -> `new ContentLoader(dataRoot).loadAll()` -> `loadEnemies/loadNpcs/loadRoomTypes` -> `parseAndValidate(...)` -> `ContentRegistry.registerEnemy/registerNpc/registerRoomType`
  - `ZoneSimulationLoop.initSimulator(...)` -> `GameSimulator.setContentRegistry(registry)` (runtime read side)
- Entity type bootstrap graph:
  - Startup integration point -> `ShadowAscentEntityTypeBootstrap.register(EntityTypeRegistry)` -> repeated `EntityTypeRegistry.register(id, baseType)` calls -> runtime lookups via `EntityTypeRegistry.get(...)`
- World extension graph:
  - `ZoneSimulationLoop.buildUnifiedLayoutViaPostProcessor(...)` -> `LevelLayout.buildUnifiedWorldLayoutFromPlan(...)` -> `RoomPostProcessor.process(...)` -> `AbilityLayer.apply(...)` -> `PuzzleLayer.apply(...)` -> `EntityPlanner.place*`

## Operational guidance

- Treat Java modding as "compile-time extension" at this stage.
- Route user-facing customization through data/content definitions and tooling pipelines.
- Do not document Python `core/mod_system.py` behavior as active for Java runtime.

## Legacy archive

Python/Pygame version is archived at:
`docs/archive/retired/2026-04-21_v0.11.71_python-systems-docs/MODDING.md`
