# P0 Regression Report

Generated: `2026-04-23 19:20:16 +0100`
Overall: **FAIL**

## Summary

| Check | Status | Duration (s) |
|-------|--------|--------------|
| `Version Sync` | `PASS` | `0.11` |
| `Data Integrity` | `FAIL` | `0.08` |
| `Java Server/Client Tests` | `PASS` | `93.02` |

## Details

### Version Sync

- Command: `C:\Users\asher\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe tools/check_version_sync.py`
- Working directory: `C:\Users\asher\OneDrive\Documents\GitHub\indie-ninja-adventures`
- Status: `PASS`
- Duration: `0.11s`

```text
Version synchronization OK: v0.12.05
```

### Data Integrity

- Command: `C:\Users\asher\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe tests/test_data_integrity.py`
- Working directory: `C:\Users\asher\OneDrive\Documents\GitHub\indie-ninja-adventures`
- Status: `FAIL`
- Duration: `0.08s`

```text
C:\Users\asher\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe: can't open file 'C:\\Users\\asher\\OneDrive\\Documents\\GitHub\\indie-ninja-adventures\\tests\\test_data_integrity.py': [Errno 2] No such file or directory
```

### Java Server/Client Tests

- Command: `C:\Users\asher\OneDrive\Documents\GitHub\indie-ninja-adventures\java\gradlew.bat :server:test :client:test --console=plain --no-daemon`
- Working directory: `C:\Users\asher\OneDrive\Documents\GitHub\indie-ninja-adventures\java`
- Status: `PASS`
- Duration: `93.02s`

```text
SaveManagerMigrationTest > clampStoryActOrdinalSupportsAllSevenActs() PASSED
SaveManagerRoundtripTest > buildWriteSnapshotOverlaysCurrentManagerStateOverLiveData() PASSED
SaveManagerRoundtripTest > loadThenBuildWriteSnapshotPreservesLiveDataAndManagerState() PASSED
StoryManagerScriptedLossTest > restoreSnapshotRehydratesSavedHubState() PASSED
StoryManagerScriptedLossTest > scriptedLossCollapsesHubAndForcesActThreeMinimum() PASSED
ScriptedLossMessageFlowTest > gameStateBufferScriptedLossFlagIsSingleUse() PASSED
ScriptedLossMessageFlowTest > networkMessageHandlerMarksScriptedLossInBuffer() PASSED
ClientConstructorGuardTest > overlayConstructorsAreHeadlessSafe() PASSED
ClientConstructorGuardTest > screenConstructorsAreHeadlessSafe() PASSED
ItemLabelFormatterTest > inventoryAbbreviationMatchesLegacyFormatting() PASSED
ItemLabelFormatterTest > inventorySellLineMatchesLegacyFormatting() PASSED
ItemLabelFormatterTest > shopAbbreviationMatchesLegacyFormatting() PASSED
ItemLabelFormatterTest > shopBuyLineMatchesLegacyFormatting() PASSED
ItemLabelFormatterTest > sellPriceMatchesLegacyTable() PASSED
Deprecated Gradle features were used in this build, making it incompatible with Gradle 9.0.
You can use '--warning-mode all' to show the individual deprecation warnings and determine if they come from your own scripts or plugins.
For more on this, please refer to https://docs.gradle.org/8.7/userguide/command_line_interface.html#sec:command_line_warnings in the Gradle documentation.
BUILD SUCCESSFUL in 1m 32s
12 actionable tasks: 4 executed, 8 up-to-date
C:\Users\asher\OneDrive\Documents\GitHub\indie-ninja-adventures\java>endlocal
```
