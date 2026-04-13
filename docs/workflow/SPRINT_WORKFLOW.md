# Sprint Workflow

Iteration-first workflow for solo development.

Primary references:

- [ITERATION_RELEASE_PROTOCOL.md](ITERATION_RELEASE_PROTOCOL.md)
- [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)

## Weekly Shape

```text
Mon: triage + plan
Tue-Thu: build/test/release iterations
Fri: hardening + docs + retro
```

## Core Rule

Every completed iteration must end in a testable tagged release.

## Iteration Loop

1. Pick one scoped task (feature, fix, balancing, tooling).
2. Implement in a focused change set.
3. Run local gates:
   - Python tests where relevant.
   - Java test + fat JAR build.
4. Update version metadata and changelog/docs.
5. Commit.
6. Tag in `v0.<minor>.<patch>` format (annotated).
7. Push `master` and tag.
8. Confirm CI + Release workflows and downloadable artifacts.
9. Publish a short iteration report for playtesting.

## Branch Guidance

- Default path: work directly from `master` for fast iteration.
- Use `feature/*` when the task is risky or large.
- Merge to `master` before tagging.
- Use `hotfix/*` for emergency production fixes.

## Definition of Done (Per Iteration)

- [ ] Code change complete for scoped goal
- [ ] Local tests/builds green
- [ ] Tagged release created in `v0.<minor>.<patch>`
- [ ] GitHub Actions passed
- [ ] Release artifacts are present and testable
- [ ] Player-facing test notes written

## Capacity Guidance

Keep each iteration small enough to build, test, and release in the same work block.

