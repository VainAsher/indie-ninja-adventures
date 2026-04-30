---
doc_type: design_spec
status: living
owner: core-team
last_updated: 2026-04-30
version_anchor: v0.13.15
---

# Worldgen Lab Detail View Design

## Goal

Worldgen Lab must show generation detail below the room graph: each room needs
its 16x16 zone role plan and an inspectable tile-level preview so formation
problems can be traced to rules, templates, or zone patches.

## Current Gap

The v0.13.15 lab report shows a room-scale minimap and aggregate room metrics.
That is useful for topology, but it cannot answer why a room looks wrong,
which zone roles were selected, where doors/chutes/platforms were placed, or
which tile layer produced the visible geometry.

## Target Design

Add a read-only detail layer to deterministic worldgen snapshots:

- `labReport.rooms[].neighborDirs`
- `labReport.rooms[].biomeIndex`
- `labReport.rooms[].zoneRows`
- `labReport.rooms[].tilePreviewRows`
- `labReport.rooms[].tileLegend`
- `labReport.rooms[].zoneLegend`

`zoneRows` is a compact 16-row encoding of `ZonePlanner` roles. `tilePreviewRows`
is a compact visual encoding of the generated 128x128 tile grid. It keeps full
room geometry visible without embedding huge raw JSON objects.

Update `tools/worldgen_lab.py render` to produce:

- `world-detail.svg`: a larger world SVG where every room contains a miniature
  zone/tile preview instead of a single colored square.
- `rooms/<roomKey>.svg`: one larger room detail image per room, showing zone
  grid and tile preview side by side.
- `index.html`: a static lab report with the macro map, expanded world detail,
  warning summary, and a room table linking to each detail SVG.
- `metrics.json`: unchanged path, now including the richer `labReport`.

## Boundaries

This slice does not add a live editor, runtime hot reload, click handlers that
require a web server, or a rule mutation UI. The output remains static and
works from `file://`.

## Acceptance Criteria

- Snapshots remain deterministic for identical inputs.
- `labReport.rooms[]` includes zone rows and tile preview rows for every room.
- The lab renderer writes `world-detail.svg` and `rooms/*.svg`.
- The HTML report provides useful room-level links and a larger visual
  formation view.
- Existing render and batch commands keep working.
- Release metadata advances in the next tag because snapshot schema changes.
