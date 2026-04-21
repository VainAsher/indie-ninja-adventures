---
doc_type: system_doc
status: living
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Performance Architecture (Java)

## Scope

Primary runtime performance controls for simulation, networking, collision, and rendering.

## Primary Java owners

- Server tick and broadcast cadence:
  - `java/server/src/main/java/com/indieniinja/server/ZoneSimulationLoop.java`
- Delta compression:
  - `java/server/src/main/java/com/indieniinja/server/DeltaEncoder.java`
  - `java/client/src/main/java/com/indieniinja/client/GameStateBuffer.java`
- Collision query scaling:
  - `java/core/src/main/java/com/indieniinja/physics/SpatialHash.java`
- Render culling:
  - `java/client/src/main/java/com/indieniinja/client/rendering/ChunkRenderer.java`

## Key controls

- Fixed server tick: 60 Hz (`TICK_NS`).
- Snapshot broadcast: 20 Hz (`BROADCAST_EVERY`).
- Forced full snapshot interval: ~3s (`FULL_SNAPSHOT_EVERY`).
- Delta encode changed/removed enemy/pickup/platform sets.
- Client merges deltas into canonical full render state.
- Spatial hash chunking limits collision candidate scans.
- Chunk rendering culls off-camera tiles.

## Method-level call graphs

- Tick/broadcast cadence graph:
  - `ZoneSimulationLoop.run()` -> `simulateTick()` each `TICK_NS` -> every `BROADCAST_EVERY` ticks call `broadcastWorldState(fullSnapshot)`
  - Full snapshot cycle: `zone.fullSnapCountdown >= FULL_SNAPSHOT_EVERY` -> `zone.deltaEncoder.reset()`
- Delta encoding graph:
  - `ZoneSimulationLoop.buildSnapshot(full=false, ...)` -> `zone.deltaEncoder.enemiesChanged/enemiesRemoved/pickupsChanged/pickupsRemoved/platformsChanged/platformsRemoved`
  - `GameStateBuffer.update(snap)` -> `applyDelta(snap)` -> mutate `enemyById/pickupById/platformById` maps
- Snapshot cache graph:
  - Full broadcast path -> `session.zoneStateCache.put(zone.hubId, payload)` -> `ZoneStateCache.encodeMap(...)` -> Redis `SETEX`
  - Reconnect path -> `ServerProtocolHandler` late-join -> `session.zoneStateCache.get(hubId)` -> cached `WORLD_STATE` send
- Collision/render scale graph:
  - Physics path -> `CollisionSystem.resolveHorizontal/resolveVertical` -> `SpatialHash.candidates(...)`
  - Render path -> `GameScreen.render(...)` -> `ChunkRenderer.render(batch, camera)` (camera-window culling)

## Caching layers

- Server room tile cache: `RoomTileCache` (Redis optional).
- Server zone snapshot cache: `ZoneStateCache` (Redis optional).
- Server item cache: `ItemCache` (Redis optional).
- Client local caches: room/world/enemy/pickup/minimap tile caches in `GameScreen`.

## Current gaps

- Perf budgets are enforced by practice/tests, but there is no single consolidated in-game perf dashboard yet.

## Legacy archive

Python/Pygame version is archived at:
`docs/archive/retired/2026-04-21_v0.11.71_python-systems-docs/PERFORMANCE.md`
