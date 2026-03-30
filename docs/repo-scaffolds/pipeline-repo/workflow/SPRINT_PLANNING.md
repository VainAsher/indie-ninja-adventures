# Stage 3: Sprint Planning

Turn the prioritised backlog into a concrete weekly sprint.

**When:** Monday, after Triage.

---

## Sprint Setup

1. Review last sprint's Done column — move any unfinished items back to Backlog
2. Pick 1–3 tasks from the top of the Backlog for This Sprint
3. Solo capacity: aim for ~15 hours of estimated work max
4. Drag selected tasks into "This Sprint" column

---

## Task Template

Every sprint task must have these filled in before moving to In Progress:

```markdown
**Goal:** One sentence — what is true when this is done

**Why it matters:** What breaks or is missing without this

**Approach:**
- File: `path/to/file.py`
- Function: `function_name()`
- Design decision: ...

**Risks:**
- Potential regression in X
- Dependency on Y

**Acceptance Criteria:**
- [ ] Specific, verifiable condition
- [ ] All tests pass (`python run_tests.py`)
- [ ] Relevant docs updated
- [ ] (If network touched) 2-player smoke test passes
- [ ] (If physics/input changed) Replay validation passes
```

A task without acceptance criteria cannot be marked Done.

---

## Sprint Goal

Write a one-sentence sprint goal at the top of the DASHBOARD.md:

> "This sprint: implement Forest boss phase 1 AI and fix the multiplayer coin desync."

This keeps focus when new issues arrive mid-week.

---

## Commit to the Sprint

Once tasks are in "This Sprint":
- Do not add more tasks mid-week unless a P0 arrives
- If a new P0 appears: swap it in, move lowest-priority current task back to Backlog
- If you finish early: pull the next Backlog item in, don't idle

---

## Capacity Guide

| Estimate | Work |
|----------|------|
| Small (2–4 hrs) | Single bug fix, doc update, small feature |
| Medium (4–8 hrs) | New system integration, multi-file change |
| Large (8–15 hrs) | New major feature, architectural change |

Never take on more than one Large task per sprint solo.
