# Contributing

Indie Ninja Adventures is now a Java-first repository. Use this guide for day-to-day contribution standards.

## Branching Model

See [docs/workflow/BRANCHING.md](docs/workflow/BRANCHING.md) for the full process.

Quick reference:

```text
main        <- stable release lane
develop     <- integration lane
feature/*   <- new work
hotfix/*    <- urgent fixes
```

Do not commit directly to `main`.

## Commit Messages

Format: `type: short description`

```text
feat: add portal travel lock reason telemetry
fix: resolve room transition camera snap jitter
docs: update release checklist for jar-first lane
test: add regression for hub migration state restore
chore: bump version metadata to v0.11.72
refactor: extract world-graph edge validation helper
```

Common types: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `perf`.

## Pull Requests

- Open PRs against `develop` unless instructed otherwise.
- Complete the PR template.
- Ensure CI checks pass before merge.

## Local Validation

Run these before opening or merging a PR:

```bash
python tools/check_version_sync.py
python tools/check_docs_freshness.py --emit-report
cd java && gradle :server:test :client:test --no-daemon
```

If your change touches runtime behavior, also smoke the built jars:

```bash
java -jar ninja-server-all.jar
java -jar ninja-client-all.jar
```

## Dev Environment

Primary setup docs:

- [docs/dev/JAVA_SETUP.md](docs/dev/JAVA_SETUP.md)
- [docs/workflow/PRE_COMMIT_LOCAL_GATES.md](docs/workflow/PRE_COMMIT_LOCAL_GATES.md)

Quick start:

```bash
git clone https://github.com/VainAsher/indie-ninja-adventures.git
cd indie-ninja-adventures
cd java && gradle :server:test :client:test --no-daemon
```

## Documentation Updates

When behavior changes, update:

- `docs/CHANGELOG.md`
- `docs/CURRENT_STATE.md` (if runtime state changes)
- `docs/ROADMAP.md` (if milestone scope/status changes)

For release work, keep `version.json` in sync with release tags.

## Prototype Lane Note

The legacy Pygame prototype lane is no longer developed in this repository.

- Prototype repo: `https://github.com/VainAsher/indie-ninja-prototype`
- Migration handover: `docs/operations/PYGAME_MIGRATION_HANDOVER.md`
