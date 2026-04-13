# Branching Model

Branching is optimized for rapid, testable iteration releases.

Primary reference: [ITERATION_RELEASE_PROTOCOL.md](ITERATION_RELEASE_PROTOCOL.md)

## Branch Structure

```
master       <- integration + release branch (iteration tags are cut here)
feature/*    <- optional short-lived branch for larger/riskier work
hotfix/*     <- urgent production fix branch
```

`develop` is optional legacy flow. It is not required for the current iteration-release process.

## Expected Flow

1. Start from `master`.
2. Use `feature/*` only when the change is risky or long-running.
3. Merge back to `master`.
4. Run local build/test gates.
5. Tag and release from `master`.

## Commit Message Format

Use Conventional Commit style:

```text
<type>: <short summary>

[optional body]
```

Supported types:

- `feat`
- `fix`
- `docs`
- `test`
- `chore`
- `refactor`
- `perf`

## Tagging Rules

1. Do not use `v1.0.0` (or any `v1.x.x`) until the owner explicitly declares alpha readiness.
2. Use `v0.<minor>.<patch>` during development.
3. Tag the final commit of the iteration.
4. Prefer annotated tags:
   - `git tag -a v0.11.22 -m "v0.11.22 - <summary>"`

## Minimal Day-to-Day Commands

```bash
git checkout master
git pull origin master

# optional
git checkout -b feature/my-task

# work + validate
git add <files>
git commit -m "fix: <summary>"
```

For release commands and verification gates, use [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).
