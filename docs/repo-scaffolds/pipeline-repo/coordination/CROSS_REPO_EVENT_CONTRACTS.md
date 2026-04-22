# Cross-Repo Event Contracts

Canonical event and automation contracts for repo-to-repo coordination.

Last reviewed: 2026-04-21

---

## Contract 1: Game Release Dispatch

**Producer:** `indie-ninja-adventures` release workflow

**Consumer:** `indie-ninja-launcher` `repository_dispatch` workflow

**Event type:** `game-release`

**Payload fields:**

- `version` (string, example `v0.11.72`)
- `release_url` (string, URL to tagged release)

**Producer workflow reference:** `.github/workflows/release.yml`

**Consumer workflow reference:** `.github/workflows/receive_game_release.yml`

**Secret required:** `CROSS_REPO_PAT` in producer repo (write access to launcher repo dispatch)

**Failure handling:**

- Dispatch step should be `continue-on-error: true`
- Failure must create/append a pipeline issue for manual follow-up

---

## Contract 2: Feedback Intake Sync

**Producer:** `indie-ninja-feedback` issues (data source)

**Consumer:** `indie-ninja-pipeline` intake workflow

**Mechanism:** scheduled pull + summary comment on pipeline intake issue

**Workflow reference:** `.github/workflows/feedback_intake_sync.yml`

**Required env vars:**

- `FEEDBACK_REPO` (default `VainAsher/indie-ninja-feedback`)
- `INTAKE_ISSUE_NUMBER` (pipeline issue number)

**Secret required:** `CROSS_REPO_PAT` in pipeline repo (read feedback repo, write pipeline issue comment)

**Failure handling:**

- Workflow failure should be visible in Actions with notification enabled
- Intake owner runs manual `workflow_dispatch` retry before triage starts

---

## Contract 3: Feedback Resolution Loop (Process Contract)

This is a procedural contract (not yet an automated dispatch).

When a pipeline/source task is shipped:

1. Add resolution comment to linked feedback issue
2. Include version number and release link
3. Apply `fixed` label when live

This keeps player-facing transparency aligned with release reality.

---

## Change Control

Any event payload change requires:

1. Update this contract file
2. Update producer workflow
3. Update consumer workflow
4. Run one manual end-to-end dry run
5. Record result in pipeline coordination issue
