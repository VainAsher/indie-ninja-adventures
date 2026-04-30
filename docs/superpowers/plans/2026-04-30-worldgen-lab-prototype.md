# Worldgen Lab Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and release a static Worldgen Lab prototype for single-seed visual inspection and batch seed formation analysis.

**Architecture:** Extend the existing Java `WorldGenerationSnapshotCommand` with deterministic `labReport` metadata, then add Python tooling that renders a static HTML/SVG report and sweeps many seeds into CSV/JSON summaries. The prototype remains offline and does not alter live runtime generation.

**Tech Stack:** Java 21, Gradle, JUnit 5/AssertJ, Python 3.11 standard library, existing worldgen snapshot and renderer tools.

---

## File Map

- Modify `java/shadowascent/src/main/java/com/indieniinja/world/GeneratorSchemaVersion.java`: bump snapshot schema from `8` to `9`.
- Create `java/shadowascent/src/main/java/com/indieniinja/world/lab/WorldgenLabReport.java`: immutable lab metric model with JSON export maps.
- Create `java/shadowascent/src/main/java/com/indieniinja/world/lab/WorldgenLabAnalyzer.java`: deterministic analyzer over `WorldGraph`, room grids, bounds, and validation report.
- Modify `java/shadowascent/src/main/java/com/indieniinja/world/WorldGenerationSnapshotCommand.java`: add `labReport`.
- Create `java/shadowascent/src/test/java/com/indieniinja/world/lab/WorldgenLabAnalyzerTest.java`: analyzer tests.
- Modify `java/shadowascent/src/test/java/com/indieniinja/world/WorldGenerationSnapshotCommandTest.java`: schema/snapshot coverage for `labReport`.
- Create `tools/worldgen_lab.py`: CLI with `render` and `batch` commands.
- Create `tools/test_worldgen_lab.py`: Python tests for render and batch output.
- Modify `tools/render_worldgen_snapshot.py`: either reuse helper functions from `worldgen_lab.py` or keep as legacy-compatible wrapper.
- Modify docs: `docs/guides/LEVEL_AUTHORING_GUIDE.md`, `docs/systems/WORLD_GEN.md`, `docs/plans/implementing/PLAN_LAYERED_HYBRID_WORLD_GENERATOR.md`, `docs/CHANGELOG.md`, `docs/CURRENT_STATE.md`, `docs/ROADMAP.md`, `README.md`, `version.json`, `java/build.gradle.kts`.

---

## Task 1: Java Lab Metrics

**Files:**
- Create: `java/shadowascent/src/main/java/com/indieniinja/world/lab/WorldgenLabReport.java`
- Create: `java/shadowascent/src/main/java/com/indieniinja/world/lab/WorldgenLabAnalyzer.java`
- Test: `java/shadowascent/src/test/java/com/indieniinja/world/lab/WorldgenLabAnalyzerTest.java`
- Modify: `java/shadowascent/src/main/java/com/indieniinja/world/WorldGenerationSnapshotCommand.java`
- Modify: `java/shadowascent/src/main/java/com/indieniinja/world/GeneratorSchemaVersion.java`
- Modify: `version.json`

- [ ] **Step 1: Write failing analyzer tests**

Create tests that:

```java
@Test
void reportIsDeterministicForSameInputs() {
    WorldGraph graph = WorldGraph.generate(12345L, 12, WorldGraph.WorldShape.BLOB);
    WorldgenLabReport first = WorldgenLabAnalyzer.analyze(12345L, graph);
    WorldgenLabReport second = WorldgenLabAnalyzer.analyze(12345L, graph);
    assertThat(first.toMap()).isEqualTo(second.toMap());
}

@Test
void reportFlagsConnectedEdgeShellDefects() {
    byte[][] grid = new byte[128][128];
    WorldgenLabReport.RoomLabMetrics metrics =
        WorldgenLabAnalyzer.analyzeRoomGrid("fixture", "combat", Set.of("down"), grid);
    assertThat(metrics.warnings()).contains("connected_down_edge_open_outside_door");
}

@Test
void generatedRoomsHaveNoConnectedEdgeShellDefects() {
    WorldGraph graph = WorldGraph.generate(1777562291895L, 10, WorldGraph.WorldShape.BLOB);
    WorldgenLabReport report = WorldgenLabAnalyzer.analyze(1777562291895L, graph);
    assertThat(report.warningCounts()).doesNotContainEntry("connected_down_edge_open_outside_door", 1);
    assertThat(report.overallStatus()).isEqualTo("pass");
}
```

