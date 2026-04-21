---
doc_type: implementation_brief
status: completed
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Implementation Brief: Java Systems Docs Rewrite and Python Archive

## Goal

Replace `docs/systems/*` with Java-canonical system docs and archive the Python/Pygame versions.

## Player-facing impact

Indirect but high: internal docs used for design, QA, and signoff reflect current Java runtime behavior instead of legacy Python behavior.

## Systems touched

- Documentation routing and canonical ownership (`docs/systems`, `docs/INDEX.md`)
- Archive structure (`docs/archive/retired/*`)
- Decision tracking (`docs/decisions/*`)
- Devlog capture (`docs/devlog/2026-04.md`)

## Risks

- Broken links or stale pointers after archive move
- Accidental carryover of Python-era claims into Java docs
- Partial archive without clear manifest

## Required tests

- `python tools/check_version_sync.py`

## Required docs to update

- `docs/systems/*.md` (all active system docs)
- `docs/INDEX.md` (routing)
- `docs/decisions/INDEX.md` and new decision record
- `docs/devlog/2026-04.md` (capture entry)

## Rollback plan

- Restore active docs from archived copies in the same change set:
  - copy `docs/archive/retired/2026-04-21_v0.11.71_python-systems-docs/*.md`
    back to `docs/systems/`

## Completion evidence

- `python tools/check_version_sync.py` passed on 2026-04-21 (`Version synchronization OK: v0.11.71`).
- Java-canonical system docs written in `docs/systems/*.md`.
- Legacy Python/Pygame systems docs archived in `docs/archive/retired/2026-04-21_v0.11.71_python-systems-docs/`.
- Routing/traceability updates captured in `docs/INDEX.md`, `docs/decisions/INDEX.md`, `docs/decisions/2026-04-21_java-systems-docs-canonicalization.md`, and `docs/devlog/2026-04.md`.
