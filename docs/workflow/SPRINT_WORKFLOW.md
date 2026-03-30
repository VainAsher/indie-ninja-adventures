# Sprint Workflow

Weekly development rhythm for solo indie development.

---

## Weekly Structure

```
Monday     — Intake + triage  (1–2 hrs)
Tue–Thu    — Execution loop   (core dev time)
Friday     — Verification + docs + retro  (1–2 hrs)
```

---

## Monday: Intake + Triage

1. Run (or check) the weekly feedback sync: [sync_feedback.yml](../../.github/workflows/sync_feedback.yml)
2. Review the intake summary comment on the intake tracking issue
3. For each new feedback issue:
   - Is it a duplicate? → close + link original
   - Is it actionable? → create a dev task in the pipeline repo using the `bug_intake` or `dev_task` template
   - Is it unclear? → comment asking for more info, label `needs-info`
4. Review current sprint board — are any tasks blocked or stale?
5. Set sprint goal: pick 1–3 tasks to complete this week

**Output:** Cleaned backlog, sprint tasks in "This Sprint" column

---

## Task Template

Every task created for a sprint must fill in:

```
Goal:          One sentence — what is true when done
Why it matters: What breaks or is missing without this
Approach:      File paths, function names, design decisions
Risks:         Regressions, unknowns, dependencies
Acceptance Criteria:
  - [ ] Specific, verifiable condition
  - [ ] All tests pass (python run_tests.py)
  - [ ] Relevant docs updated
```

A task without acceptance criteria cannot be marked Done.

---

## Tue–Thu: Execution Loop

For each sprint task:

```
1. Create branch:  git checkout -b feature/<task-name> develop
2. Implement
3. Test locally:   python run_tests.py
4. Verify acceptance criteria (check them off)
5. Commit:         git commit -m "feat|fix: description"
6. Push + PR → develop
7. CI passes → merge
8. Mark task Done on sprint board
```

**If tests fail:** Fix before moving on. Never merge a red branch.

**If blocked:** Move task to "Blocked" column, note the blocker, pick next task.

**Commit discipline:**
- Commit each logical unit of work, not at end of day
- Message format: `type: description` (see [BRANCHING.md](BRANCHING.md))
- If working alone, squash is optional — clear history is enough

---

## Friday: Verification + Docs + Retro

### Verification
- Run full test suite: `python run_tests.py`
- If physics/input changed: run a replay and verify determinism
- If netcode touched: smoke test 2-player local session

### Documentation
For each completed task, check:
- [ ] Code comments are clear where logic is non-obvious
- [ ] `docs/CHANGELOG.md` has an entry (if user-visible)
- [ ] Relevant system doc updated (`docs/dev/SYSTEMS.md`, `docs/dev/ARCHITECTURE.md`)
- [ ] `docs/ROADMAP.md` reflects what's now done

### Retro (2 minutes)
- What went well?
- What slowed me down?
- What carries over to next sprint?

---

## Sprint Board (GitHub Projects)

Column flow:

```
Backlog → This Sprint → In Progress → In Review → Done
```

- **Backlog**: Everything triaged but not yet scheduled
- **This Sprint**: Committed to this week (max 3 tasks)
- **In Progress**: Currently being worked on (max 1 at a time)
- **In Review**: PR open, waiting for CI or self-review
- **Done**: Merged, verified, documented

---

## Priority Guide

When deciding what to put in sprint:

| Priority | Criteria |
|----------|----------|
| P0 — Critical | Crash, data loss, blocks testing, urgent from feedback |
| P1 — High | Breaks a major feature, reported by multiple users |
| P2 — Medium | Noticeable issue, workaround exists |
| P3 — Low | Polish, cosmetic, nice-to-have |

Always clear all P0s before starting P1 work.

---

## Capacity

Solo developer: approximately 15–25 productive hours/week.

Rule of thumb: commit to tasks that total no more than 15 hours of estimated work per sprint. Leave buffer for review, docs, and unexpected issues.
