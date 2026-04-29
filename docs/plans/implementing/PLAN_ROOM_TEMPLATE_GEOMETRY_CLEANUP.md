---
doc_type: implementation_plan
status: implementing
owner: core-team
last_updated: 2026-04-29
version_anchor: v0.13.5
---

# Room Template Geometry Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring authored TMX room templates into the shared room geometry contract so strict validation can gate future template edits.

**Architecture:** Keep authored interiors intact and normalize only the outer shell expected by `RoomGeometryRules`: top edge, bottom two-tile floor, left/right wall edges, and standard midpoint door-corridor exceptions. Apply the cleanup to both canonical Java templates and the root template copies currently open in the editor.

**Tech Stack:** Tiled TMX CSV maps, Python validator, Java world generation tests.

---

### Task 1: Confirm Failing Contract

**Files:**
- Read: `java/assets/rooms/templates/*.tmx`
- Read: `assets/rooms/templates/*.tmx`

- [x] Run strict validation against `java/assets/rooms/templates`.
- [x] Run strict validation against `assets/rooms/templates`.
- [x] Confirm failures are floor gaps at row 126 under the two-tile floor rule.

### Task 2: Normalize Template Shells

**Files:**
- Modify: `java/assets/rooms/templates/*.tmx`
- Modify: `assets/rooms/templates/*.tmx`

- [x] Set top edge tiles to `SOLID` outside the standard horizontal door corridor.
- [x] Set bottom two rows to `SOLID` outside the standard horizontal door corridor.
- [x] Set left and right edge tiles to `SOLID` outside the standard vertical door corridor.
- [x] Preserve interior geometry and center door corridor exceptions.

### Task 3: Documentation

**Files:**
- Create: `docs/plans/implementing/PLAN_ROOM_TEMPLATE_GEOMETRY_CLEANUP.md`
- Modify: previous implementation plan verification notes.

- [x] Document the cleanup scope.
- [x] Update stale verification notes that previously expected strict geometry failures.

### Task 4: Verification

**Commands:**
- [x] `python tools/validate_room_templates.py --dir java/assets/rooms/templates --strict-geometry`
- [x] `python tools/validate_room_templates.py --dir assets/rooms/templates --strict-geometry`
- [x] `python tools/validate_room_templates.py --dir java/assets/rooms/templates`
- [x] `python tools/validate_room_templates.py --dir assets/rooms/templates`
- [x] `cd java; ./gradlew.bat :shadowascent:test --tests com.indieniinja.world.RoomGeometryRulesTest --no-daemon`
- [x] `cd java; ./gradlew.bat :server:test --tests com.indieniinja.server.WorldGraphGenerationTest --no-daemon`
- [x] `git diff --check`
  - Result: no whitespace errors; Git reports CRLF normalization warnings for touched TMX and Java files.

**Compatibility:** Authored template edge tiles change. Runtime already enforced the same shell rules before door carving, so this aligns source assets with runtime behavior instead of introducing a new gameplay rule.
