# Shadow Ascent Agent Operating Context

Repository-level operating context for Claude agents working in the Shadow Ascent codebase.

## Canonical Reads

Read these first before planning, editing, reviewing, or proposing process changes:

1. `README.md`
2. `docs/INDEX.md`
3. `docs/CURRENT_STATE.md`
4. Relevant workflow docs in `docs/workflow/`
5. Relevant design / technical / production / operations docs routed from `docs/INDEX.md`

## Source-of-Truth Policy

- `README.md` defines project and repository shape.
- `docs/INDEX.md` is the canonical documentation router.
- `docs/workflow/` contains operational policy.
- Version truth comes from `version.json`.
- Do not create a second source of truth in agent notes, ad hoc plans, or temporary summaries.

## Repo and Product Boundaries

Shadow Ascent spans more than one repository:

- `indie-ninja-adventures` — game source, CI/CD, build pipeline
- `indie-ninja-launcher` — launcher executable, player guides, GitHub Pages
- `indie-ninja-feedback` — public bugs, feature requests, player feedback
- `indie-ninja-pipeline` — planning, triage, release management

Agents must call out cross-repo impact explicitly. Do not assume a change is isolated to this repo.

## General Engineering Rules

- Prefer the smallest safe change.
- Scope before implementation.
- Validate before declaring done.
- Update canonical docs instead of duplicating content.
- Preserve evidence for bugs, regressions, and balancing changes.
- Escalate when documentation conflicts or architecture truth is unclear.
- Stop when save, replay, or protocol compatibility risk cannot be classified safely.

## Required Validation Mindset

Every meaningful change should answer:

- What changed?
- What player or developer behavior is affected?
- What systems are touched?
- What tests or smoke checks prove safety?
- What docs must be updated?
- What compatibility class applies?
- What evidence should be preserved?

## Escalation Defaults

Escalate instead of guessing when any of the following are true:

- canonical docs conflict
- architecture truth is missing or stale
- save compatibility may break
- replay determinism may break
- network protocol compatibility may break
- repo ownership is unclear
- task scope crosses unrelated systems
- security, privacy, licensing, or visibility concerns appear

## Preferred Agent Order

Default entry point is the coordinator agent.

Typical chains:

- Feature work: `coordinator -> implementation -> review`
- Bug / replay / desync: `coordinator -> debug -> implementation -> review`
- Process / workflow / docs system work: `coordinator -> process-librarian -> review`

## Output Quality Rules

Agents should produce:

- concise task summary
- canonical docs consulted
- systems touched
- risk statement
- required tests or evidence
- docs to update
- escalation conditions

Avoid vague reassurance. Be explicit about uncertainty.
