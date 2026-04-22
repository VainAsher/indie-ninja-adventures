---
doc_type: operations
status: living
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
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

## Implementation Checklist (Next Actions)

### A. Pipeline Repo

- [ ] Copy scaffold updates from `docs/repo-scaffolds/pipeline-repo/`
- [ ] Create/confirm intake issue and set `INTAKE_ISSUE_NUMBER`
- [ ] Add `CROSS_REPO_PAT`
- [ ] Enable `feedback_intake_sync.yml` and run `workflow_dispatch` dry run
- [ ] Link board fields to severity/system labels

### B. Game Repo (`indie-ninja-adventures`)

- [ ] Keep `release.yml` as source-of-truth release producer
- [ ] Keep Java-first gates (`:server:test`, `:client:test`, shadow JARs)
- [ ] Keep release dispatch to launcher using payload contract
- [ ] Decide whether to retire local `sync_feedback.yml` after pipeline sync is verified

### C. Launcher Repo

- [ ] Validate `receive_game_release.yml` consumes current payload shape
- [ ] Align release announcement text with JAR-first game lane
- [ ] Keep launcher release pipeline isolated from game runtime ownership

### D. Feedback Repo

- [ ] Confirm labels and issue forms align with pipeline triage categories
- [ ] Keep auto-label and auto-response workflows focused on intake only
- [ ] Ensure pinned "Latest Release" issue is maintained each release

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
