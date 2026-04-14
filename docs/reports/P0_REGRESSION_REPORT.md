# P0 Regression Report

Generated: `2026-04-14 19:00:51 +0100`
Overall: **PASS**

## Summary

| Check | Status | Duration (s) |
|-------|--------|--------------|
| `Version Sync` | `PASS` | `0.07` |
| `Data Integrity` | `PASS` | `0.23` |
| `Java Server/Client Tests` | `PASS` | `27.16` |

## Details

### Version Sync

- Command: `C:\Users\asher\OneDrive\Documents\GitHub\indie-ninja-adventures\.venv\Scripts\python.exe tools/check_version_sync.py`
- Working directory: `C:\Users\asher\OneDrive\Documents\GitHub\indie-ninja-adventures`
- Status: `PASS`
- Duration: `0.07s`

```text
Version synchronization OK: v0.11.35
```

### Data Integrity

- Command: `C:\Users\asher\OneDrive\Documents\GitHub\indie-ninja-adventures\.venv\Scripts\python.exe tests/test_data_integrity.py`
- Working directory: `C:\Users\asher\OneDrive\Documents\GitHub\indie-ninja-adventures`
- Status: `PASS`
- Duration: `0.23s`

```text
pygame 2.6.1 (SDL 2.28.4, Python 3.12.0)
Hello from the pygame community. https://www.pygame.org/contribute.html
test_dialogue_events_requiring_arguments_include_argument (__main__.TestDataIntegrity.test_dialogue_events_requiring_arguments_include_argument) ... ok
test_dialogue_events_supported_by_runtime_router (__main__.TestDataIntegrity.test_dialogue_events_supported_by_runtime_router) ... ok
test_legacy_mission_system_ids_match (__main__.TestDataIntegrity.test_legacy_mission_system_ids_match) ... ok
test_mission_boss_ids_exist (__main__.TestDataIntegrity.test_mission_boss_ids_exist) ... ok
test_mission_boss_ids_runtime_compatible (__main__.TestDataIntegrity.test_mission_boss_ids_runtime_compatible) ... ok
test_mission_enemy_types_exist (__main__.TestDataIntegrity.test_mission_enemy_types_exist) ... ok
test_mission_hazards_exist (__main__.TestDataIntegrity.test_mission_hazards_exist) ... ok
test_mission_objective_items_exist (__main__.TestDataIntegrity.test_mission_objective_items_exist) ... ok
test_mission_reward_items_exist (__main__.TestDataIntegrity.test_mission_reward_items_exist) ... ok
test_shop_pool_items_exist (__main__.TestDataIntegrity.test_shop_pool_items_exist) ... ok
----------------------------------------------------------------------
Ran 10 tests in 0.002s
OK
```

### Java Server/Client Tests

- Command: `C:\Users\asher\OneDrive\Documents\GitHub\indie-ninja-adventures\java\gradlew.bat :server:test :client:test --console=plain --no-daemon`
- Working directory: `C:\Users\asher\OneDrive\Documents\GitHub\indie-ninja-adventures\java`
- Status: `PASS`
- Duration: `27.16s`

```text
> Task :core:processResources NO-SOURCE
> Task :core:classes UP-TO-DATE
> Task :core:jar
> Task :server:compileJava UP-TO-DATE
> Task :server:processResources UP-TO-DATE
> Task :server:classes UP-TO-DATE
> Task :server:compileTestJava UP-TO-DATE
> Task :server:processTestResources NO-SOURCE
> Task :server:testClasses UP-TO-DATE
> Task :server:test UP-TO-DATE
> Task :client:compileJava UP-TO-DATE
> Task :client:processResources UP-TO-DATE
> Task :client:classes UP-TO-DATE
> Task :client:compileTestJava UP-TO-DATE
> Task :client:processTestResources NO-SOURCE
> Task :client:testClasses UP-TO-DATE
> Task :client:test UP-TO-DATE
BUILD SUCCESSFUL in 26s
10 actionable tasks: 1 executed, 9 up-to-date
C:\Users\asher\OneDrive\Documents\GitHub\indie-ninja-adventures\java>endlocal
```
