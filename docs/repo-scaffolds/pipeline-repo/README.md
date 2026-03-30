# Indie Ninja Adventures — Dev Pipeline

Private development management repo. This is the brain of the operation.

---

## The Loop

```
Player → Feedback (indie-ninja-feedback)
       → Triage (this repo)
       → Plan → Build (indie-ninja-adventures)
       → Test → Release
       → Document → Repeat
```

---

## Workflow Stages

| Stage | Doc | Cadence |
|-------|-----|---------|
| 1. Intake | [workflow/INTAKE.md](workflow/INTAKE.md) | Monday |
| 2. Triage | [workflow/TRIAGE.md](workflow/TRIAGE.md) | Monday |
| 3. Sprint Planning | [workflow/SPRINT_PLANNING.md](workflow/SPRINT_PLANNING.md) | Monday |
| 4. Execution | [workflow/EXECUTION_LOOP.md](workflow/EXECUTION_LOOP.md) | Tue–Thu |
| 5. Release | [workflow/RELEASE_CYCLE.md](workflow/RELEASE_CYCLE.md) | Monthly |

---

## Issue Templates

- **Dev Task** — planned feature or improvement (use for sprint tasks)
- **Bug Intake** — triaged bug from feedback repo (linked to original report)

---

## GitHub Project (Kanban)

Column flow:

```
Backlog → This Sprint → In Progress → In Review → Done
```

Create the project at: `github.com/VainAsher?tab=projects → New project → Board`

Link this repo as the project's default repository.

---

## Dashboard

- [dashboard/DASHBOARD.md](dashboard/DASHBOARD.md) — Active sprint, blocked items, build stability
- [dashboard/BACKLOG.md](dashboard/BACKLOG.md) — Prioritised backlog

---

## One-Time Setup Actions

1. Create `VainAsher/indie-ninja-launcher` (public repo) — copy `docs/repo-scaffolds/launcher-repo/`
2. Create `VainAsher/indie-ninja-feedback` (public repo) — copy `docs/repo-scaffolds/feedback-repo/`
3. Create `VainAsher/indie-ninja-pipeline` (private repo — this repo)
4. Create GitHub Project (kanban) and link to pipeline repo
5. Run label setup: `docs/repo-scaffolds/feedback-repo/LABELS.md`
6. Create `CROSS_REPO_PAT` secret in game repo (classic PAT, `repo` scope)
7. Create intake tracking issue in game repo (update `INTAKE_ISSUE_NUMBER` in `sync_feedback.yml`)
8. Create `develop` branch in game repo: `git checkout -b develop main && git push origin develop`
9. Pin a "Latest Release" issue in feedback repo
10. Set up GitHub Pages on launcher repo (`Settings → Pages → main /docs`)
