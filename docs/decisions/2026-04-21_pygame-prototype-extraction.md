---
doc_type: decision_record
status: accepted
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Decision: Extract Pygame Prototype From `indie-ninja-adventures`

- Date: 2026-04-21
- Status: accepted
- Owners: core-team

## Context

The repository now contains two diverged game lines:

- Java stack (libGDX + Netty) which is the active runtime and release direction.
- Legacy Python/Pygame prototype (`demo_game.py`, root python systems, python-only tests, and python EXE build lane).

The two lines no longer share a stable compatibility contract (client protocol assumptions, game modes, launcher behavior, and testing surfaces differ). Keeping both lines in one repo has increased process drift, stale docs, and CI/release coupling risk.

## Decision

The Pygame prototype and `ninja_dash.exe` production lane will be split out of this repository into a separate project.

`indie-ninja-adventures` remains the Java-first game repository. During migration, legacy python paths remain temporarily available only as an explicit compatibility lane.

Implementation checkpoint (2026-04-21):
- Launcher fallback to `demo_game.py` removed.
- CI default lane switched to Java build/test ownership.
- Release lane switched to Java JAR + docs archive assets (no `ninja_dash.exe` build in this repo).

## Alternatives Considered

1. Keep both stacks in one repo with stricter folder boundaries.
: Rejected - still couples release, docs, CI, and ownership surfaces.
2. Keep python runtime in this repo but archive only docs.
: Rejected - does not remove build/test/release coupling.
3. Immediate hard delete of python runtime in this repo.
: Rejected - high operational risk without migration and handover path.

## Consequences

- Positive:
  - Clear ownership and architecture boundary.
  - Cleaner CI/release semantics for Java runtime.
  - Reduced stale-doc and stale-test noise in this repo.
- Negative:
  - Short-term migration overhead (repo setup, handover docs, release path changes).
  - Temporary dual-maintenance until split completes.
- Operational follow-up:
  - Execute `PLAN_PYGAME_EXTRACTION.md`.
  - Maintain explicit migration checkpoints and rollback options.

## Related Docs and Systems

- [PLAN_PYGAME_EXTRACTION.md](../plans/implementing/PLAN_PYGAME_EXTRACTION.md)
- [PYGAME_EXTRACTION_INVENTORY.md](../operations/PYGAME_EXTRACTION_INVENTORY.md)
- [PYGAME_SPLIT_CHECKLIST.md](../operations/PYGAME_SPLIT_CHECKLIST.md)
- [CURRENT_STATE.md](../CURRENT_STATE.md)
- [INDEX.md](../INDEX.md)
