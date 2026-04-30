---
doc_type: design_spec
status: approved
owner: core-team
last_updated: 2026-04-30
version_anchor: v0.13.14
---

# Worldgen Lab Prototype Design

## Goal

Build a fast local inspection tool that helps tune world-generation formations
without booting the game. The prototype must expose deterministic single-seed
and batch-seed evidence about generated room geometry, layout shape, rule
failures, and formation quality.

## Scope

The prototype is an offline authoring and QA tool. It does not replace live
server generation, does not add an in-game editor, and does not mutate
generation rules from the UI. It reads the existing deterministic worldgen
snapshot output and adds lab-specific metrics, reports, and batch summaries.

## Recommended Approach

Use a static snapshot/report pipeline:

1. Java exports deterministic worldgen snapshots with additional lab metrics.
2. Python renders one HTML/SVG report bundle from a snapshot.
3. Python batch tooling generates many snapshots, renders failing examples, and
   writes sortable CSV/JSON summaries.

This builds on the existing `WorldGenerationSnapshotCommand` and
`tools/render_worldgen_snapshot.py` instead of adding a runtime dependency or
client debug screen.

## Prototype Slices

### Slice 1: Lab Snapshot Metrics

Add a `labReport` block to the Java snapshot export. It should report:

- room count and room type distribution
- connected-edge shell defects
- door corridor counts
- empty room-grid cells inside bounds
- solid/platform/air/void ratios
- per-room warning flags
- overall quality score suitable for sorting batch output

The lab block is inspection metadata. Because snapshots gain a new block, this
slice must bump `GeneratorSchemaVersion.CURRENT` and
`version.json.generator_schema_version`.

### Slice 2: HTML/SVG Lab Report

Extend the Python renderer into a lab report bundle:

- `index.html`: navigable report with summary, metric tables, and links
- `megamap.svg`: room-grid overview with warning overlays
- `metrics.json`: machine-readable lab metrics
- `overlay.txt`: existing compact text overlay for terminal inspection

The first version should be static HTML with no framework. It should be easy to
open from disk and easy to attach to bug reports.

### Slice 3: Batch Seed Sweeper

Add a batch command that runs many deterministic seeds and emits:

- `summary.csv`
- `summary.json`
- `failures/` report bundles for the worst seeds

The batch output must sort by quality score and expose failure reasons such as
open connected edge, missing shell, excessive void, missing anchors, or
validation warnings.

### Slice 4: Authoring Docs and Prototype Release

Document how to use the lab to tune formations:

- run a single seed
- run a batch sweep
- interpret quality score and warnings
- decide whether to adjust room geometry rules, room structure rules, zone
  patch catalogs, section templates, sockets, or anchors

Release as a prototype patch after local gates pass.

## Data Flow

```text
seed + rooms + shape
  -> Gradle worldgenSnapshot task
  -> snapshot JSON with graph/progression/layout/contracts/validation/megamap/labReport
  -> tools/worldgen_lab.py render
  -> index.html + SVG + JSON + overlay
  -> tools/worldgen_lab.py batch
  -> summary.csv + summary.json + selected failure bundles
```

## Quality Metrics

The prototype quality score should be simple and explainable:

- hard fail when a room shell defect exists
- large penalty for validation report invalidity
- penalty for empty interior grid cells
- penalty for high air/void ratio in rooms with expected floors
- small penalty for repeated room type or template concentration

Exact scoring can evolve; the report must show the component penalties so a
designer can understand why a seed ranks poorly.

## Testing

Use TDD for logic:

- Java tests verify deterministic `labReport` output and connected-edge defect
  detection.
- Python tests verify renderer output files and batch summary sorting.
- Release gates remain the existing version sync, docs freshness, Java tests,
  and JAR build.

## Non-Goals

- No live rule editing UI in this prototype.
- No in-game debug screen.
- No replacement of `WorldGraph`, `ZonePlanner`, or `RoomGenerator`.
- No browser server dependency for the shipped prototype.

## Success Criteria

- One command creates a visual lab report for a seed.
- One command sweeps at least 100 seeds and ranks suspicious formations.
- Reports make geometry/rule problems visible without playing the seed.
- Docs explain how to use the evidence to tune level-generation inputs.
