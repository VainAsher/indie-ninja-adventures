# Stage 1: Intake

Convert raw feedback into clean, actionable issues.

**When:** Monday morning, after the weekly sync workflow runs.

---

## Steps

### 1. Check the Sync Summary

Open the game repo's intake tracking issue. A comment from `sync_feedback.yml` lists:
- New issues from this week
- Total open count
- Issues grouped by label

### 2. Review Each New Issue

For each issue in the summary:

**Is it a duplicate?**
- Search feedback repo: `is:issue label:bug "collision"` etc.
- If duplicate: comment "Duplicate of #X", add `duplicate` label, close.

**Is it unclear?**
- Comment asking for repro steps, version, system specs
- Add `needs-info` label
- Do not triage until info arrives

**Is it actionable?**
- Can it be reproduced or reasonably verified?
- Does it fall within scope (not a platform issue, not by design)?
- If yes → create a dev task here (next step)

**Is it a known issue?**
- Already in `docs/operations/BUG_BACKLOG.md` in game repo?
- Comment "Known issue — tracked in vX.X.X backlog", link, close.

### 3. Create Dev Tasks

For each actionable issue, create a new issue in **this repo** using the `bug_intake` or `dev_task` template.

Link back to the original: `Source: VainAsher/indie-ninja-feedback#123`

Group related reports into a single task if they share a root cause.

### 4. Update Triage Labels

In the feedback repo, remove `needs-triage` and add appropriate label:
- `fixed` — already addressed in upcoming build
- `needs-info` — waiting on reporter
- Leave open if triaged into pipeline

---

## Output

Clean, linked issues in this repo ready for triage prioritisation.
