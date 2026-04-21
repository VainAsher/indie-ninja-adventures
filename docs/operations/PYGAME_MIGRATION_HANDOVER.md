---
doc_type: operations
status: living
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Pygame Migration Handover

Migration handover for the extraction of the legacy Pygame runtime lane from `indie-ninja-adventures`.

## Cutover Summary (2026-04-21)

- Launcher fallback to `demo_game.py` removed.
- CI and release defaults moved to Java JAR lanes.
- Legacy prototype source/test/build paths removed from this repository after transfer verification.
- Prototype lane continues in `VainAsher/indie-ninja-prototype`.

## Ownership Map

| Repository | Scope Owner | Primary Responsibility | Out of Scope |
| --- | --- | --- | --- |
| `VainAsher/indie-ninja-adventures` | Core game runtime team | Java server/client runtime, Java CI/release, canonical gameplay delivery | Pygame runtime feature work and EXE build lane |
| `VainAsher/indie-ninja-prototype` | Prototype lane owner | Legacy Pygame runtime, prototype tests, prototype EXE build specs | Java runtime release gates |
| `VainAsher/indie-ninja-launcher` | Launcher lane owner | Launcher updates, install/update UX, release asset resolution | Core game engine/runtime implementation |
| `VainAsher/indie-ninja-feedback` | Player-facing intake owner | Public bug/feedback intake and issue templates | Sprint planning and implementation sequencing |
| `VainAsher/indie-ninja-pipeline` | Delivery coordination owner | Internal triage, backlog/sprint flow, release coordination | Public player support intake |

## Cross-Repo Coordination Links

- Launcher JAR-first coordination: `https://github.com/VainAsher/indie-ninja-launcher/issues/1`
- Prototype normalization follow-up: `https://github.com/VainAsher/indie-ninja-prototype/issues/1`
- Feedback intake/labels alignment: `https://github.com/VainAsher/indie-ninja-feedback/issues/2`
- Pipeline triage loop wiring: `https://github.com/VainAsher/indie-ninja-pipeline/issues/1`

## Active Support Boundaries

- Game runtime regressions in Java lane: file in `indie-ninja-adventures`.
- Prototype/Pygame regressions: file in `indie-ninja-prototype`.
- Launcher distribution/update regressions: file in `indie-ninja-launcher`.
- Player-facing bug reports and feature requests: open in `indie-ninja-feedback`.
- Triage prioritization and sprint intake: manage in `indie-ninja-pipeline`.

## Close-Out Audit (2026-04-21)

- Split-era extraction planning notes archived under `docs/archive/retired/2026-04-21_v0.11.71_pygame-extraction/`.
- Living doc routing updated (`docs/INDEX.md`, `docs/CURRENT_STATE.md`, extraction redirect docs).
- Workflow/release hygiene validated after extraction cutover (CI run `24712532879` passed).
