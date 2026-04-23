# P0 Regression Report

Generated: `2026-04-23 21:30:51 +0100`
Overall: **PASS**

## Summary

| Check | Status | Duration (s) |
|-------|--------|--------------|
| `Version Sync` | `PASS` | `0.20` |
| `Data Integrity` | `SKIP` | `0.00` |
| `Java Server/Client Tests` | `PASS` | `52.34` |

## Details

### Version Sync

- Command: `C:\Users\asher\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe tools/check_version_sync.py`
- Working directory: `C:\Users\asher\OneDrive\Documents\GitHub\indie-ninja-adventures`
- Status: `PASS`
- Duration: `0.20s`

```text
Version synchronization OK: v0.12.05
```

### Data Integrity

- Command: `C:\Users\asher\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe tests/test_data_integrity.py`
- Working directory: `C:\Users\asher\OneDrive\Documents\GitHub\indie-ninja-adventures`
- Status: `SKIP`
- Duration: `0.00s`

```text
Skipped: required path not found: C:\Users\asher\OneDrive\Documents\GitHub\indie-ninja-adventures\tests\test_data_integrity.py
```

### Java Server/Client Tests

- Command: `C:\Users\asher\OneDrive\Documents\GitHub\indie-ninja-adventures\java\gradlew.bat :server:test :client:test --console=plain --no-daemon`
- Working directory: `C:\Users\asher\OneDrive\Documents\GitHub\indie-ninja-adventures\java`
- Status: `PASS`
- Duration: `52.34s`

```text
ZoneSimulationLoopScriptedLossOrderingTest > missionPickupSeededForPlayerCannotBeConsumedByOtherPlayer() PASSED
ZoneSimulationLoopScriptedLossOrderingTest > missionScopedPickupSeedAndCollectionForceNextFullSnapshot() PASSED
ZoneSimulationLoopScriptedLossOrderingTest > missionPickupSeedRequestSpawnsPersistentQuestPickups() PASSED
ZoneSimulationLoopScriptedLossOrderingTest > scriptedLossBroadcastsToAllZoneMembersAndDrainsSnapshotYinYang() PASSED
ZoneSimulationLoopScriptedLossOrderingTest > immediateBossDefeatQueueAdvancesHubStateInSameTick() PASSED
ZoneSimulationLoopScriptedLossOrderingTest > scriptedLossBroadcastIsOneShotAcrossTicks() PASSED
ZoneSimulationLoopScriptedLossOrderingTest > duplicateMissionPickupSeedRequestIdIsIgnored() PASSED
> Task :client:compileJava UP-TO-DATE
> Task :client:processResources UP-TO-DATE
> Task :client:classes UP-TO-DATE
> Task :client:compileTestJava UP-TO-DATE
> Task :client:processTestResources NO-SOURCE
> Task :client:testClasses UP-TO-DATE
> Task :client:test UP-TO-DATE
Deprecated Gradle features were used in this build, making it incompatible with Gradle 9.0.
You can use '--warning-mode all' to show the individual deprecation warnings and determine if they come from your own scripts or plugins.
For more on this, please refer to https://docs.gradle.org/8.7/userguide/command_line_interface.html#sec:command_line_warnings in the Gradle documentation.
BUILD SUCCESSFUL in 51s
12 actionable tasks: 1 executed, 11 up-to-date
C:\Users\asher\OneDrive\Documents\GitHub\indie-ninja-adventures\java>endlocal
```
