---
doc_type: system_doc
status: living
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Endings and Narrative Resolution (Java)

## Scope

Act progression and scripted loss/finale transition hooks currently implemented in Java runtime.

## Primary Java owners

- `java/client/src/main/java/com/indieniinja/client/game/StoryManager.java`
- `java/client/src/main/java/com/indieniinja/client/GameScreen.java`
- `java/server/src/main/java/com/indieniinja/server/ZoneSimulationLoop.java`
- `java/core/src/main/java/com/indieniinja/network/WorldSnapshot.java`

## Current implementation

- Narrative progression is modeled as act state (`Act`) plus hub-state transitions.
- Scripted-loss signaling is supported from simulation to client.
- `StoryManager` applies act transitions and narrative flags used by dialogue/conditions.
- End-state transitions are currently gameplay/system driven rather than a dedicated cinematic-ending pipeline.

## Method-level call graphs

- Scripted-loss event graph:
  - `GameSimulator.step(...)` sets scripted-loss flag -> `ZoneSimulationLoop.simulateTick()` -> `sim.drainPendingScriptedLoss()` -> `ZoneSimulationLoop.broadcastEvent(MessageType.SCRIPTED_LOSS, ...)`
- Scripted-loss client graph:
  - `NetworkClientThread` handles `MessageType.SCRIPTED_LOSS` -> `GameStateBuffer.markScriptedLoss()`
  - `GameScreen.render(...)` -> `stateBuffer.pollScriptedLoss()` -> scripted-loss overlay
  - `GameScreen.handleScriptedLossOverlayInput()` -> `StoryManager.onVeilMaidenDefeatedAct1()`
- Hub-state narrative graph:
  - `ZoneSimulationLoop.buildSnapshot(...)` -> `snap.hubState = hubStateMachine.getState().name()` -> `WorldSnapshot.toMap()`
  - `GameStateBuffer.update(...)` -> `GameScreen.render(...)` -> `StoryManager.onHubStateUpdate(...)` -> `StoryManager.syncActFromHubState()` -> `StoryManager.setAct(...)`

## Contracts

- Hub-state wire values are authoritative for act progression synchronization.
- Scripted-loss handling is one-shot polled on client buffer/overlay path.

## Current gaps

- No dedicated Java "ending manager" equivalent to legacy prototype architecture.
- Final ending/cutscene orchestration remains a future authored pipeline task.

## Legacy archive

Python/Pygame version is archived at:
`docs/archive/retired/2026-04-21_v0.11.71_python-systems-docs/ENDINGS.md`
