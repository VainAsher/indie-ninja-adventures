---
doc_type: system_doc
status: living
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.13.7
---

# World Generation and Layout (Java)

## Scope

Deterministic room-graph generation, zone planning, tile synthesis, puzzle/ability postprocess, and hub world assembly.

For hands-on room, zone, and level-design workflow, see `docs/guides/LEVEL_AUTHORING_GUIDE.md`.

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

Template rooms resolve through `data/room_template_catalog.json` first, then fall back to `java/assets/rooms/templates/<id>.tmx` and sorted `<id>_*.tmx` / `<id>-*.tmx` convention variants. Template-first lookup runs in both the `RoomTypeDefinition`-based path and the String-based `WorldGenerator` path. If no `.tmx` is found, generation falls through to procedural.

## Runtime flow

1. Generate macro progression graph from seed — assigns central hub, region hubs, dungeon nodes, requirements, grants, optional branches, and critical path.
2. Generate legacy `WorldGraph` from seed and shape — assigns `RoomType` to each `RoomNode`.
3. Build per-room zone grid (`ZonePlanner`) then tile grid (`RoomGenerator`/`WorldGenerator`).
   - Template types load a seed-selected `.tmx` variant first; door openings carved by `carveDoors()`.
   - Non-template types go through `ZonePlanner` → `RoomGenerator` procedural path.
   - `RoomStructureRules` drives room-level zone grammar before zones expand into 8x8 tile templates.
   - `RoomGeometryRules` and `RoomGeometryEnforcer` apply shared wall, floor, and door-corridor rules to both procedural rooms and loaded TMX templates.
4. Apply postprocess/puzzle layers for gates, puzzles, and entity planning.
5. Stitch unified layout for simulation and snapshot descriptors.
6. Client renders tile output with blob autotile mapping and room metadata.

## Progression graph layer

`WorldProgressionGenerator.generate(worldSeed)` creates the macro progression
graph above room placement. This is a pure model layer in
`com.indieniinja.world.progression`; it does not yet alter server runtime,
`WorldGraph` persistence, room layout, or tile generation.

Current model responsibilities:

| Model | Purpose |
| ----- | ------- |
| `WorldProgressionGraph` | Container for central hub, region hubs, dungeon nodes, critical path, and snapshot serialization. |
| `WorldProgressionGenerator` | Deterministic world-seed generator for macro progression beats. |
| `ProgressionValidator` | Solvability check that walks reachable nodes while accumulating grants. |
| `ProgressionValidationResult` | Validation outcome, reachable ids, collected grants, and blocked required nodes. |

The generated graph contains:

- `central_hub` as the root.
- 3-4 region hubs selected deterministically from the world seed.
- required dungeon beats per region: entry, trial, gate, and boss.
- optional treasure branches.
- ability/key-style grants that appear before later requirements.

The validator requires every non-optional node to become reachable from
`central_hub`. Optional nodes may remain gated, but current generated optional
treasure branches are also reachable after their region grant.

This layer is intentionally above `WorldGraph`. Later section/layout slices will
consume it to choose authored section templates and spatial structure.

## Snapshot export

`WorldGenerationSnapshotCommand` exports a deterministic JSON snapshot for a
seed, room count, and graph shape:

```bash
cd java
./gradlew.bat :shadowascent:worldgenSnapshot -Pseed=12345 -Prooms=20 -Pshape=BLOB "-Pout=build/worldgen-snapshots/seed-12345.json" --no-daemon
```

The command writes:

| Field | Meaning |
| ----- | ------- |
| `generatorSchemaVersion` | Current generator snapshot schema from `GeneratorSchemaVersion.CURRENT`. |
| `worldSeed` / `shape` / `roomCountRequested` | Inputs used to generate the graph. |
| `roomCountActual` | Number of generated rooms after frontier expansion. |
| `seedStreams` | Stable stream identifiers reserved for graph, room, zone, and autotile layers. |
| `bounds` | Min/max room-grid bounds and room-space dimensions. |
| `rooms[]` | Stable room ids, grid coordinates, type ids, room seeds, biome indexes, sorted neighbor dirs, and tile CRC checksums. |
| `progressionGraph` | Macro progression snapshot with world nodes, region hubs, dungeon nodes, and critical path ids. |

The first snapshot schema is graph-centric. Later layered-generator slices should
append section, socket, anchor, validator, and megamap blocks instead of
replacing the command.

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
- Room shell safety is data-driven by `data/room_geometry_rules.json`.
- Procedural room structure is data-driven by `data/room_structure_rules.json`.
- Authored room template selection is data-driven by `data/room_template_catalog.json`.
- Authored 8x8 zone patch selection is data-driven by `data/zone_template_catalog.json`.
- Changing geometry rule values is replay-breaking because it changes deterministic tile output.
- Changing structure rule values is replay-breaking because it changes deterministic zone plans and hazard placement.
- Changing template catalog weights or files is replay-breaking because room seeds may resolve to different TMX layouts.
- Changing zone patch catalog weights or files is replay-breaking because procedural zone expansion may stamp different tile patches.
- Authored TMX templates and catalog entries can be checked with `python tools/validate_room_templates.py --dir java/assets/rooms/templates --strict-geometry --catalog data/room_template_catalog.json`.
- Authored zone patch TMX files and catalog entries can be checked with `python tools/validate_zone_templates.py --dir java/assets/rooms/zone_templates --catalog data/zone_template_catalog.json`.

