---
doc_type: system_doc
status: living
owner: core-team
last_updated: 2026-05-01
version_anchor: v0.13.17
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
- Section templates:
  - `java/shadowascent/src/main/java/com/indieniinja/world/sections/SectionTemplate.java`
  - `java/shadowascent/src/main/java/com/indieniinja/world/sections/SectionTemplateLibrary.java`
- Hybrid layout:
  - `java/shadowascent/src/main/java/com/indieniinja/world/layout/HybridLayoutPlan.java`
  - `java/shadowascent/src/main/java/com/indieniinja/world/layout/HybridLayoutPlanner.java`
- Socket and anchor contracts:
  - `java/shadowascent/src/main/java/com/indieniinja/world/contracts/SocketAnchorPlan.java`
  - `java/shadowascent/src/main/java/com/indieniinja/world/contracts/SocketAnchorPlanner.java`
- Validation and repair reporting:
  - `java/shadowascent/src/main/java/com/indieniinja/world/validation/GenerationValidationReport.java`
  - `java/shadowascent/src/main/java/com/indieniinja/world/validation/GenerationValidationPlanner.java`
- Megamap export:
  - `java/shadowascent/src/main/java/com/indieniinja/world/megamap/MegamapSnapshot.java`
  - `java/shadowascent/src/main/java/com/indieniinja/world/megamap/MegamapStitcher.java`
- Lab analysis:
  - `java/shadowascent/src/main/java/com/indieniinja/world/lab/WorldgenLabReport.java`
  - `java/shadowascent/src/main/java/com/indieniinja/world/lab/WorldgenLabAnalyzer.java`
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
2. Load authored section templates — describes pacing chunks, footprints, edge rules, required sockets, mutable zones, and anchor candidates.
3. Generate hybrid layout plan — assigns section footprints to deterministic grid coordinates and emits progression-edge connections.
4. Resolve socket and anchor plan — converts section sockets into connection contracts and section anchors into world-space bounds.
5. Validate layered metadata — checks progression, layout connection contracts, critical anchors, and repair recommendations.
6. Generate legacy `WorldGraph` from seed and shape — assigns `RoomType` to each `RoomNode`.
7. Build per-room zone grid (`ZonePlanner`) then tile grid (`RoomGenerator`/`WorldGenerator`).
   - Template types load a seed-selected `.tmx` variant first; door openings carved by `carveDoors()`.
   - Non-template types go through `ZonePlanner` → `RoomGenerator` procedural path.
   - `RoomStructureRules` drives room-level zone grammar before zones expand into 8x8 tile templates.
   - `RoomGeometryRules` and `RoomGeometryEnforcer` apply shared wall, floor, and door-corridor rules to both procedural rooms and loaded TMX templates.
8. Emit megamap snapshot metadata — continuous room origins, seams, overlays, metrics, and autotile preview checksums.
9. Emit lab report metadata — per-room tile counts, warning counts, quality
   score, and connected-edge shell diagnostics for authoring iteration.
10. Apply postprocess/puzzle layers for gates, puzzles, and entity planning.
11. Stitch unified layout for simulation and snapshot descriptors.
12. Client renders tile output with blob autotile mapping and room metadata.

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

## Section template layer

Section templates live in `data/worldgen/sections/*.json` and are loaded by
`SectionTemplateLibrary`. They are authored pacing chunks between macro
progression and concrete rooms.

### Section schema contract (strict mode aware)

| Field | Required for most kinds | Required for `hub_home` / `boss_approach` | Notes |
| ----- | ----------------------- | ------------------------------------------ | ----- |
| `id` | yes | yes | Stable template id for deterministic selection and snapshots. |
| `biome` | yes | yes | Biome/theme target for template filtering. |
| `kind` | yes | yes | Pacing purpose, e.g. `key_trial`, `shop_save_loop`, `boss_approach`. |
| `footprint.gridW/gridH` | yes | no | Positive grid dimensions in room-grid units. |
| `nodeKinds[]` | yes (non-empty) | no | Local beat list; required for navigable authored sections. |
| `edgeRules[]` | yes (non-empty) | no | Directed links (`from`/`to`) between `nodeKinds`. |
| `requiredSockets[]` | yes (non-empty) | no | Socket tokens (underscore grammar) consumed by contract planning. |
| `anchors[]` | yes (non-empty) | yes (non-empty) | Placement candidates (at least `id` + `kind` per anchor). |
| `mutableZones[]` | no | no | Optional procedural dressing bounds. |

