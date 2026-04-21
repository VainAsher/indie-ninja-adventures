---
doc_type: system_doc
status: living
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Companions System (Java)

## Scope

Yin/Yang companion-orb rendering and balance visualization in the Java client.

## Primary Java owners

- `java/client/src/main/java/com/indieniinja/client/rendering/EntityRenderer.java`
- `java/core/src/main/java/com/indieniinja/network/PlayerState.java`
- `java/shadowascent/src/main/java/com/indieniinja/sim/YinYangComponent.java`

## Runtime flow

1. Server simulation computes yin/yang values and flow balance per player.
2. Values are serialized on `PlayerState` (`yinValue`, `yangValue`, `flowMode`).
3. `EntityRenderer.renderCompanions(...)` draws two orbiting orbs around each player.
4. Orb size/alpha and flow effects derive directly from current player balance values.

## Method-level call graphs

- Authoritative balance graph:
  - `GameSimulator.step(...)` -> `tickYinYang()` -> `YinYangComponent.decay(DT)` -> `YinYangComponent.absorbYin(...)` or `YinYangComponent.absorbYang(...)` -> `YinYangComponent.isBalanced()`
- Snapshot graph:
  - `GameSimulator.getSnapshot(frame)` -> write `PlayerState.yinValue/yangValue/flowMode` -> `WorldSnapshot`
- Render graph:
  - `GameScreen.render(delta)` -> `EntityRenderer.render(batch, snap, delta)` -> `EntityRenderer.renderCompanions(batch, player, delta)` -> orbit/sizing from `player.yinValue`, `player.yangValue`, `player.flowMode`

## Design notes

- Companions are visualized state, not independent server entities.
- Orbit constants are defined in `EntityRenderer` (`COMPANION_RADIUS`, `COMPANION_SPEED`).
- Flow mode doubles orbit speed and enables extra visual linkage.

## Current gaps

- No separate gameplay AI/behavior module for companions; this is currently a rendering-language system for yin/yang state readability.

## Legacy archive

Python/Pygame version is archived at:
`docs/archive/retired/2026-04-21_v0.11.71_python-systems-docs/COMPANIONS.md`
