---
doc_type: system_doc
status: living
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Mechanics and Simulation (Java)

## Scope

Player/enemy/boss mechanics and physics execution in the authoritative Java simulation pipeline.

## Primary Java owners

- `java/shadowascent/src/main/java/com/indieniinja/sim/GameSimulator.java`
- `java/shadowascent/src/main/java/com/indieniinja/sim/SimPlayer.java`
- `java/shadowascent/src/main/java/com/indieniinja/sim/SimEnemy.java`
- `java/shadowascent/src/main/java/com/indieniinja/sim/SimBoss.java`
- `java/core/src/main/java/com/indieniinja/physics/PhysicsSystem.java`
- `java/core/src/main/java/com/indieniinja/physics/CollisionSystem.java`
- `java/core/src/main/java/com/indieniinja/physics/PhysicsConstants.java`
- `java/core/src/main/java/com/indieniinja/network/InputCommand.java`

## Runtime flow

1. Client input is packed into `InputCommand`.
2. Server loop (or solo mode) applies commands each tick in `GameSimulator`.
3. Physics/collision update movement/contact flags.
4. Mechanics state updates (jump/dash/crouch/block/stance/teleport/ninjutsu/yin-yang).
5. Combat, pickups, AI, and world interactions are resolved.
6. Snapshot output is serialized for render/network consumers.

## Method-level call graphs

- Tick entry graph:
  - Server: `ServerProtocolHandler.handleInput(...)` -> `PlayerRecord.latestInput.set(InputCommand.fromMap(...))`
  - Server loop: `ZoneSimulationLoop.simulateTick()` -> collect `Map<Integer, InputCommand>` -> `GameSimulator.step(inputs)`
  - Solo: `InputPoller.poll()` -> `GameSimulator.step(Map.of(slot, cmd))`
- Core step pipeline graph:
  - `GameSimulator.step(...)` -> `applyPlayerInput(...)` -> `rebuildDynamicTiles()` -> `stepEnemies()` -> `clock.stepOne()`
  - `GameClock.stepOne()` -> `EventBus.emit(new TickEvent(...))` -> `PhysicsSystem.onTick(...)` -> `CollisionSystem.onTick(...)`
  - `GameSimulator.step(...)` continues -> `stepPlatforms()` -> `stepCombat()` -> `spawnPendingShurikens()` -> `stepShurikens()` -> `stepPickups()` -> `stepPickupRespawns()` -> `stepNpcs()` -> `stepEchoes()` -> `stepBosses()` -> `tickYinYang()` -> `tickLantern()` -> `stepPlayerRespawns()`
- Physics/collision graph:
  - `PhysicsSystem.onTick(...)` -> `applyGravity(...)` -> velocity integration (`p.x += p.vx`, `p.y += p.vy`)
  - `CollisionSystem.onTick(...)` -> `resolveEntity(...)` -> `resolveHorizontal(...)` + `resolveVertical(...)` -> `SpatialHash.candidates(...)`
- Snapshot graph:
  - `ZoneSimulationLoop.buildSnapshot(...)` -> `GameSimulator.getSnapshot(frame)` -> `WorldSnapshot`

## Design notes

- Java implementation is centralized in `GameSimulator` rather than split into many per-mechanic classes from the old Python layout.
- `PhysicsState.abilityFlags` and tile semantics gate movement-medium behavior.

## Current gaps

- Some advanced boss patterns and late-game tuning remain iterative.

## Legacy archive

Python/Pygame version is archived at:
`docs/archive/retired/2026-04-21_v0.11.71_python-systems-docs/MECHANICS.md`