`SectionTemplateLibrary` always emits deterministic validation issues
(`validationIssues`) sorted by file/field/kind for stable CI logs. In default
mode, malformed templates still load leniently where possible to preserve
legacy generation flow while exposing actionable issues.

Enable strict contract enforcement with:

```bash
cd java
./gradlew.bat :shadowascent:test -Dninja.sectionTemplateStrict=true --tests com.indieniinja.world.sections.SectionTemplateLibraryTest --no-daemon
```

In strict mode, any schema error fails load with issue kind, field path, and
repair action so malformed authored content is CI-failing instead of silently
defaulted.

### Migration policy for legacy partial templates

- Default mode remains backward-compatible for draft/legacy section files.
- Strict mode should be enabled in CI and release gates once authoring data is
  migrated for the target campaign.
- When migrating old templates, fix validation issues in deterministic order
  (top of the strict-mode error list first) to avoid chasing non-stable logs.

## Hybrid layout layer

`HybridLayoutPlanner.plan(worldSeed, progressionGraph, sectionTemplates)` turns
progression nodes into section assignments. The current implementation is a
conservative deterministic grid planner: critical-path sections are placed in
readable order, optional sections move into a lower row, and assigned
progression child links become layout connections.

Current model responsibilities:

| Model | Purpose |
| ----- | ------- |
| `HybridLayoutPlan` | Snapshot container for bounds, section assignments, and connections. |
| `HybridLayoutPlanner` | Selects section templates for progression nodes and assigns non-overlapping grid footprints. |

This layer still does not replace live server `WorldGraph` placement or room
tile generation. It gives tooling and later slices an inspectable spatial plan
before validation, repair, and megamap stitching consume it.

## Socket and anchor contract layer

`SocketAnchorPlanner.plan(worldSeed, hybridLayout, sectionTemplates)` resolves
authored section contracts into deterministic metadata:

| Field | Purpose |
| ----- | ------- |
| `connectionContracts[]` | One contract per assigned layout connection, with source/destination socket shape and match status. |
| `resolvedAnchors[]` | Gameplay anchor candidates converted from local section bounds to world-space bounds. |
| `status` | `matched` when traversal tags and height bands are compatible, otherwise `needs_transition`. |

Socket ids currently use the convention `side_band_traversal`, for example
`west_low_walk` or `east_mid_jump`. The planner parses those ids into side,
height band, traversal tags, width, and clearance metadata. This is still a pure
snapshot layer; it does not carve corridors or instantiate entities yet.
Socket ids use grammar `side_band_traversal[_modifier...]`:

- `west_low_walk`
- `east_mid_jump`
- `north_high_climb_bridge`

Set strict grammar mode with `-Dninja.socketContractStrict=true` to reject
unknown `side` or `band` tokens. In strict mode, unknown side/band tokens are
downgraded to `unknown` socket contracts, which force `needs_transition`.

Compatibility matrix for core traversal tags:

| Traversal tag | Default width | Typical use |
| ------------- | ------------- | ----------- |
| `walk` | 4 | Flat corridor or ledge join |
| `jump` | 3 | Gap crossing or vertical offset join |
| `climb` | 4 | Vertical traversal with climbable support |

Sockets are directly compatible only when traversal tags overlap and the band
distance is within one step (`low <-> mid <-> high`).

## Validation and repair report layer

`GenerationValidationPlanner.validate(progressionGraph, hybridLayout,
socketAnchorPlan)` emits a deterministic `GenerationValidationReport`.

Current checks:

