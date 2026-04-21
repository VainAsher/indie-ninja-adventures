---
doc_type: system_doc
status: living
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Rendering Pipeline (Java)

## Scope

Client render pipeline for world, entities, HUD, overlays, and map presentation.

## Primary Java owners

- Screen orchestration:
  - `java/client/src/main/java/com/indieniinja/client/GameScreen.java`
- Camera:
  - `java/client/src/main/java/com/indieniinja/client/GameCamera.java`
- World tiles:
  - `java/client/src/main/java/com/indieniinja/client/rendering/ChunkRenderer.java`
  - `java/client/src/main/java/com/indieniinja/client/rendering/BlobTileSet.java`
- Entities and FX:
  - `java/client/src/main/java/com/indieniinja/client/rendering/EntityRenderer.java`
  - `java/client/src/main/java/com/indieniinja/client/rendering/ParticleSystem.java`
  - `java/client/src/main/java/com/indieniinja/client/rendering/AnimationRegistry.java`
- HUD and overlays:
  - `java/client/src/main/java/com/indieniinja/client/rendering/HudRenderer.java`
  - `java/client/src/main/java/com/indieniinja/client/ui/MinimapRenderer.java`
  - `java/client/src/main/java/com/indieniinja/client/ui/*Overlay.java`

## Runtime flow

1. `GameScreen` obtains current snapshot (solo or network).
2. Camera updates to local player context.
3. Tile layer renders via `ChunkRenderer`.
4. Entities and particles render.
5. HUD renders status, toasts, and mode overlays.
6. Optional overlays (dialogue, mission menu, inventory, shop, minimap, pause) render last.

## Method-level call graphs

- Main render pass graph:
  - `GameScreen.render(delta)` -> `WorldSnapshot snap = stateBuffer.poll()`
  - `camera.follow(local.posX, local.posY)` -> `camera.clampToBounds(worldW, worldH)`
  - `chunkRenderer.render(batch, camera)` -> `entityRenderer.render(batch, snap, delta)` -> `particleSystem.render(batch)`
  - `chunkRenderer.renderVignette(...)` -> `hudRenderer.render(snap, connected, fps, localSlot)` -> `hudRenderer.renderToasts(delta)`
- Overlay pass graph:
  - `GameScreen.render(...)` -> `dialogueOverlay.render(...)` -> `missionSelectOverlay.render(...)` -> `minimapRenderer.render(...)` -> `inventoryOverlay.render(...)` -> `shopOverlay.render(...)` -> `pauseScreen.render(delta)` -> `devConsole.render(...)`
- Camera snap graph:
  - Spawn/transition path -> `camera.snapTo(x, y)` (used after spawn/room/runtime resets)

## Contracts

- Render reads merged canonical state from `GameStateBuffer` (not raw deltas).
- Tile visuals depend on world tile IDs and autotile role mapping.

## Legacy archive

Python/Pygame version is archived at:
`docs/archive/retired/2026-04-21_v0.11.71_python-systems-docs/RENDERING.md`
