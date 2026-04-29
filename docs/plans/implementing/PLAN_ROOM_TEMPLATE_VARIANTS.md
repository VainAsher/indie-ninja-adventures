---
doc_type: implementation_plan
status: implementing
owner: core-team
last_updated: 2026-04-29
version_anchor: v0.13.5
---

# Room Template Variants Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow authored TMX room templates to have deterministic weighted variants instead of one hardcoded file per room type.

**Architecture:** Add a `RoomTemplateCatalog` resolver below `TmxRoomLoader`. `RoomGenerator` passes the room seed into template loading, the catalog selects a concrete TMX path, and `TmxRoomLoader` parses that selected file. Existing `<roomType>.tmx` lookup remains the fallback.

**Tech Stack:** Java 21, Jackson, JUnit 5, AssertJ, Tiled TMX files, JSON config under `data/`.

---

### Task 1: Catalog Resolver

**Files:**
- Create: `java/shadowascent/src/main/java/com/indieniinja/world/RoomTemplateCatalog.java`
- Test: `java/shadowascent/src/test/java/com/indieniinja/world/RoomTemplateCatalogTest.java`

- [x] Load explicit weighted entries from `data/room_template_catalog.json`.
- [x] Support `ninja.roomTemplateCatalog` system-property override.
- [x] Ignore missing explicit files and fall back to convention discovery.
- [x] Discover `<roomType>.tmx`, `<roomType>_*.tmx`, and `<roomType>-*.tmx` in sorted order.
- [x] Select deterministically from room seed.

### Task 2: Loader Integration

**Files:**
- Modify: `java/shadowascent/src/main/java/com/indieniinja/world/TmxRoomLoader.java`
- Modify: `java/shadowascent/src/main/java/com/indieniinja/world/RoomGenerator.java`

- [x] Add seed-aware `TmxRoomLoader.loadTemplate(roomTypeId, roomSeed)`.
- [x] Route `RoomGenerator` template loads through the seed-aware loader.
- [x] Preserve `loadTemplate(roomTypeId)` compatibility by using seed `0`.

### Task 3: Catalog Data

**Files:**
- Create: `data/room_template_catalog.json`

- [x] Encode current authored templates as one-entry weighted sets.
- [x] Keep behavior stable until additional variant TMX files are added.

### Task 4: Documentation

**Files:**
- Modify: `docs/dev/TILED_SETUP.md`
- Modify: `docs/systems/WORLD_GEN.md`

- [x] Document JSON weighted variants.
- [x] Document filename convention fallback.
- [x] Explain that selected TMX templates still receive runtime geometry enforcement.

### Task 5: Verification

**Commands:**
- [x] `cd java; ./gradlew.bat :shadowascent:test --tests com.indieniinja.world.RoomTemplateCatalogTest --no-daemon`
- [x] `cd java; ./gradlew.bat :shadowascent:test --tests com.indieniinja.world.RoomStructureRulesTest --no-daemon`
- [x] `cd java; ./gradlew.bat :shadowascent:test --tests com.indieniinja.world.RoomGeometryRulesTest --no-daemon`
- [x] `cd java; ./gradlew.bat :server:test --tests com.indieniinja.server.WorldGraphGenerationTest --no-daemon`
- [x] `python tools/validate_room_templates.py --dir java/assets/rooms/templates`
- [x] `python tools/validate_room_templates.py --dir java/assets/rooms/templates --strict-geometry`
  - Result after `PLAN_ROOM_TEMPLATE_GEOMETRY_CLEANUP.md`: all Java templates pass strict geometry.
- [x] `git diff --check`
  - Result: no whitespace errors; Git reports CRLF normalization warnings for touched Java files.

**Compatibility:** Existing template names still work. Adding new variants or changing weights is replay-breaking because a room seed may resolve to a different authored TMX.
