---
doc_type: workflow
status: active
owner: core-team
last_updated: 2026-04-20
---
# OneDrive Build Recovery Workflow

## When to use

You see a Gradle build failure containing any of:

```
Execution failed for task ':core:compileJava'.
> java.io.IOException: Unable to delete directory
  'java\core\build\classes\java\main'
```

or

```
Execution failed for task ':client:copyJarToRoot'.
> Cannot access a file in the destination directory.
  > Failed to create MD5 hash for file content.
```

## Root cause

OneDrive syncs `java/*/build/` in real-time, holding file handles that block:
- Gradle's output-directory cleanup before recompilation
- Gradle's incremental MD5 hashing for `Copy` tasks whose destination is under OneDrive

## Permanent fix (already applied)

`java/build.gradle.kts` detects `/OneDrive/` in the repo canonical path and redirects all subproject `build/` dirs to `%LOCALAPPDATA%\indie-ninja-builds\<module>` — outside OneDrive's sync boundary. CI paths (`D:\a\...`) are unaffected.

The redirect covers NEW builds. If **old** `java/*/build/classes` dirs exist (pre-redirect), Gradle still tries to clean them and will lock. The manual step below clears those once.

## Recovery steps

### From bash (git bash / WSL / Claude sessions)

```bash
bash tools/build-local.sh
```

Or manually:

```bash
rm -rf java/core/build/classes java/core/build/resources \
       java/shadowascent/build/classes java/shadowascent/build/resources \
       java/server/build/classes java/server/build/resources \
       java/client/build/classes java/client/build/resources

cd java && ./gradlew.bat :client:shadowJar --no-daemon
```

After the build, copy the JAR manually if `copyJarToRoot` fails:

```bash
cp "$LOCALAPPDATA/indie-ninja-builds/client/libs/ninja-client-all.jar" ninja-client-all.jar
```

### From Windows cmd

```bat
tools\build-local.bat
```

## Why copyJarToRoot fails separately

`copyJarToRoot` copies the fat JAR into the repo root (which is on OneDrive). Gradle's incremental build tracker computes MD5 hashes of ALL files in the destination directory — if OneDrive locks any file there, the MD5 step fails even though the JAR copy itself would succeed.

**Fix already applied**: `doNotTrackState()` added to `copyJarToRoot` in `java/client/build.gradle.kts`. This disables incremental tracking for that task (always runs on `shadowJar` completion) but avoids the lock failure.

## Distribution reminder

After a local build that bypasses the launcher's download mechanism, copy the JAR to any local test installs:

```bash
cp ninja-client-all.jar "C:/Users/asher/OneDrive/Desktop/game/Fresh Test/ninja-client-all.jar"
```

## Escalation

If `build-local.sh` fails twice in a row on the same module:
1. Check `git status` — confirm no OneDrive conflict markers (`.conflict` files, duplicate entries)
2. Run with `--info` flag to identify exactly which file Gradle is locking
3. If the file is inside `%LOCALAPPDATA%\indie-ninja-builds\`, OneDrive has somehow started syncing that path — exclude it in OneDrive settings (Settings → Account → Choose folders)
