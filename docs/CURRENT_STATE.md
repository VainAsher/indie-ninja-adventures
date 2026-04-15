---
doc_type: current_state
status: living
owner: core-team
last_updated: 2026-04-15
version_anchor: v0.11.47
replaces: docs/HANDOVER.md
---

# Current State

Canonical runtime and handover snapshot for the active Java stack.

## Baseline

- Date baseline: 2026-04-15
- Version baseline: v0.11.47
- Platform baseline: Windows desktop
- Engine stack: Java 21 + libGDX + Netty
- Source of truth for release metadata: `version.json`

## Product State

- Product direction: campaign-first single-player with optional multiplayer overlay.
- Active execution plan: [`docs/plans/implementing/PLAN_SHADOW_ASCENT.md`](plans/implementing/PLAN_SHADOW_ASCENT.md)
- Current milestone lane: P0 stabilization and onboarding/runtime evidence hardening.

## Runtime Reality (Implemented)

- Authoritative server loop, zone simulation, and snapshot replication are active.
- Client rendering/UI loop is on libGDX desktop runtime.
- Mission lifecycle tracing and session-correlation logging are active.
- Siren-first onboarding flow and objective/mission affordances are active.
- Release/version parity gate is enforced through `tools/check_version_sync.py`.

## Canonical Documentation Set

- [INDEX.md](INDEX.md) - top-level documentation routing
- [ROADMAP.md](ROADMAP.md) - milestone sequencing and current targets
- [CHANGELOG.md](CHANGELOG.md) - release-facing version history
- [PLAYER_EXPECTATIONS.md](PLAYER_EXPECTATIONS.md) - launcher-first playtest contract
- [GDD.md](GDD.md) - design intent and narrative/mechanics contracts
- [RELEASE_VERSION_SYNC_CHECKLIST.md](RELEASE_VERSION_SYNC_CHECKLIST.md) - release metadata gate

## Repository Process Defaults

- Plan-embedded tasks are canonical for implementation tracking.
- `docs/TASK_LIST.md` is historical and archived.
- Retired/stale docs move immediately to `docs/archive/retired/`.
- Archive ZIP snapshots are kept in `docs/archive/zips/` and mirrored to release assets.
- Docs freshness checks are warning-only in CI unless explicitly run in strict mode.
