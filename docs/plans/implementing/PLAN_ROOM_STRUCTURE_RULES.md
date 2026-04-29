---
doc_type: implementation_plan
status: implementing
owner: core-team
last_updated: 2026-04-29
version_anchor: v0.13.5
---

# Room Structure Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move room-level zone structure out of hardcoded planner switches and into data-driven rules.

**Architecture:** Keep the existing `ZonePlanner -> RoomGenerator -> ZoneTemplateLibrary` pipeline, but insert a `RoomStructureRules` model that controls fill counts, hazard odds, DECOR finalization, perimeter depth, and center arena clearing. This gives room types stable intent before the 8x8 zone templates are mixed into the final tile grid.

**Tech Stack:** Java 21, Jackson, JUnit 5, AssertJ, JSON config under `data/`.

---

### Task 1: Rule Model

**Files:**
- Create: `java/shadowascent/src/main/java/com/indieniinja/world/RoomStructureRules.java`
- Test: `java/shadowascent/src/test/java/com/indieniinja/world/RoomStructureRulesTest.java`

- [x] Add `RoomStructureRules` and `RoomSpec` records.
- [x] Load `data/room_structure_rules.json`, with `ninja.roomStructureRules` system-property override.
- [x] Clamp counts, chances, perimeter depth, and center-clear radius to safe values.
- [x] Fall back to Java defaults if JSON is missing or invalid.

### Task 2: Planner Integration

**Files:**
- Modify: `java/shadowascent/src/main/java/com/indieniinja/world/ZonePlanner.java`
- Test: `java/shadowascent/src/test/java/com/indieniinja/world/RoomStructureRulesTest.java`

- [x] Replace room-type fill counts with `RoomSpec.fillMin/fillMax`.
- [x] Replace hazard probabilities with `RoomSpec` chance fields.
- [x] Replace DECOR finalization probabilities with `RoomSpec` chance fields.
- [x] Replace hardcoded perimeter depth with `RoomSpec.perimeterDepth`.
- [x] Add `centerClearRadiusZones` to preserve open arenas after finalization.

### Task 3: Data File

**Files:**
- Create: `data/room_structure_rules.json`

- [x] Encode the current hardcoded behavior as default data.
- [x] Set `boss.centerClearRadiusZones` to `1` so boss rooms keep a 3x3 open center.

### Task 4: Documentation

**Files:**
- Modify: `docs/systems/WORLD_GEN.md`
- Modify: `docs/dev/TILED_SETUP.md`

- [x] Document structure rules and their effect on generated zone plans.
- [x] Document how authored TMX templates relate to procedural structure rules.

### Task 5: Verification

**Commands:**
- [x] `cd java; ./gradlew.bat :shadowascent:test --tests com.indieniinja.world.RoomStructureRulesTest --no-daemon`
- [x] `cd java; ./gradlew.bat :shadowascent:test --tests com.indieniinja.world.RoomGeometryRulesTest --no-daemon`
- [x] `cd java; ./gradlew.bat :server:test --tests com.indieniinja.server.WorldGraphGenerationTest --no-daemon`
- [x] `python tools/validate_room_templates.py --dir java/assets/rooms/templates`
- [x] `python tools/validate_room_templates.py --dir java/assets/rooms/templates --strict-geometry`
  - Result after `PLAN_ROOM_TEMPLATE_GEOMETRY_CLEANUP.md`: all Java templates pass strict geometry.
- [x] `git diff --check`
  - Result: no whitespace errors; Git reports CRLF normalization warnings for touched Java files.

**Compatibility:** Replay-breaking for procedural room zone plans because changing `data/room_structure_rules.json` changes room shape and hazard placement. Save and protocol formats are unchanged.
