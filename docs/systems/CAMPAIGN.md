---
doc_type: system_doc
status: living
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Campaign System (Java)

## Scope

Campaign progression, mission lifecycle, story act state, and save/restore behavior in the Java client/server stack.

## Primary Java owners

- Client campaign state:
  - `java/client/src/main/java/com/indieniinja/client/game/MissionManager.java`
  - `java/client/src/main/java/com/indieniinja/client/game/StoryManager.java`
  - `java/client/src/main/java/com/indieniinja/client/game/SaveManager.java`
  - `java/client/src/main/java/com/indieniinja/client/game/SaveData.java`
  - `java/client/src/main/java/com/indieniinja/client/game/MissionDefinition.java`
  - `java/client/src/main/java/com/indieniinja/client/game/MissionLocationTriggerRegistry.java`
- Server campaign/hub progression signals:
  - `java/server/src/main/java/com/indieniinja/server/ZoneSimulationLoop.java`
  - `java/shadowascent/src/main/java/com/indieniinja/world/HubStateMachine.java`

## Runtime flow

1. Mission definitions load from `data/missions.json`.
2. `MissionManager` controls active mission state, objective progress, completion, failure, and timing.
3. `GameScreen` feeds mission objective events (kills, switches, location contact, pickups).
4. `StoryManager` tracks act/hub-state progression and narrative flags.
5. `SaveManager` persists and restores campaign/story/mission state in slot-based saves.
6. Server loop emits hub/scripted-loss style events that feed client narrative transitions.

## Method-level call graphs

- Mission progression graph:
  - `GameScreen.startMissionFlow(...)` -> `MissionManager.startMission(missionId)`
  - `GameScreen` objective events -> `MissionManager.onEnemyKilled/onBossDefeated/onItemCollected/onSwitchActivated/onReachLocation` -> `MissionManager.progressObjective(...)` -> `MissionManager.checkAllObjectivesMet(...)` -> `MissionManager.completeMission()` (or `MissionManager.failMission()`)
  - `GameScreen.render(delta)` -> `MissionManager.tick(delta)` -> `MissionManager.failMission()` (timeout path)
- Story sync graph:
  - `ZoneSimulationLoop.buildSnapshot(...)` -> `snap.hubState = hubStateMachine.getState().name()`
  - `GameStateBuffer.update(snap)` -> `GameScreen.render(...)` -> `StoryManager.onHubStateUpdate(snap.hubState)` -> `StoryManager.syncActFromHubState()` -> `StoryManager.setAct(...)`
- Save/load graph:
  - Load: `GameScreen` startup -> `SaveManager.load()` -> `SaveManager.applyLoadedData(...)` -> `SaveData.restore(story, missions)` -> `StoryManager.restoreSnapshot(...)` + `MissionManager.restore*`
  - Save: `GameScreen` exit/forced-save path -> `SaveManager.save()` -> `SaveManager.buildSaveSnapshotForWrite()` -> `SaveData.capture(story, missions)` -> `SaveManager.rotateBackup(...)`
- Location trigger graph:
  - `GameScreen` startup -> `MissionLocationTriggerRegistry.load(file)` -> `MissionLocationTriggerRegistry.findMissingReachObjectives(missionManager)`
  - Active reach objective resolution -> `MissionLocationTriggerRegistry.get(activeMissionId, locationId)`

## Contracts

- Objective type parsing uses `ObjectiveType` wire strings.
- Mission availability is act-gated.
- Save format includes checksum sidecar and backup rotation.

## Current gaps

- Some narrative arcs are still event-driven scaffolding rather than finalized authored sequences.
- Endgame/cinematic sequencing remains minimal and is handled by gameplay-state transitions.

## Legacy archive

Python/Pygame version is archived at:
`docs/archive/retired/2026-04-21_v0.11.71_python-systems-docs/CAMPAIGN.md`