- [ ] **Step 2: Run tests red**

Run:

```powershell
cd java
.\gradlew.bat :shadowascent:test --tests com.indieniinja.world.lab.WorldgenLabAnalyzerTest --no-daemon
```

Expected: fails because lab classes do not exist.

- [ ] **Step 3: Implement minimal analyzer**

Add:

- `WorldgenLabReport` record with fields `worldSeed`, `overallStatus`, `qualityScore`, `roomCount`, `typeCounts`, `warningCounts`, `rooms`.
- Nested `RoomLabMetrics` record with `roomKey`, `roomType`, `solidTiles`, `platformTiles`, `airTiles`, `warnings`.
- `WorldgenLabAnalyzer.analyze(long, WorldGraph)`, generating each room grid with `ZonePlanner.plan(...)` and `RoomGenerator.generate(...)`.
- `WorldgenLabAnalyzer.analyzeRoomGrid(...)`, checking connected edges preserve shell outside the door span.

- [ ] **Step 4: Append labReport to snapshot**

In `WorldGenerationSnapshotCommand`, add:

```java
root.put("labReport", WorldgenLabAnalyzer.analyze(seed, graph).toMap());
```

Bump `GeneratorSchemaVersion.CURRENT` and `version.json.generator_schema_version` to `9`.

- [ ] **Step 5: Run Java focused tests green**

Run:

```powershell
cd java
.\gradlew.bat :shadowascent:test --tests com.indieniinja.world.lab.WorldgenLabAnalyzerTest --tests com.indieniinja.world.WorldGenerationSnapshotCommandTest --no-daemon
```

Expected: pass.

---

## Task 2: Single-Seed HTML Lab Report

**Files:**
- Create: `tools/worldgen_lab.py`
- Test: `tools/test_worldgen_lab.py`
- Optionally modify: `tools/render_worldgen_snapshot.py`

- [ ] **Step 1: Write failing Python render test**

Add a fixture snapshot in the test body and assert:

```python
def test_render_writes_html_svg_metrics_and_overlay(tmp_path):
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps({
        "worldSeed": 123,
        "megamap": {"overlayRows": ["S.", ".E"], "rooms": [], "metrics": {"roomCount": 2}},
        "labReport": {"overallStatus": "pass", "qualityScore": 100, "warningCounts": {}, "rooms": []}
    }), encoding="utf-8")
    out = tmp_path / "out"
    result = subprocess.run([sys.executable, "tools/worldgen_lab.py", "render", str(snapshot), "--out", str(out)], text=True, capture_output=True)
    assert result.returncode == 0
    assert (out / "index.html").exists()
    assert (out / "megamap.svg").exists()
    assert (out / "metrics.json").exists()
    assert (out / "overlay.txt").exists()
```

- [ ] **Step 2: Run test red**

Run:

```powershell
python tools/test_worldgen_lab.py
```

Expected: fails because `tools/worldgen_lab.py` does not exist.

- [ ] **Step 3: Implement `render` command**

Implement standard-library `argparse` command:

```powershell
python tools/worldgen_lab.py render <snapshot.json> --out <dir>
```

It writes `index.html`, `megamap.svg`, `metrics.json`, and `overlay.txt`.

- [ ] **Step 4: Run render tests green**

Run:

```powershell
python tools/test_worldgen_lab.py
```