## Geometry rules

`data/room_geometry_rules.json` controls the first runtime slice of data-driven room geometry:

| Field | Meaning |
| ----- | ------- |
| `roomWidthTiles` / `roomHeightTiles` | Expected room tile dimensions; currently 128×128. |
| `edgeWallThickness` | Solid wall thickness for top/side shell edges when no neighbor exists. |
| `floorThickness` | Solid floor thickness for rooms without a downward neighbor. |
| `doorHalfSpan` | Half-width of centered door openings. Total span is `doorHalfSpan * 2 + 1`. |
| `horizontalDoorDepth` | How far left/right door openings are cleared into the room. |
| `verticalDoorDepth` | How far top/down door openings are cleared into ceiling/floor rows. |

This layer is intentionally below room grammar. It guarantees safe structure, while `ZonePlanner`, `ZoneTemplateLibrary`, and future room grammar passes decide the actual play-space shape.

## Structure rules

`data/room_structure_rules.json` controls the procedural zone plan before `RoomGenerator` mixes concrete 8x8 zone templates into tiles:

| Field | Meaning |
| ----- | ------- |
| `fillMin` / `fillMax` | Range of obstacle or hazard zones placed before DECOR finalization. |
| `lavaChance` / `iceChance` / `waterChance` | Chance that a placed obstacle zone becomes that hazard instead of plain `FILL`. |
| `decorFillChance` | Chance that unresolved `DECOR` becomes solid terrain. |
| `decorPlatformChance` | Chance that unresolved `DECOR` becomes one-way platform terrain. |
| `decorWalkChance` | Chance that unresolved `DECOR` becomes walkable open space; remaining probability becomes `VOID`. |
| `perimeterDepth` | How many outer zone rings are thickened into walls, except door corridors. |
| `centerClearRadiusZones` | Radius around the room center forced back to `WALK` after finalization; useful for boss arenas. |

These rules solve a different layer from TMX templates. Procedural rooms still mix `ZoneTemplateLibrary` patterns per `FILL`/`PLAT` zone; structure rules decide how many of those roles appear and where broad room constraints apply. Authored TMX templates bypass zone planning for their interior layout, then still receive runtime geometry enforcement for doors, walls, and floors.

## Zone patch catalog

`data/zone_template_catalog.json` lets authored 8x8 TMX patches mix into procedural zone expansion:

| Field | Meaning |
| ----- | ------- |
| `roles.<role>.fallbackWeight` | Relative weight reserved for the built-in `ZoneTemplateLibrary` pool. Use `0` only when the role should be fully catalog-authored. |
| `roles.<role>.templates[].file` | TMX filename under `java/assets/rooms/zone_templates/`. |
| `roles.<role>.templates[].weight` | Relative deterministic selection weight for that authored patch; values below 1 clamp to 1 at runtime. |
| `roles.<role>.templates[].biomeIndexes` | Optional integer biome-index allowlist for biome-specific patches. Omit or leave empty to apply to all biomes. |

The runtime loads valid catalog entries through `ZonePatchTemplateLibrary`. During `ZoneTemplateLibrary.pick(...)`, the authored catalog rolls first. If the roll lands in fallback weight, no valid patch exists, or the role has no catalog entry, generation uses the existing hardcoded weighted pool. This lets hand-authored Tiled patches improve room geometry while preserving procedural variety.

Patch TMX files are 8x8, CSV-encoded, use the terrain layer, and use GIDs 0-8. They are small zone components, not full rooms, so they do not receive full-room wall/floor enforcement.

## Template catalog

`data/room_template_catalog.json` lets authored room ids map to weighted TMX variants:

| Field | Meaning |
| ----- | ------- |
| `roomTypes.<id>[].file` | TMX filename under `java/assets/rooms/templates/`. |
| `roomTypes.<id>[].weight` | Relative deterministic selection weight; values below 1 clamp to 1. |

Selection is deterministic from the room seed. Missing explicit files are ignored; if no explicit file exists for the room type, the loader falls back to discovered convention variants named `<id>.tmx`, `<id>_*.tmx`, or `<id>-*.tmx`. This keeps one-file rooms working while allowing authored sets such as `combat_standard_a.tmx`, `combat_standard_b.tmx`, and `combat_standard_c.tmx`.

## Legacy archive

Python/Pygame version is archived at:
`docs/archive/retired/2026-04-21_v0.11.71_python-systems-docs/WORLD_GEN.md`
