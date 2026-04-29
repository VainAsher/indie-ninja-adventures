---
doc_type: implementation_plan
status: implementing
owner: core-team
last_updated: 2026-04-29
version_anchor: v0.13.5
---

# Room Template Catalog Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a release guardrail that validates data-driven room template catalog entries against authored TMX files.

**Architecture:** Extend `tools/validate_room_templates.py` with a catalog validator and `--catalog` CLI option. The validator checks JSON shape, file existence, path safety, and positive weights. Catalog validation is intended for the canonical Java template directory because `data/room_template_catalog.json` describes the full runtime template set.

**Tech Stack:** Python 3 standard library, unittest, JSON, Tiled TMX files.

---

### Task 1: Failing Tests

**Files:**
- Create: `tools/test_validate_room_templates.py`

- [x] Add test for missing catalog template file.
- [x] Add test for non-positive catalog weight.
- [x] Add test for valid existing weighted entry.
- [x] Run `python tools/test_validate_room_templates.py` and verify it fails because `validate_template_catalog` is missing.

### Task 2: Validator Implementation

**Files:**
- Modify: `tools/validate_room_templates.py`

- [x] Add `validate_template_catalog(catalog_path, template_dir)`.
- [x] Validate required `roomTypes` object.
- [x] Validate each room entry is a non-empty list.
- [x] Validate each variant has a local `file`, an existing TMX path, and `weight >= 1`.
- [x] Add `--catalog` CLI option.

### Task 3: Documentation

**Files:**
- Modify: `docs/dev/TILED_SETUP.md`
- Modify: `docs/systems/WORLD_GEN.md`
- Create: `docs/guides/LEVEL_AUTHORING_GUIDE.md`

- [x] Document canonical catalog validation command.
- [x] Document that root editor templates can be geometry-validated but do not contain the full catalog set.
- [x] Add comprehensive level, room, zone, and rule authoring guide.

### Task 4: Verification

**Commands:**
- [x] `python tools/test_validate_room_templates.py`
- [x] `python tools/validate_room_templates.py --dir java/assets/rooms/templates --strict-geometry --catalog data/room_template_catalog.json`
- [x] `python tools/validate_room_templates.py --dir assets/rooms/templates --strict-geometry`

**Compatibility:** No runtime behavior changes. This slice only adds validation and documentation around existing data-driven template selection.