| Check | Failure kind | Repair tier |
| ----- | ------------ | ----------- |
| Required progression nodes are reachable | `blocked_progression_node` | `regenerate` |
| Every layout edge has a socket contract | `missing_connection_contract` | `replace` |
| Critical anchors live on reachable nodes | `unreachable_critical_anchor` | `regenerate` |
| Mandatory edge needs transition without explicit strategy | `critical_path_transition_debt` | `replace` |
| Optional edge needs transition | `optional_transition_debt` (`warning`) | `patch` |
| Any socket mismatch requiring a bridge room | repair action `insert_transition_room` | `patch` |

This layer records what should be patched, replaced, or regenerated, but it does
not mutate geometry yet. Later repair/stitching work can consume these actions.

## Megamap snapshot layer

`MegamapStitcher.stitch(worldSeed, requestedRooms, shape, worldGraph)` emits a
compact continuous-map descriptor for tooling and golden-seed diffs.

Current export fields:

| Field | Purpose |
| ----- | ------- |
| `bounds` | Normalized room-grid and tile-space extent for the stitched map. |
| `rooms[]` | Stable room ids, grid coordinates, continuous tile origins, room size, type, biome, and tile checksum. |
| `seams[]` | Unique connected-room seam rectangles with source, destination, direction, bounds, and passability marker. |
| `overlayRows[]` | Text minimap rows for fast visual review. |
| `metrics` | Room/seam counts, stamped vs empty tile counts, passable/solid/platform/hazard counts, and stitched checksum. |
| `autotileSummary` | Deterministic edge-mask preview checksum for solid-like tiles. |

The companion tool renders this block without booting the client:

```bash
python tools/render_worldgen_snapshot.py java/shadowascent/build/worldgen-snapshots/seed-12345-v8.json --out build/worldgen-viewer/seed-12345-v8
```

It writes `overlay.txt`, `metrics.json`, and `megamap.svg`.

## Worldgen Lab

`WorldgenLabAnalyzer.analyze(worldSeed, graph)` emits the snapshot `labReport`
block. It is intentionally read-only: it generates the same per-room grids as
the snapshot exporter, counts solid/platform/passable tiles, aggregates room
type usage, exports 16x16 zone role rows and 128x128 tile preview rows, and
flags connected room borders that are open outside the legal door span.

Current warning categories:

| Warning | Meaning |
| ------- | ------- |
| `connected_up_edge_open_outside_door` | A room with an upward connection has top-shell air outside the door corridor. |
| `connected_down_edge_open_outside_door` | A room with a downward connection has bottom-floor air outside the door corridor. |
| `connected_left_edge_open_outside_door` | A room with a left connection has side-shell air outside the door corridor. |
| `connected_right_edge_open_outside_door` | A room with a right connection has side-shell air outside the door corridor. |

Render a single snapshot:

```bash
python tools/worldgen_lab.py render java/shadowascent/build/worldgen-snapshots/seed-12345.json --out build/worldgen-lab/seed-12345
```

Render the Act 1 vertical-slice baseline seed:

```bash
python tools/worldgen_lab.py act1 --out build/worldgen-lab/act1-seed-420
```

`act1` defaults to seed `420`, 20 rooms, and `BLOB` shape. Use this when
tuning formation rules for the Act 1 baseline so before/after changes are
measured against the same deterministic world.

The render bundle includes:

| File | Purpose |
| ---- | ------- |
| `index.html` | Static report with macro map, expanded world detail, warning summary, and room links. |
| `megamap.svg` | Compact room-graph overview. |
| `world-detail.svg` | Expanded world view where each room shows a miniature tile preview. |
| `pipeline.svg` | Static stage strip for progression, layout, sockets/anchors, validation, megamap, and lab analysis. |
| `pipeline.json` | Machine-readable pipeline stage summary for quick comparisons and issue capture. |
| `rooms/<room>.svg` | Per-room detail view with 16x16 zone plan and 128x128 tile preview. |
| `metrics.json` | Machine-readable snapshot, lab report, legends, and metrics. |
| `overlay.txt` | Plain text macro minimap. |

Batch existing snapshots and render the lowest-quality seeds:

