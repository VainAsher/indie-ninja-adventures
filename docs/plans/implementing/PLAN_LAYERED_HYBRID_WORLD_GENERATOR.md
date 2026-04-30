---
doc_type: implementation_plan
status: implementing
owner: core-team
last_updated: 2026-04-30
version_anchor: v0.13.9
---

# Layered Hybrid World Generator

## Goal

Move Shadow Ascent from a mostly room-centric generator toward a layered hybrid
pipeline that can combine progression graphs, authored content, procedural room
grammar, validation, repair, and inspectable deterministic snapshots.

## Target Architecture

Generation should be layered in this order:

1. Seed policy and generator schema version.
2. World, region, and dungeon progression graphs.
3. Section selection and hybrid spatial layout.
4. Room template instantiation or legacy procedural synthesis.
5. Zone patch expansion.
6. Socket and anchor resolution.
7. Progression and reachability validation.
8. Repair, replacement, or regeneration.
9. Megamap stitching, autotiling, and runtime export.

The existing `WorldGraph -> ZonePlanner -> RoomGenerator -> ZoneTemplateLibrary`
path remains the legacy synthesis backend while higher layers are added around
it incrementally.

## Slice 1: Tiled Zone Patch Templates

**Goal:** Let designers author 8x8 zone patch templates in Tiled and mix them
into procedural room generation without replacing the existing hardcoded zone
template pool.

**Architecture:**

- Add `data/zone_template_catalog.json`.
- Add `java/assets/rooms/zone_templates/` as the canonical runtime patch path.
- Add a Java catalog/loader below `ZoneTemplateLibrary`.
- Give each role a `fallbackWeight` so authored patches can blend with the
  current procedural pool.
- Add validation tooling for patch size, tile ids, catalog shape, and path
  safety.

### Tasks

- [x] Inspect existing `ZoneTemplateLibrary`, `RoomGenerator`, and template
  catalog patterns.
- [x] Add unit tests for deterministic catalog selection and TMX parsing.
- [x] Implement `ZonePatchTemplateLibrary`.
- [x] Route `ZoneTemplateLibrary.pick(...)` through authored patches first,
  then hardcoded fallback.
- [x] Add sample `FILL` and `PLAT` patch TMX files.
- [x] Add `tools/validate_zone_templates.py`.
- [x] Update level-authoring and world-generation docs.
- [x] Run focused Java and Python verification.

### Verification

- [x] `python tools/validate_zone_templates.py --dir java/assets/rooms/zone_templates --catalog data/zone_template_catalog.json`
- [x] `python tools/validate_zone_templates.py --dir assets/rooms/zone_templates --catalog data/zone_template_catalog.json`
- [x] `cd java; .\gradlew.bat :shadowascent:test --tests com.indieniinja.world.ZonePatchTemplateLibraryTest --no-daemon`
- [x] `cd java; .\gradlew.bat :server:test --tests com.indieniinja.server.ZoneTemplateLibraryTest --no-daemon`
- [x] `python tools/check_docs_freshness.py --emit-report`
- [x] `git diff --check`

## Future Slices

There are 8 planned slices total:

1. **Tiled zone patch templates:** complete in this plan.
2. **Generator schema and snapshots:** add `GeneratorSchemaVersion`, explicit
   seed stream metadata, and a deterministic JSON snapshot CLI.
3. **Progression graph layer:** add world, region, and dungeon progression
   models with solvability tests.
4. **Section templates:** complete in this plan.
   Add authored section schemas for key trials, locks,
   shortcuts, boss approaches, shops, saves, and region entrances.
5. **Hybrid BSP/grid layout:** complete in this plan.
   Place section footprints with deterministic macro grid space and local
   connectivity metadata.
6. **Sockets and anchors:** make room/section joins and gameplay placements
   explicit contracts.
7. **Validation and repair:** add progression, reachability, and bounded repair
   passes.
8. **Megamap stitcher and viewer:** export continuous maps, overlays, metrics,
   and diffable golden seeds.

## Slice 2: Generator Schema and Snapshots

**Goal:** Create a stable inspection/export surface before deeper graph and
layout refactors.