Expected: pass.

---

## Task 3: Batch Seed Sweeper

**Files:**
- Modify: `tools/worldgen_lab.py`
- Modify: `tools/test_worldgen_lab.py`

- [ ] **Step 1: Write failing batch test**

Add a test that creates three small fixture snapshots in an input directory,
runs:

```powershell
python tools/worldgen_lab.py batch --snapshots <fixtures> --out <out>
```

Assert `summary.csv`, `summary.json`, and `failures/` exist, and the lowest
quality score appears first.

- [ ] **Step 2: Run batch test red**

Run:

```powershell
python tools/test_worldgen_lab.py
```

Expected: fails because `batch` is missing.

- [ ] **Step 3: Implement batch over existing snapshots**

Support:

```powershell
python tools/worldgen_lab.py batch --snapshots <dir> --out <dir> --failures 5
```

It reads `*.json`, sorts by `labReport.qualityScore`, writes CSV/JSON, and
renders the worst failing snapshots into `failures/<seed>/`.

- [ ] **Step 4: Add optional generated snapshot mode**

Support:

```powershell
python tools/worldgen_lab.py batch --seeds 100 --rooms 10 --shape BLOB --out <dir>
```

It shells out to `java/gradlew.bat :shadowascent:worldgenSnapshot` for each
seed on Windows.

- [ ] **Step 5: Run Python tests green**

Run:

```powershell
python tools/test_worldgen_lab.py
```

Expected: pass.

---

## Task 4: Docs, Release Metadata, and Prototype Tag

**Files:**
- Modify: `docs/guides/LEVEL_AUTHORING_GUIDE.md`
- Modify: `docs/systems/WORLD_GEN.md`
- Modify: `docs/plans/implementing/PLAN_LAYERED_HYBRID_WORLD_GENERATOR.md`
- Modify: `docs/CHANGELOG.md`
- Modify: `docs/CURRENT_STATE.md`
- Modify: `docs/ROADMAP.md`
- Modify: `README.md`
- Modify: `version.json`
- Modify: `java/build.gradle.kts`

- [ ] **Step 1: Update docs**

Document single-seed and batch commands, report outputs, and how to decide
which generation rule to tune based on warning categories.

- [ ] **Step 2: Update release metadata**

Set app version to `0.13.15`, keep generator schema version `9`, and add a
changelog entry `Worldgen Lab prototype`.

- [ ] **Step 3: Run gates**

Run:

```powershell
python tools/check_version_sync.py --tag v0.13.15
python tools/check_docs_freshness.py --emit-report
cd java
.\gradlew.bat :shadowascent:test --tests com.indieniinja.world.lab.WorldgenLabAnalyzerTest --tests com.indieniinja.world.WorldGenerationSnapshotCommandTest --no-daemon
.\gradlew.bat :server:test :client:test :server:shadowJar :client:shadowJar --no-daemon
cd ..
python tools/test_worldgen_lab.py
git diff --check
```

- [ ] **Step 4: Commit and tag**

Stage intended files only, leaving `docs/workflow/video_ideas.md` untracked.
Commit:

```powershell
git commit -m "feat(worldgen): add lab prototype"
git tag -a v0.13.15 -m "Release v0.13.15"
```

- [ ] **Step 5: Push and verify**

Run:

```powershell
git push origin master
git push origin v0.13.15
gh run watch <ci-run> --repo VainAsher/indie-ninja-adventures --exit-status
gh run watch <release-run> --repo VainAsher/indie-ninja-adventures --exit-status
gh release view v0.13.15 --repo VainAsher/indie-ninja-adventures --json tagName,name,url,assets
```

Expected: CI and Release success; release has client jar, server jar, docs ZIP.

---

## Self-Review

- Spec coverage: single-seed report, batch sweeper, docs, release all mapped to tasks.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: `WorldgenLabReport`, `WorldgenLabAnalyzer`, and `labReport` names are consistent across tasks.
