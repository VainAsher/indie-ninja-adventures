---
doc_type: workflow
status: living
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Operating Rhythm and Habits

Practical operating guide for daily, weekly, and monthly execution across game, launcher, feedback, and pipeline repos.

## What This Guide Optimizes

- Consistent delivery speed without repo drift
- Traceable decisions and release evidence
- Clear player-facing communication

## Daily Rhythm

### 1) Start-of-day (15-20 min)

1. Check pipeline board (`Backlog`, `This Sprint`, `Blocked`).
2. Confirm no new P0/P1 feedback escalations.
3. Pick one active task and state expected done condition.

Habit: one focused objective per session before opening new scope.

### 2) Build loop (core execution)

1. Implement one logical change.
2. Run local gates:
   - `python tools/check_version_sync.py`
   - `python tools/check_docs_freshness.py --emit-report`
   - `cd java && ./gradlew :server:test :client:test --no-daemon`
3. Commit with clear scope and reason.
4. Update linked pipeline issue with progress/evidence.

Habit: never hold uncommitted multi-feature state overnight.

### 3) End-of-day close (10-15 min)

1. Update task status (`In Progress`, `Blocked`, or `Done`).
2. Add short evidence note (commands run, observed result).
3. Record cross-repo dependencies discovered today.

Habit: leave a restart point that future-you can execute in under 5 minutes.

## Weekly Rhythm (Control Tower Week)

### Monday - Intake, triage, planning

1. Run or confirm `feedback_intake_sync.yml` summary.
2. Triage new intake into severity/type/system.
3. Build sprint scope (1-3 tasks, realistic solo capacity).
4. Freeze sprint scope unless P0 arrives.

### Tuesday to Thursday - Execution and validation

1. Drive sprint tasks to done using execution loop.
2. Keep PRs small and merge when green.
3. Push status back to feedback issue links where applicable.

### Friday - Hardening and reporting

1. Re-check blockers and carry-over decisions.
2. Run release-readiness scan for active branch.
3. Update dashboard metrics and weekly report notes.
4. Confirm documentation and decision records are current.

Habit: Friday is closure and audit day, not net-new feature day.

## Monthly Rhythm (Release + Audit)

### Release coordination

1. Confirm sprint goals and release scope are complete.
2. Run full release gates in game repo:
   - `cd java && ./gradlew :server:test :client:test :server:shadowJar :client:shadowJar --no-daemon`
3. Tag release, verify assets, verify launcher dispatch path.
4. Publish player-facing notes (launcher docs/changelog and feedback pin).

### Audit pass

1. Verify each shipped item has links:
   - feedback source issue
   - pipeline planning issue
   - implementation PR/commit
   - release note mention (if user-facing)
2. Archive retired plans/docs to avoid stale references.
3. Log what slipped and why into next month planning.

Habit: if work cannot be traced end-to-end, treat it as incomplete.

## Knowledge Sharing Habits

### Session-level sharing

- Write one sentence: what changed, why, and risk left.
- Link exact file or issue references.
- Keep handover notes in pipeline or docs, not chat-only history.

### Decision sharing

- For non-trivial decisions, create/update a decision record.
- Include alternatives considered and rejection reason.
- Link to operational impact (build, release, or player experience).

### Documentation hygiene

- Update docs in same PR as behavior change whenever possible.
- Move stale docs to archive immediately.
- Keep index pages current so onboarding cost stays low.

## Auditing Impact

Following this rhythm improves auditability by making every release answer:

1. What changed?
2. Why was it prioritized?
3. How was it validated?
4. Where was it communicated to players?

When this loop is followed, audit prep becomes normal operations, not emergency reconstruction.

## End-User Release Impact

These habits directly improve player outcomes:

- Faster fixes: triage and ownership are explicit
- Fewer regressions: gates are run consistently
- Better trust: release notes and issue closures match shipped behavior
- Better support: feedback reports map to tracked internal work

## Minimum Non-Negotiables

1. Pipeline owns planning and cross-repo coordination.
2. Source repos own implementation and release artifact production.
3. Feedback repo stays intake-only.
4. Every shipped fix has source-to-release traceability.
