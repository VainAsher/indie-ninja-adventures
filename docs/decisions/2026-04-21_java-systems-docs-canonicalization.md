---
doc_type: decision_record
status: accepted
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# 2026-04-21 - Java Systems Docs Canonicalization

## Metadata

- Date: 2026-04-21
- Title: Java systems docs become canonical; Python systems docs archived
- Status: `accepted`
- Owners: core-team

## Context

`docs/systems` described the legacy Python/Pygame runtime while current implementation is Java (`java/client`, `java/core`, `java/shadowascent`, `java/server`). This created signoff and controls-traceability risk for current releases.

## Decision

- `docs/systems/*` is defined as Java-canonical documentation.
- Python-era system docs are archived under:
  - `docs/archive/retired/2026-04-21_v0.11.71_python-systems-docs/`
- Routing docs are updated to point to the canonical active set and the archive location.

## Alternatives Considered

1. Keep mixed Python + Java content in the same files:
   - Rejected because it preserves ambiguity and encourages stale references.
2. Keep Python docs in place and add Java addenda only:
   - Rejected because canonical ownership remains unclear.
3. Delete Python docs outright:
   - Rejected because historical extraction and migration context is still useful.

## Consequences

- Positive:
  - Active docs now map directly to current runtime code.
  - Archive preserves migration history without polluting active references.
  - Easier P0/P1 evidence traceability for Java milestones.
- Negative:
  - Short-term rewrite effort across all system docs.
  - Existing bookmarks into legacy paths must be re-routed.
- Operational follow-up:
  - Keep new system docs synchronized with Java module changes.
  - Route future Python references only through archive/legacy docs.

## Related Docs and Systems

- Docs:
  - `docs/systems/*.md`
  - `docs/archive/retired/2026-04-21_v0.11.71_python-systems-docs/`
  - `docs/INDEX.md`
  - `docs/workflow/DOCUMENTATION_ROUTING_WORKFLOW.md`
  - `docs/workflow/REPO_HYGIENE_AND_ARCHIVE.md`
- Runtime systems:
  - `java/client`, `java/core`, `java/shadowascent`, `java/server`

## Supersession

- Supersedes: none
- Superseded by: none

