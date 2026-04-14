# Release Version Sync Checklist

Authoritative version source: [`version.json`](../version.json)

This checklist is the P0-08 release metadata gate.

## Required parity targets

1. `version.json["version"]`
2. `java/build.gradle.kts` subproject `version = "<x.y.z>"`
3. `README.md` version banner (`Version: **vX.Y.Z**`)
4. `docs/ROADMAP.md` metadata line (`Version: vX.Y.Z`)
5. `docs/CHANGELOG.md` latest heading (`## [X.Y.Z]`)

## Validation command

```bash
python tools/check_version_sync.py
```

Validate against a release tag before cutting a release:

```bash
python tools/check_version_sync.py --tag v0.<minor>.<patch>
```

## Policy

- Do not create/push release tags unless this check passes.
- Keep versions below `1.0.0` until alpha release is explicitly authorized.
- Any version bump must update all parity targets in the same commit.
