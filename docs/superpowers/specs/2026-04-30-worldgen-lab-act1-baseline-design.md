---
doc_type: design_spec
status: approved
owner: core-team
last_updated: 2026-04-30
version_anchor: v0.13.17
---

# Worldgen Lab Act 1 Baseline Design

## Goal

Make seed `420` the first-class Act 1 vertical-slice worldgen baseline and make
the lab useful for fast before/after tuning of formations.

## Target Workflow

The authoring loop should be:

1. Generate and render the baseline with one command.
2. Inspect pipeline stage health, world detail, and room detail.
3. Change a room rule, zone patch, template, socket, or validation rule.
4. Re-run the same seed.
5. Compare the previous and candidate snapshots.

## Scope

This slice stays static and file-based. It does not add a live web server,
in-browser rule editing, hot reload, or mutation UI.

## Required Outputs

- `tools/worldgen_lab.py act1` renders seed `420` to a stable baseline folder.
- `pipeline.json` summarizes progression, layout, socket/anchor, validation,
  megamap, and lab-analysis stages.
- `pipeline.svg` gives a visual stage strip in the static report.
- `tools/worldgen_lab.py compare` writes `compare.html`, `compare.json`, and
  `compare.csv` for before/after seed tuning.
- Docs describe seed `420` as the Act 1 worldgen baseline.

## Acceptance Criteria

- Existing `render` and `batch` commands keep working.
- A fixture snapshot for seed `420` can be rendered through `act1 --snapshot`.
- `render` always writes pipeline artifacts.
- `compare` reports quality delta, warning deltas, and room checksum changes.
- No generator snapshot schema bump is needed because this is tool/report
  output over existing schema `10`.
