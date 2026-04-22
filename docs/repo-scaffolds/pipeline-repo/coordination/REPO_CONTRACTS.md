# Repo Contracts

Canonical ownership contract for the Indie Ninja multi-repo setup.

Last reviewed: 2026-04-21

---

## Contract Summary

| Repo | Visibility | Primary Purpose | Owns | Must Not Own |
|------|------------|-----------------|------|--------------|
| `indie-ninja-adventures` | Private | Core game source + Java build/release | Java runtime code, tests, release assets (JAR + docs zip), technical docs | Public feedback intake, sprint board management |
| `indie-ninja-launcher` | Public | Player launcher distribution + update UX | Launcher code, launcher releases, player install/update docs | Game runtime implementation or internal sprint planning |
| `indie-ninja-feedback` | Public | Player issue intake | Issue forms, auto-labeling, acknowledgement responses, public bug/feature tracking | Internal planning and prioritization decisions |
| `indie-ninja-pipeline` | Private | Delivery control tower | Master planning, triage, backlog/sprint board, cross-repo coordination, weekly/monthly reporting | Runtime build artifacts and player-facing binaries |

---

## Planning Rules

1. Master roadmap and sprint sequencing are owned by `indie-ninja-pipeline`.
2. Source repos keep implementation-level plans only.
3. Cross-repo decisions must be recorded in pipeline issues or decision docs.
4. Every player-facing release note maps back to planned work in pipeline.

---

## Handoff Rules

- Feedback -> Pipeline: via weekly intake sync + linked issue creation
- Pipeline -> Source: via scoped implementation tasks
- Source -> Launcher: via release event contract (see `CROSS_REPO_EVENT_CONTRACTS.md`)
- Source/Launcher -> Feedback: via "fixed in version" closure updates

---

## Branch and Merge Rules

- `indie-ninja-adventures`: use feature branches into `main` (or `develop` if explicitly re-enabled)
- `indie-ninja-launcher`: feature branches into `main`
- `indie-ninja-feedback`: workflow/templates on `main`
- `indie-ninja-pipeline`: planning/workflow updates on `main`

No release tag should be pushed without passing the repo-local release checklist.

---

## Audit Rules

For every shipped release, keep these links discoverable:

- Source implementation issue/PR
- Pipeline planning issue
- Feedback source issue(s)
- Player-facing changelog/announcement

Missing links means the work is not audit-complete.