```bash
python tools/worldgen_lab.py batch --snapshots java/shadowascent/build/worldgen-snapshots --out build/worldgen-lab/batch --failures 5
```

Or generate and summarize a quick seed sweep:

```bash
python tools/worldgen_lab.py batch --seeds 25 --rooms 20 --shape BLOB --out build/worldgen-lab/sweep --failures 5
```

Compare a baseline snapshot or rendered bundle against a candidate:

```bash
python tools/worldgen_lab.py compare --base build/worldgen-lab/act1-seed-420 --candidate build/worldgen-lab/act1-seed-420-after-rule-change --out build/worldgen-lab/act1-compare
```

The compare bundle writes `compare.html`, `compare.json`, and `compare.csv`.
Use it after changing geometry rules, structure rules, room templates, zone
patches, or validation policy. Important fields are `qualityDelta`,
`warningDeltas`, and `roomChecksumChanges`.

Use `summary.csv` to sort by `qualityScore` and warning totals. If warnings
cluster on one room type, tune that room's TMX template or structure rules. If
warnings cluster on one edge direction across many room types, tune
`data/room_geometry_rules.json` or the shared shell enforcement.

Zone symbols in `zoneRows`:

| Symbol | Role |
| ------ | ---- |
| `.` | walk |
| `#` | fill |
| `=` | platform |
| `D` | door |
| `V` | save |
| `$` | shop |
| `T` | loot |
| `v` | chute |
| `C` | climb |
| `+` | connector |
| `^` | lava |
| `i` | ice |
| `~` | water |

Tile symbols in `tilePreviewRows`:

| Symbol | Tile |
| ------ | ---- |
| `.` | air |
| `#` | solid |
| `=` | platform |
| `i` | ice |
| `~` | water |
| `^` | lava |
| `L` | locked door |
| `g` | gas |
| `c` | climbable |

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
| `sectionTemplates` | Loaded authored section templates with count and stable template metadata. |
| `hybridLayout` | Deterministic section-footprint bounds, assignments, and assigned progression-edge connections. |
| `socketAnchorPlan` | Deterministic connection contracts plus resolved anchor world bounds. |
| `validationReport` | Deterministic validation outcome, issues, and bounded repair actions. |
| `megamap` | Continuous-map room origins, seams, overlays, metrics, and autotile preview checksums. |
| `labReport` | Per-room lab metrics, quality score, type counts, and warning counts for tuning formations. |

Future live-placement work should consume or extend the megamap block instead
of replacing the command.

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
- Authored section pacing chunks are data-driven by `data/worldgen/sections/*.json`.
- Changing geometry rule values is replay-breaking because it changes deterministic tile output.
- Changing structure rule values is replay-breaking because it changes deterministic zone plans and hazard placement.
- Changing template catalog weights or files is replay-breaking because room seeds may resolve to different TMX layouts.
- Changing zone patch catalog weights or files is replay-breaking because procedural zone expansion may stamp different tile patches.
- Changing section templates, hybrid layout policy, socket/anchor resolution,
  validation/repair policy, or megamap export semantics is snapshot-schema-visible
  now and will become replay-breaking once live room placement consumes section
  assignments.
- Authored TMX templates and catalog entries can be checked with `python tools/validate_room_templates.py --dir java/assets/rooms/templates --strict-geometry --catalog data/room_template_catalog.json`.
- Authored zone patch TMX files and catalog entries can be checked with `python tools/validate_zone_templates.py --dir java/assets/rooms/zone_templates --catalog data/zone_template_catalog.json`.
- Enemy placement is suppressed in rooms at section connection boundaries. Callers pass a `Set<String>` of seam room keys (from `PuzzlePlan.roomKey(gridX, gridY)`) to `RoomPostProcessor.process()` as the `seamRoomKeys` parameter. When a room's key is in the set, `EntityPlanner.placeEnemies()` returns `List.of()` immediately. This enforces the LayerProcGen effect-distance principle: no immediate combat engagement at section transitions. Omit the parameter (backward-compat overload) or pass `Collections.emptySet()` to disable seam clearance.

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
