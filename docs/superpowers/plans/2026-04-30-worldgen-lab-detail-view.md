# Worldgen Lab Detail View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand Worldgen Lab from room-level topology into zone and tile-level formation inspection.

**Architecture:** Extend the Java lab analyzer with compact zone/tile rows, bump generator schema, then update the Python static renderer to output a large world-detail SVG and per-room detail SVGs. The lab remains read-only and file-based.

**Tech Stack:** Java 21, JUnit 5/AssertJ, Python 3.11 standard library, SVG/HTML.

---

## File Map

- Modify `java/shadowascent/src/main/java/com/indieniinja/world/lab/WorldgenLabReport.java`: add detail fields to room metrics.
- Modify `java/shadowascent/src/main/java/com/indieniinja/world/lab/WorldgenLabAnalyzer.java`: export `zoneRows`, `tilePreviewRows`, legends, directions, and biome.
- Modify `java/shadowascent/src/main/java/com/indieniinja/world/GeneratorSchemaVersion.java`: bump from `9` to `10`.
- Modify `java/shadowascent/src/test/java/com/indieniinja/world/lab/WorldgenLabAnalyzerTest.java`: detail export coverage.
- Modify `java/shadowascent/src/test/java/com/indieniinja/world/WorldGenerationSnapshotCommandTest.java`: snapshot detail coverage.
- Modify `tools/worldgen_lab.py`: render expanded world and per-room SVGs.
- Modify `tools/test_worldgen_lab.py`: assert detail artifacts.
- Modify docs/version release metadata after code is green.

## Task 1: Java Detail Snapshot Data

- [x] **Step 1: Add failing Java assertions**

Add assertions that every generated room metric exposes `zoneRows` with 16 rows,
`tilePreviewRows` with 128 rows, `neighborDirs`, `biomeIndex`, and legends.

- [x] **Step 2: Run focused Java test red**

Run:

```powershell
cd java
.\gradlew.bat :shadowascent:test --tests com.indieniinja.world.lab.WorldgenLabAnalyzerTest --no-daemon
```

- [x] **Step 3: Implement analyzer detail fields**

Use `ZonePlanner.plan(room.seed, roomType, dirs)` before tile generation.
Encode zone rows as role-symbol strings and tile preview rows as tile-symbol
strings. Keep full 128x128 rows for inspectability.

- [x] **Step 4: Bump schema and snapshot assertions**

Set `GeneratorSchemaVersion.CURRENT = 10` and update snapshot tests to expect
detail rows under `labReport.rooms[0]`.

- [x] **Step 5: Run focused Java tests green**

Run:

```powershell
cd java
.\gradlew.bat :shadowascent:test --tests com.indieniinja.world.lab.WorldgenLabAnalyzerTest --tests com.indieniinja.world.WorldGenerationSnapshotCommandTest --no-daemon
```

## Task 2: Python Detail Renderer

- [x] **Step 1: Add failing Python render assertions**

Update `tools/test_worldgen_lab.py` fixture snapshots with one room containing
`zoneRows` and `tilePreviewRows`. Assert `world-detail.svg` and
`rooms/<roomKey>.svg` are written.

- [x] **Step 2: Run Python test red**

Run:

```powershell
python tools/test_worldgen_lab.py
```

- [x] **Step 3: Implement detail SVG rendering**

Add functions in `tools/worldgen_lab.py` to render:

- large expanded world detail from `labReport.rooms[]`
- per-room SVGs under `rooms/`
- links in `index.html`

- [x] **Step 4: Run Python tests green**

Run:

```powershell
python tools/test_worldgen_lab.py
```

## Task 3: Docs, Gates, Release

- [x] **Step 1: Update authoring/system docs**

Document `world-detail.svg`, `rooms/*.svg`, zone symbols, tile symbols, and how
to diagnose rule/template problems.

- [x] **Step 2: Update release metadata**

Set version to `0.13.16`, generator schema to `10`, and add changelog/current
state entries for the detail view.

- [x] **Step 3: Run gates**

Run:

```powershell
python tools/test_worldgen_lab.py
python tools/check_version_sync.py --tag v0.13.16
python tools/check_docs_freshness.py --emit-report
cd java
.\gradlew.bat :shadowascent:test --tests com.indieniinja.world.lab.WorldgenLabAnalyzerTest --tests com.indieniinja.world.WorldGenerationSnapshotCommandTest --no-daemon
.\gradlew.bat :server:test :client:test :server:shadowJar :client:shadowJar --no-daemon
cd ..
git diff --check
```

- [x] **Step 4: Commit, tag, push, verify**

Commit as `feat(worldgen): add lab detail view`, tag `v0.13.16`, push master
and tag, then verify CI, Release, and release assets.

## Self-Review

- Spec coverage: all approved detail-view requirements map to Java export,
  Python renderer, docs, and release tasks.
- Placeholder scan: no deferred TBD/TODO tasks.
- Type consistency: `zoneRows`, `tilePreviewRows`, `world-detail.svg`, and
  `rooms/*.svg` are named consistently across tasks.
