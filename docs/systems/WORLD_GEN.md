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

## Runtime flow

1. Generate `WorldGraph` from seed and shape.
2. Build per-room zone grid (`ZonePlanner`) then tile grid (`RoomGenerator`/`WorldGenerator`).
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
