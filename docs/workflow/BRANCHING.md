# Branching Model

Indie Ninja Adventures uses a simple Git Flow adapted for solo development.

---

## Branch Structure

```
main         ← stable, tagged releases only — never commit directly
develop      ← integration branch — all features merge here first
feature/*    ← new work — branched from develop, PR back to develop
hotfix/*     ← urgent production fixes — branched from main, PR to main
```

### `main`

- Only updated by merging `develop` at release time, or a `hotfix/*` branch
- Every merge to `main` gets a version tag: `v0.8.0`, `v0.8.1`, etc.
- CI runs on push to `main`

### `develop`

- The active working branch
- All features and fixes merge here via PR
- CI runs on every push — if CI fails, do not merge further until fixed
- Periodically merged into `main` as a release

### `feature/<name>`

- One branch per task/feature
- Branch from `develop`: `git checkout -b feature/boss-ai develop`
- Keep focused — one logical change per branch
- PR → `develop` when complete and CI-green
- Delete branch after merge

### `hotfix/<name>`

- For urgent production bugs only (crash, data loss, unplayable)
- Branch from `main`: `git checkout -b hotfix/fix-save-corruption main`
- PR → `main` (triggers release workflow if tagged)
- Back-merge into `develop` immediately after: `git merge hotfix/fix-save-corruption`

---

## Commit Message Format

```
<type>: <short description>

[optional body]
[optional: Closes #123]
```

**Types:**

| Type | When to use |
|------|-------------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `test` | Adding or updating tests |
| `chore` | Build, CI, dependencies, tooling |
| `refactor` | Code change with no behaviour change |
| `perf` | Performance improvement |

**Examples:**

```
feat: add boss phase transitions for Forest zone

fix: resolve replay desync on frame skip after wall jump

docs: add multiplayer architecture section to ARCHITECTURE.md

test: add edge case for wall collision during dash

chore: bump version to 0.8.1 in version.json and pyproject.toml
```

---

## Day-to-Day Workflow

```bash
# Start a new task
git checkout develop
git pull origin develop
git checkout -b feature/my-task

# Work, commit often
git add <files>
git commit -m "feat: implement X"

# Before PR — run tests
python run_tests.py

# Push and open PR → develop
git push -u origin feature/my-task
```

---

## Release Workflow

```bash
# 1. Merge develop → main
git checkout main
git merge develop --no-ff -m "chore: release v0.8.1"

# 2. Tag the release
git tag v0.8.1

# 3. Push (triggers GitHub Actions release build)
git push origin main
git push origin v0.8.1

# 4. Cut new develop from main
git checkout develop
git merge main
git push origin develop
```

See [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) for the full pre/post-release process.

---

## Naming Conventions

| Branch type | Format | Example |
|-------------|--------|---------|
| Feature | `feature/<kebab-case>` | `feature/boss-ai-forest` |
| Hotfix | `hotfix/<kebab-case>` | `hotfix/fix-save-corruption` |
| Tags | `v<major>.<minor>.<patch>` | `v0.8.1` |
