---
doc_type: system_doc
status: living
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# World Generation and Layout (Java)

## Scope

Deterministic room-graph generation, zone planning, tile synthesis, puzzle/ability postprocess, and hub world assembly.

## Primary Java owners

- Graph and room generation core:
  - `java/shadowascent/src/main/java/com/indieniinja/world/WorldGraph.java`
  - `java/shadowascent/src/main/java/com/indieniinja/world/WorldGenerator.java`
  - `java/shadowascent/src/main/java/com/indieniinja/world/ZonePlanner.java`
  - `java/shadowascent/src/main/java/com/indieniinja/world/RoomGenerator.java`
  - `java/shadowascent/src/main/java/com/indieniinja/world/SeedHierarchy.java`
  - `java/shadowascent/src/main/java/com/indieniinja/world/AutotileResolver.java`
- Postprocess pipeline:
  - `java/shadowascent/src/main/java/com/indieniinja/world/postprocess/RoomPostProcessor.java`
  - `java/shadowascent/src/main/java/com/indieniinja/world/postprocess/AbilityLayer.java`
  - `java/shadowascent/src/main/java/com/indieniinja/world/postprocess/PuzzleLayer.java`
  - `java/shadowascent/src/main/java/com/indieniinja/world/postprocess/EntityPlanner.java`
- Puzzle planning:
  - `java/shadowascent/src/main/java/com/indieniinja/world/puzzle/PuzzlePlanner.java`
  - `java/shadowascent/src/main/java/com/indieniinja/world/puzzle/PuzzlePlan.java`
- Server assembly/caching:
  - `java/server/src/main/java/com/indieniinja/server/ZoneSimulationLoop.java`
  - `java/server/src/main/java/com/indieniinja/server/RoomTileCache.java`
  - `java/server/src/main/java/com/indieniinja/server/WorldGraphRepository.java`

## Room Types

`WorldGraph.RoomType` enum. All types produce a wire string via `name().toLowerCase()` used as the room type key throughout the pipeline.

| Enum value       | Wire / id          | Template | Notes                              |
| ---------------- | ------------------ | -------- | ---------------------------------- |
| `START`          | `start`            | yes      | Player spawn room                  |
| `EXIT`           | `exit`             | yes      | Level exit                         |
| `SHOP`           | `shop`             | yes      | Merchant room (procedural layout)  |
| `SHOP_INTERIOR`  | `shop_interior`    | yes      | Merchant room (authored layout)    |
| `COMBAT`         | `combat`           | no       | Standard combat arena (procedural) |
| `COMBAT_STANDARD`| `combat_standard`  | yes      | Combat chamber (authored layout)   |
| `PLATFORM`       | `platform`         | no       | Platform challenge (procedural)    |
| `PLATFORM_ASCENT`| `platform_ascent`  | yes      | Vertical platform climb (authored) |
| `TREASURE`       | `treasure`         | no       | Vault (procedural)                 |
| `TREASURE_MAZE`  | `treasure_maze`    | yes      | Maze + high-loot (authored layout) |
| `BOSS`           | `boss`             | yes      | Boss arena (authored layout)       |

Template rooms resolve to `java/assets/rooms/templates/<id>.tmx`. Template-first lookup runs in both the `RoomTypeDefinition`-based path and the String-based `WorldGenerator` path. If no `.tmx` is found, generation falls through to procedural.

## Runtime flow

1. Generate `WorldGraph` from seed and shape — assigns `RoomType` to each `RoomNode`.
2. Build per-room zone grid (`ZonePlanner`) then tile grid (`RoomGenerator`/`WorldGenerator`).
   - Template types load their `.tmx` first; door openings carved by `carveDoors()`.
   - Non-template types go through `ZonePlanner` → `RoomGenerator` procedural path.
3. Apply postprocess/puzzle layers for gates, puzzles, and entity planning.
4. Stitch unified layout for simulation and snapshot descriptors.
5. Client renders tile output with blob autotile mapping and room metadata.

## Method-level call graphs

- Hub init graph:
  - `ZoneSimulationLoop.initSimulator(...)` -> `WorldGraph.generate(seed, rooms, shape)` (when `zone.worldGraph` is absent)
  - `ZoneSimulationLoop.initSimulator(...)` -> `buildUnifiedLayoutViaPostProcessor(graph, zone)` -> `LevelLayout.buildUnifiedWorldLayoutFromPlan(graph, puzzlePlan, masterHubId)`
  - Layout attach -> `new GameSimulator(graph.startRoom().seed, hubId, layout)`
- Puzzle/postprocess graph:
  - `ZoneSimulationLoop.buildUnifiedLayoutViaPostProcessor(...)` -> `PuzzlePlanner.plan(graph, worldSeed)`
  - `RoomPostProcessor.process(...)` -> `AbilityLayer.apply(...)` -> `PuzzleLayer.apply(...)` -> `EntityPlanner.computeSpawn(...)` -> `EntityPlanner.placeEnemies/placePickups/placeNpcs/placeBoss/placePortals/placeMovingPlatforms/placeFallingPlatforms`
- Room synthesis graph:
  - `WorldGenerator.generate(seed, cols, rows, neighborDirs, roomType)` -> `ZonePlanner.plan(...)` -> `RoomGenerator.generate(...)`
- Client tile role graph:
  - `ChunkRenderer` room-grid build -> `AutotileResolver.computeRole(grid2d, r, c, rows, cols)` -> `BlobTileSet.getFrame(...)`

## Contracts

- Generation is deterministic from seed and shape inputs.
- Room type and neighbor direction metadata are required for correct door/path topology.
- Server caches can accelerate tile and graph reconstruction without changing deterministic output.

## Legacy archive

Python/Pygame version is archived at:
`docs/archive/retired/2026-04-21_v0.11.71_python-systems-docs/WORLD_GEN.md`
