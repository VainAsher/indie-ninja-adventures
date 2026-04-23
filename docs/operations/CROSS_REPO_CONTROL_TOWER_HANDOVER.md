---
doc_type: operations
status: living
owner: core-team
last_updated: 2026-04-24
version_anchor: v0.12.06
---

# Cross-Repo Control Tower Handover

Handover for the multi-repo operating model where `indie-ninja-pipeline` is the planning and coordination control tower.

## Purpose

Provide one operating reference for ownership, workflow placement, and release coordination across:

- `indie-ninja-adventures` (private source/runtime)
- `indie-ninja-launcher` (public launcher/distribution)
- `indie-ninja-feedback` (public player intake)
- `indie-ninja-pipeline` (private planning/triage/reporting)

## Session Changes Landed

1. Pipeline scaffold promoted to control-tower model:
   - `docs/repo-scaffolds/pipeline-repo/README.md`
   - `docs/repo-scaffolds/pipeline-repo/workflow/INTAKE.md`
   - `docs/repo-scaffolds/pipeline-repo/workflow/TRIAGE.md`
   - `docs/repo-scaffolds/pipeline-repo/workflow/SPRINT_PLANNING.md`
   - `docs/repo-scaffolds/pipeline-repo/workflow/EXECUTION_LOOP.md`
   - `docs/repo-scaffolds/pipeline-repo/workflow/RELEASE_CYCLE.md`
   - `docs/repo-scaffolds/pipeline-repo/dashboard/DASHBOARD.md`
   - `docs/repo-scaffolds/pipeline-repo/dashboard/BACKLOG.md`

2. New coordination contracts added to scaffold:
   - `docs/repo-scaffolds/pipeline-repo/coordination/REPO_CONTRACTS.md`
   - `docs/repo-scaffolds/pipeline-repo/coordination/CROSS_REPO_EVENT_CONTRACTS.md`

3. New pipeline intake workflow scaffolded:
   - `docs/repo-scaffolds/pipeline-repo/.github/workflows/feedback_intake_sync.yml`

4. Local cross-repo workflow guidance updated:
   - `docs/workflow/CROSS_REPO_COORDINATION.md`

## Control-Tower Operating Decision

Master planning and cross-repo coordination live in `indie-ninja-pipeline`.

That includes:

- intake summary and triage control
- sprint board ownership
- cross-repo dependency tracking
- release coordination and monthly reporting

Runtime implementation remains in source repos.

## Implementation Checklist

### A. Pipeline Repo

- [x] Copy scaffold updates from `docs/repo-scaffolds/pipeline-repo/` — applied; `README.md`, `coordination/`, `dashboard/`, `workflow/` all present
- [x] Create/confirm intake issue and set `INTAKE_ISSUE_NUMBER` — issue #2 ("Weekly Intake Tracking") open; `INTAKE_ISSUE_NUMBER: 2` confirmed in live workflow
- [x] `CROSS_REPO_PAT` — not required; pipeline uses `github.token` (feedback repo is public)
- [x] Enable `feedback_intake_sync.yml` and run `workflow_dispatch` dry run — 3 confirmed successful runs (latest 2026-04-23)
- [x] Link board fields to severity/system labels — 13 labels mirrored from feedback to pipeline on 2026-04-24: `feature`, `feedback`, `performance`, `multiplayer`, `urgent`, `replay-system`, `ui`, `combat`, `needs-triage`, `world-gen`, `needs-info`, `wont-fix`, `fixed`

### B. Game Repo (`indie-ninja-adventures`)

- [x] Keep `release.yml` as source-of-truth release producer
- [x] Keep Java-first gates (`:server:test`, `:client:test`, shadow JARs)
- [x] Keep release dispatch to launcher using payload contract — `CROSS_REPO_PAT` configured; dispatch confirmed working for v0.12.02–v0.12.06
- [x] `sync_feedback.yml` retired to deprecated stub pointing to pipeline issue #2

### C. Launcher Repo

- [x] Validate `receive_game_release.yml` consumes current payload shape — 5 confirmed successful `game-release` dispatch runs
- [x] Release announcement issues created per release — issues #6–#10 created automatically (v0.12.02–v0.12.06)
- [x] Launcher release pipeline isolated from game runtime ownership — uses `github.token` only, no cross-repo secrets required
- [x] Old release announcement issues closed — issues #6–#9 closed on 2026-04-24; issue #10 (v0.12.06) is the current open announcement

### D. Feedback Repo

- [x] Labels align with pipeline triage categories — `bug`, `feature`, `feedback`, `performance`, `urgent`, plus system labels (`combat`, `world-gen`, `ui`, `replay-system`, `multiplayer`) are present
- [x] Issue forms present — `bug_report.yml`, `feature_request.yml`, `gameplay_feedback.yml`, `performance_issue.yml`
- [x] Pinned "Latest Release" issue — issue #1 ("Welcome and Latest Release Tracking") is pinned and updated with v0.12.06 on 2026-04-24

### E. End-to-End Verification Gate

- [x] Game release tagged and assets published — confirmed for v0.12.06
- [x] Launcher receives dispatch and posts release announcement — confirmed (5 runs)
- [x] Feedback intake summary appears in pipeline intake issue #2 — confirmed (3 runs)
- [x] Contract 3 (feedback resolution loop) — exercised 2026-04-24: feedback #7 (replay non-determinism) triaged with v0.12.06 release link + `fixed` label; feedback #6 (mission soft lock) triaged with v0.12.04 reference; feedback #1 (welcome/latest release) updated with v0.12.06 link

## Risk Notes

- If both game and pipeline run intake sync on the same cadence, duplicate summaries will appear.
- `CROSS_REPO_PAT` drift or missing scope is the most common breakage in cross-repo automation.
- Event payload changes without consumer update will silently degrade launcher coordination.

## Verification Gate

Before calling migration complete, run one release dry run and prove:

1. Game release tagged and assets published
2. Launcher receives dispatch and posts expected announcement/update signal
3. Feedback intake summary appears in pipeline intake issue
4. One feedback issue is linked through pipeline -> source -> release -> feedback closure comment

## Ownership Reminder

This handover is process ownership. It does not replace repo-local release or test checklists.
