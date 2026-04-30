# Worldgen Lab Act 1 Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development or superpowers:executing-plans.

**Goal:** Make seed `420` the Act 1 worldgen baseline and add the minimum
before/after reporting needed for fast formation tuning.

**Architecture:** Extend the existing static Python lab renderer. Do not change
runtime world generation or snapshot schema.

## File Map

- Modify `tools/worldgen_lab.py`: add `act1`, `compare`, `pipeline.json`, and
  `pipeline.svg`.
- Modify `tools/test_worldgen_lab.py`: cover render artifacts, Act 1 baseline
  rendering from an existing snapshot, and compare deltas.
- Modify docs: worldgen system docs, level authoring guide, layered generator
  plan, changelog/current state/roadmap/readme/version metadata.

## Tasks

- [x] Add failing tests for pipeline artifacts in `render`.
- [x] Add failing test for `act1 --snapshot` rendering seed `420`.
- [x] Add failing test for `compare` quality, warning, and checksum deltas.
- [x] Implement pipeline summary and visual stage strip.
- [x] Implement `act1` command with seed `420` defaults.
- [x] Implement `compare` command.
- [x] Update docs and release metadata for `v0.13.17`.
- [x] Run local gates.
- [ ] Commit, tag, push, and verify CI/release assets.

## Verification

```powershell
python tools/test_worldgen_lab.py
python tools/check_version_sync.py --tag v0.13.17
python tools/check_docs_freshness.py --emit-report
cd java
.\gradlew.bat :shadowascent:test --tests com.indieniinja.world.lab.WorldgenLabAnalyzerTest --tests com.indieniinja.world.WorldGenerationSnapshotCommandTest --no-daemon
.\gradlew.bat :server:test :client:test :server:shadowJar :client:shadowJar --no-daemon
cd ..
git diff --check
```
