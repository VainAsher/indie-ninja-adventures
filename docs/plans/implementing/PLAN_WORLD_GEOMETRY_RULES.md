---
doc_type: implementation_plan
status: implementing
owner: core-team
last_updated: 2026-04-29
version_anchor: v0.13.5
---

# World Geometry Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a data-driven geometry rule layer so procedural and authored rooms can enforce wall, floor, and door-corridor structure.

**Architecture:** Introduce a small rules object owned by `java/shadowascent/world`, then route procedural room boundary creation and door carving through it. Extend template validation so authored TMX files can be checked against the same assumptions without changing Tiled authoring flow.

**Tech Stack:** Java 21, JUnit 5, AssertJ, Python 3 XML validation script, Tiled TMX CSV maps.

---

### Task 1: Geometry Rule Model

**Files:**
- Create: `java/shadowascent/src/main/java/com/indieniinja/world/RoomGeometryRules.java`
- Test: `java/shadowascent/src/test/java/com/indieniinja/world/RoomGeometryRulesTest.java`

- [x] Add immutable defaults for room size, edge thickness, floor thickness, door half-span, and door carve depth.
- [x] Add JSON loading with fallback to defaults when a config file is absent.
- [x] Verify invalid numeric values are clamped to safe minimums.

### Task 2: Procedural Enforcement

**Files:**
- Modify: `java/shadowascent/src/main/java/com/indieniinja/world/RoomGenerator.java`
- Test: `java/shadowascent/src/test/java/com/indieniinja/world/RoomGeometryRulesTest.java`

- [x] Replace hardcoded boundary and door-carve constants with `RoomGeometryRules`.
- [x] Enforce full floor thickness for rooms without a down neighbor.
- [x] Preserve door corridor openings for connected directions.
- [x] Keep template-first behavior, then apply door carving through the shared rule object.

### Task 3: Template Validation

**Files:**
- Modify: `tools/validate_room_templates.py`

- [x] Add optional geometry rule checks for edge walls, floor thickness, and standable tiles.
- [x] Treat standard door corridors as allowed edge exceptions.
- [x] Keep existing basic validation path intact.

### Task 4: Authoring Docs

**Files:**
- Modify: `docs/dev/TILED_SETUP.md`
- Modify: `docs/systems/WORLD_GEN.md`

- [x] Document canonical template path.
- [x] Document room geometry rules and validation command.
- [x] Explain the difference between authored full-room TMX templates and procedural zone templates.

### Task 5: Verification

**Commands:**
- [x] `cd java; ./gradlew.bat :shadowascent:test --tests com.indieniinja.world.RoomGeometryRulesTest --no-daemon`
- [x] `python tools/validate_room_templates.py --dir java/assets/rooms/templates`
- [x] `python tools/validate_room_templates.py --dir java/assets/rooms/templates --strict-geometry`
  - Initial result: surfaced authored template floor gaps at row 126 under the new two-tile floor rule.
  - Current result after `PLAN_ROOM_TEMPLATE_GEOMETRY_CLEANUP.md`: all Java templates pass strict geometry.
- [x] `cd java; ./gradlew.bat :server:test --tests com.indieniinja.server.WorldGraphGenerationTest --no-daemon`

**Compatibility:** Replay-breaking for procedural room geometry because floor thickness and door carving can alter deterministic tile output. Save and protocol formats are unchanged.