**Architecture:**

- Add `GeneratorSchemaVersion` as the runtime source for generator snapshot
  schema identity.
- Add `generator_schema_version` to `version.json` for release metadata.
- Add a deterministic Java command that exports world graph, room metadata,
  seed-stream identifiers, bounds, and room tile checksums to JSON.
- Keep the export graph-centric for now; later slices can append section,
  anchor, validator, and megamap blocks without changing the command shape.

### Tasks

- [x] Add unit tests for deterministic snapshot export.
- [x] Implement `GeneratorSchemaVersion`.
- [x] Implement `WorldGenerationSnapshotCommand`.
- [x] Document CLI usage and schema fields.
- [x] Run focused verification.

### Verification

- [x] `cd java; .\gradlew.bat :shadowascent:test --tests com.indieniinja.world.WorldGenerationSnapshotCommandTest --tests com.indieniinja.world.ZonePatchTemplateLibraryTest --no-daemon`
- [x] `cd java; .\gradlew.bat :shadowascent:worldgenSnapshot -Pseed=12345 -Prooms=12 -Pshape=BLOB "-Pout=build/worldgen-snapshots/seed-12345.json" --no-daemon`
- [x] `python tools/validate_zone_templates.py --dir java/assets/rooms/zone_templates --catalog data/zone_template_catalog.json`
- [x] `python tools/check_version_sync.py --tag v0.13.6`
- [x] `python tools/check_docs_freshness.py --emit-report`
- [x] `git diff --check`

## Slice 3: Progression Graph Layer

**Goal:** Add deterministic macro progression models before section/layout
placement so the generator can reason about central hubs, region hubs, dungeon
beats, requirements, grants, and critical path solvability before it places
rooms.

**Architecture:**

- Add `com.indieniinja.world.progression`.
- Keep this layer pure and independent from server persistence and legacy
  `WorldGraph` runtime generation.
- Generate a central hub, region hubs, dungeon nodes, optional branches, and a
  critical path from the world seed.
- Validate solvability by walking reachable nodes while accumulating grants.
- Append the progression graph to deterministic worldgen snapshot exports and
  bump `GeneratorSchemaVersion.CURRENT`.

### Tasks

- [x] Add TDD coverage for deterministic graph generation and seed-sweep
  solvability.
- [x] Implement `WorldProgressionGraph`.
- [x] Implement `WorldProgressionGenerator`.
- [x] Implement `ProgressionValidator` and `ProgressionValidationResult`.
- [x] Append `progressionGraph` to `WorldGenerationSnapshotCommand`.
- [x] Update system, architecture, authoring, changelog, and current-state docs.
- [x] Run focused verification.

### Verification

- [x] `cd java; .\gradlew.bat :shadowascent:test --tests com.indieniinja.world.WorldGenerationSnapshotCommandTest --tests com.indieniinja.world.progression.WorldProgressionGeneratorTest --no-daemon`
- [x] `cd java; .\gradlew.bat :shadowascent:test --tests com.indieniinja.world.progression.WorldProgressionGeneratorTest --no-daemon`
- [x] `cd java; .\gradlew.bat :shadowascent:worldgenSnapshot -Pseed=12345 -Prooms=12 -Pshape=BLOB "-Pout=build/worldgen-snapshots/seed-12345-v3.json" --no-daemon`
- [x] `python tools/check_version_sync.py --tag v0.13.7`
- [x] `python tools/check_docs_freshness.py --emit-report`
- [x] `git diff --check`
- [x] `cd java; .\gradlew.bat :server:test :client:test :server:shadowJar :client:shadowJar --no-daemon`

## Slice 4: Section Templates

**Goal:** Add an authored section-template contract between macro progression
graphs and concrete room layout so future layout slices can pick reusable
pacing chunks before placing rooms.

**Architecture:**

- Add `com.indieniinja.world.sections`.
- Load deterministic JSON section templates from `data/worldgen/sections/*.json`.
- Model footprints, local node kinds, edge rules, required sockets, mutable
  zones, and anchor candidates.
- Append `sectionTemplates` to deterministic worldgen snapshot exports and bump
  `GeneratorSchemaVersion.CURRENT`.
- Keep this as a pure data/export layer; hybrid placement consumes it in Slice 5.

### Tasks

- [x] Add TDD coverage for loading complete section template data.
- [x] Add TDD coverage for deterministic biome/kind selection.
- [x] Add TDD coverage for stable snapshot ordering.
- [x] Implement `SectionTemplate`.
- [x] Implement `SectionTemplateLibrary`.
- [x] Add starter authored section JSON files.
- [x] Append `sectionTemplates` to `WorldGenerationSnapshotCommand`.
- [x] Update system, architecture, authoring, changelog, and current-state docs.
- [x] Run focused verification.
- [x] Run release gates.

### Verification

- [x] `cd java; .\gradlew.bat :shadowascent:test --tests com.indieniinja.world.sections.SectionTemplateLibraryTest --tests com.indieniinja.world.WorldGenerationSnapshotCommandTest --no-daemon`
- [x] `cd java; .\gradlew.bat :shadowascent:worldgenSnapshot -Pseed=12345 -Prooms=12 -Pshape=BLOB "-Pout=build/worldgen-snapshots/seed-12345-v4.json" --no-daemon`
- [x] `python tools/check_version_sync.py --tag v0.13.8`
- [x] `python tools/check_docs_freshness.py --emit-report`
- [x] `git diff --check`
- [x] `cd java; .\gradlew.bat :server:test :client:test :server:shadowJar :client:shadowJar --no-daemon`

## Slice 5: Hybrid BSP/Grid Layout

**Goal:** Turn macro progression nodes and authored section templates into an
inspectable deterministic layout plan before concrete room instantiation.

**Architecture:**

- Add `com.indieniinja.world.layout`.
- Place selected section footprints into deterministic room-grid coordinates.
- Preserve progression-edge connectivity between assigned sections.
- Keep the layer pure: no server persistence, no live `WorldGraph` replacement,
  and no tile generation changes yet.
- Append `hybridLayout` to deterministic worldgen snapshot exports and bump
  `GeneratorSchemaVersion.CURRENT`.

### Tasks

- [x] Add TDD coverage for deterministic layout output.
- [x] Add TDD coverage for non-overlapping section footprints.
- [x] Add TDD coverage for assigned progression child connections.
- [x] Implement `HybridLayoutPlan`.
- [x] Implement `HybridLayoutPlanner`.
- [x] Append `hybridLayout` to `WorldGenerationSnapshotCommand`.
- [x] Update system, architecture, authoring, changelog, and current-state docs.
- [x] Run focused verification.
- [x] Run release gates.

### Verification

- [x] `cd java; .\gradlew.bat :shadowascent:test --tests com.indieniinja.world.layout.HybridLayoutPlannerTest --tests com.indieniinja.world.WorldGenerationSnapshotCommandTest --no-daemon`
- [x] `cd java; .\gradlew.bat :shadowascent:worldgenSnapshot -Pseed=12345 -Prooms=12 -Pshape=BLOB "-Pout=build/worldgen-snapshots/seed-12345-v5.json" --no-daemon`
- [x] `python tools/check_version_sync.py --tag v0.13.9`
- [x] `python tools/check_docs_freshness.py --emit-report`
- [x] `git diff --check`
- [x] `cd java; .\gradlew.bat :server:test :client:test :server:shadowJar :client:shadowJar --no-daemon`

## Release Plan

- **Next tag:** `v0.13.9`.
- **Release scope:** Slice 5 only, because it adds the pure hybrid layout
  planning layer and updates snapshot schema version 5.
- **Pre-tag gates:** follow `docs/workflow/RELEASE_CHECKLIST.md`.
- **Post-push gates:** verify CI and Release workflows, then confirm release
  assets include client/server JARs and docs archive.

## Compatibility

Changing zone patch catalog weights or TMX patch contents is replay-breaking for
procedural rooms because the final tile grid can change for the same world seed.
The fallback pool remains available so missing or invalid authored patches do
not hard-fail generation.
