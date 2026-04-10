# Phase 0 Audit — Indie Ninja Adventures (Java)
**Date:** 2026-04-09 | **Version audited:** v0.10.73 | **Auditor:** Claude (Phase 0 baseline)

---

## Overview

This document is a regression-proof foundation audit of the Java 2D procedural multiplayer ninja Metroidvania prototype. It covers all five subsystems specified in the Phase 0 brief, identifies failure points, and provides recommendations for integrating PostgreSQL (persistence) and Redis (real-time caching). The audit is written against the `master` branch as of the date above.

**Module layout:**
| Module | Role |
|--------|------|
| `:core` | Shared ECS, physics, world generation, network types, inventory/crafting |
| `:server` | Netty authoritative server, zone sim loop, delta encoding |
| `:client` | libGDX desktop client, rendering, UI overlays, dialogue/missions |

**Test coverage:** 3 test files (PhysicsParityTest, GameSimulatorTest, ProtocolParityTest) — all in `:server`.

---

## 1. Entity / Component System

### Files
- [core/Entity.java](core/src/main/java/com/indieniinja/core/Entity.java)
- [core/EntityManager.java](core/src/main/java/com/indieniinja/core/EntityManager.java)
- [core/Component.java](core/src/main/java/com/indieniinja/core/Component.java)
- [core/EventBus.java](core/src/main/java/com/indieniinja/core/EventBus.java)

### What works
- **Clean ECS**: Entity holds ID + type + optional PhysicsState + a `Map<Class, Component>`. Components compose behavior without inheritance chains.
- **Pre-built active list**: `EntityManager.activeEntities()` returns a cached `List<Entity>` rebuilt only on spawn/destroy — zero allocation on the 60 Hz hot path.
- **Priority event bus**: `EventBus.subscribe(class, handler, priority)` — physics runs at 60, collision at 45, mechanics at 40. Adding a new system with explicit priority never breaks existing ordering.
- **Component lifecycle**: `initialize()` / `update()` / `cleanup()` hooks are clear and consistently called.
- **Tag system**: string tags on entities allow lightweight grouping without creating new EntityType enum values.

### Weaknesses / Failure Points

| # | Issue | Risk |
|---|-------|------|
| ECS-1 | **No cache integration hook on spawn/destroy.** `EntityManager.create()` and `destroy()` have no listener/observer extension point. Adding Redis invalidation later requires modifying `EntityManager` directly, which risks breaking the physics hot path. | Medium |
| ECS-2 | **No `Component` serialization interface.** Components have no `toMap()` / `fromMap()` contract. DB serialization (PostgreSQL) for persistent components (health, abilities, inventory) requires ad-hoc casting in every persistence layer. | High |
| ECS-3 | **Tag index drift.** `Entity.addTag()` does NOT call `EntityManager.indexTag()` — it must be called separately. If any caller forgets, `byTag` queries return stale results silently. | Medium |
| ECS-4 | **`activeEntities()` only includes physics entities.** Systems that need to tick non-physics components (UI, state machines, dialogue) must use `all()` — no documented contract for which systems should use which. | Low |
| ECS-5 | **No auto-registration for new component types.** New components (traversal, combat HUD) must be manually wired into any future cache/DB serialization registry. | Medium |

### Recommendations
- Add a `EntityLifecycleListener` interface (`onCreate`, `onDestroy`) to `EntityManager`. The Redis invalidation layer can register as a listener without touching core ECS.
- Add `Serializable` marker interface (or `toMap()` abstract method) to `Component` so a future `EntitySerializer` can iterate `entity.components()` generically.
- Move tag management so `Entity.addTag(tag)` calls back to its owning `EntityManager` (pass `em` in constructor, or use a factory method on `em`).

---

## 2. PhysicsSystem & CollisionSystem

### Files
- [physics/PhysicsSystem.java](core/src/main/java/com/indieniinja/physics/PhysicsSystem.java)
- [physics/CollisionSystem.java](core/src/main/java/com/indieniinja/physics/CollisionSystem.java)
- [physics/SpatialHash.java](core/src/main/java/com/indieniinja/physics/SpatialHash.java)
- [physics/TileRect.java](core/src/main/java/com/indieniinja/physics/TileRect.java)
- [physics/PhysicsConstants.java](core/src/main/java/com/indieniinja/physics/PhysicsConstants.java)

### What works
- **Zero allocation hot path** (single-chunk entity AABB lookup, no new objects).
- **Swept sub-step collision** activates at speeds > 8 px/tick (dash = 16 px/tick) — prevents tunnelling.
- **Tile layer handling**: SOLID blocks all, PLATFORM blocks only from above, WATER passable with velocity damping, LAVA flags `onLava`, ICE flags `onIce`, DOOR_LOCKED treated as SOLID.
- **Corner smoothing** nudges players past edge catches (4–14 px overlap range).
- **Dynamic tiles** (moving/falling platforms) injected by `GameSimulator.stepPlatforms()` before each tick — separate from spatial hash.
- **SpatialHash.remove()** works for puzzle door unlocking at runtime.

### Weaknesses / Failure Points

| # | Issue | Risk |
|---|-------|------|
| PHYS-1 | **`CollisionSystem` imports `WorldGenerator` directly.** `import com.indieniinja.world.WorldGenerator` — physics has a compile-time dependency on world generation. This violates the clean physics↔world boundary and prevents reusing `CollisionSystem` outside world context. | Medium |
| PHYS-2 | **No GAS layer.** SOLID and LIQUID (WATER) exist. GAS (mist, smoke, wind zones) has no tile type. Adding it later requires assigning a new constant and updating all tile-type switch statements across collision and rendering. | Low |
| PHYS-3 | **No ability-gated traversal hooks.** All entities get water drag, all entities get ice friction. There's no per-entity ability check (`entity.hasComponent(WaterWalkComponent.class)`) before applying medium effects. | Medium |
| PHYS-4 | **Multi-chunk `candidates()` allocates `ArrayList`.** The single-chunk fast path is zero-allocation, but entities crossing chunk boundaries (128+ px wide or at a chunk edge) hit `new ArrayList<>()`. Rare but violates the stated zero-allocation contract. | Low |
| PHYS-5 | **Dynamic tiles are not in `SpatialHash`.** Moving/falling platforms are checked via a separate `dynamicTiles` list. `SpatialHash` is not the single source of truth for collision candidates. Callers of `spatialHash.candidates()` alone won't see platforms. | Low |
| PHYS-6 | **`SpatialHash.candidates()` returns duplicates** for tiles spanning multiple chunks. CollisionSystem handles this by idempotency, but a new developer querying `candidates()` for other purposes (raycasts, AI line-of-sight) will get unexpected duplicates. | Low |
| PHYS-7 | **No raycast API.** `SpatialHash` has only `candidates()`. Line-of-sight checks for enemy AI and projectile traces must be implemented separately — there's no existing hook to add them cleanly. | Medium |

### Regression tests
`PhysicsParityTest` (6 tests) covers: freefall, terminal velocity cap, jump cut, coyote on-ground skip, constant parity with Python. **Missing:** water drag parity, lava ceiling damage trigger, corner smoothing range, swept sub-step correctness.

### Recommendations
- Replace `CollisionSystem`'s `WorldGenerator.WATER` constants with a local tile-type enum or a separate `TileLayer` class that physics can reference without depending on world generation.
- Add `PhysicsState.abilityFlags` bitmask and check it before applying medium effects.
- Add a `SpatialHash.raycast(x0,y0,x1,y1)` returning the first hit `TileRect` — enemy AI line-of-sight already needs this.
- Cache the per-room `SpatialHash` in Redis keyed by `(roomSeed, neighborDirs)` — generation is deterministic so the hash never needs to be rebuilt for previously-visited rooms.

---

## 3. WorldGenerator, RoomGenerator, WorldGraph

### Files
- [world/WorldGenerator.java](core/src/main/java/com/indieniinja/world/WorldGenerator.java)
- [world/WorldGraph.java](core/src/main/java/com/indieniinja/world/WorldGraph.java)
- [world/RoomGenerator.java](core/src/main/java/com/indieniinja/world/RoomGenerator.java)
- [world/ZonePlanner.java](core/src/main/java/com/indieniinja/world/ZonePlanner.java)
- [world/postprocess/RoomPostProcessor.java](core/src/main/java/com/indieniinja/world/postprocess/RoomPostProcessor.java)
- [world/puzzle/PuzzlePlanner.java](core/src/main/java/com/indieniinja/world/puzzle/PuzzlePlanner.java)

### What works
- **7 tile types** (AIR, SOLID, PLATFORM, ICE, WATER, LAVA, DOOR_LOCKED) — clear semantics.
- **6 world shapes** (SNAKE, BRANCHY, BLOB, SPIRAL, TREE, GRID) via `WorldShape` enum with `rev` and `straight` biases.
- **Frontier BFS** room placement with configurable pruning per shape.
- **Room type specialization**: START, EXIT, SHOP, COMBAT, PLATFORM, TREASURE, BOSS via `assignTypes()`.
- **Post-processing pipeline**: AbilityLayer → PuzzleLayer → EntityPlanner applied per room via `RoomPostProcessor`.
- **Biome system**: 5 biomes by depth — deterministic.
- **Door carving**: all 4 cardinal directions, correct thickness per wall orientation.
- **`collectGroundPositions()`**: scans grid for valid spawn points (excludes LAVA, WATER).
- **`PuzzlePlanner`**: generates edge gates and puzzle rooms for the hub.

### Weaknesses / Failure Points

| # | Issue | Risk |
|---|-------|------|
| WORLD-1 | **No looping rooms.** BFS frontier creates tree topologies. There are no back-edges — no graph cycles. Metroidvania backtracking via loops requires cycle creation, which the current generator doesn't support. | High |
| WORLD-2 | **No Redis caching for generated tile grids.** Every time a zone is initialized, `WorldGenerator.generate()` and `RoomGenerator.generate()` run from scratch. These are pure functions of `(seed, roomType, neighborDirs)` — ideal Redis cache candidates. | High |
| WORLD-3 | **No PostgreSQL persistence for `WorldGraph`.** The world seed and graph topology are regenerated each server start. A returning player gets a different world layout every session. | High |
| WORLD-4 | **`biomeForDepth()` is fragile.** `(Math.abs(worldSeed) + depth) % BIOME_COUNT` — adding or removing a biome changes all existing room biomes for the same seed. | Medium |
| WORLD-5 | **New room archetypes require manual `assignTypes()` update.** The switch-style count assignment in `WorldGraph.generate()` is not extensible via registration — adding `RoomType.PUZZLE` requires code change. | Medium |
| WORLD-6 | **`collectGroundPositions()` is O(rows × cols) per call.** At 128×128, that's 16,384 checks per room initialization. Acceptable for now, but should be memoized or cached alongside the tile grid. | Low |
| WORLD-7 | **`RoomNode.neighborDirs` is mutated during generation.** The field is a private `LinkedHashSet` exposed via unmodifiable view, but mutated via package-private `neighborDirs.add()` during `WorldGraph.generate()`. If generation is ever parallelized, this is a data race. | Low |

### Recommendations
- Add cycle edges to `WorldGraph.generate()`: after BFS completes, scan adjacent room pairs that are not yet connected and add back-edges with configurable probability.
- Redis cache key: `"room_tile:{seed}:{roomType}:{sortedNeighborDirs}"` → serialized `byte[][]`. Populate on first generation, read on re-visit.
- PostgreSQL: store `WorldGraph` as a `world_graph` table row per `(hub_id, world_seed, shape)` with rooms as a JSONB column. Load on reconnect.
- Move `biomeForDepth()` to a deterministic mapping table so BIOME_COUNT changes don't shift existing biomes.

---

## 4. Networking — WorldSnapshot, PlayerState, InventoryState

### Files
- [network/WorldSnapshot.java](core/src/main/java/com/indieniinja/network/WorldSnapshot.java)
- [network/PlayerState.java](core/src/main/java/com/indieniinja/network/PlayerState.java)
- [network/InventoryState.java](core/src/main/java/com/indieniinja/network/InventoryState.java)
- [server/DeltaEncoder.java](server/src/main/java/com/indieniinja/server/DeltaEncoder.java)
- [server/ZoneSimulationLoop.java](server/src/main/java/com/indieniinja/server/ZoneSimulationLoop.java)

### What works
- **CRC32 delta encoding** for enemies, pickups, falling platforms — changed-only diffs.
- **Full snapshot every 60 broadcasts (~3s)** with `DeltaEncoder.reset()` to force full re-diff.
- **Zero-copy multicast**: snapshot encoded once, `Unpooled.wrappedBuffer()` written to all zone members.
- **Shurikens always sent** (2s TTL < full-snapshot interval, cannot use delta).
- **Moving platforms always sent** (position changes every tick).
- **Overflow entities** for adjacent-zone entities visible through door openings.
- **`worldRooms` list** on full snapshots — client reconstructs megamap.
- **`LockSupport.parkNanos` + spin** for sub-millisecond tick precision on Windows.
- **`AtomicReference<InputCommand>` on `PlayerRecord`** — Netty I/O thread writes, sim loop reads — lock-free.
- **Authoritative physics in Phase B**: server now owns player positions; client input drives the sim.

### Weaknesses / Failure Points

| # | Issue | Risk |
|---|-------|------|
| NET-1 | **Phase B player positions are server-authoritative but `PlayerRecord.posX/Y` is still read at spawn.** Comment says "explicitSpawnSet" for room-crossing players. If `explicitSpawnSet` is not set before first tick, new players spawn at `pr.posX/pr.posY` (default 0,0). | Medium |
| ~~NET-2~~ | ~~**`DeltaEncoder` checksums are in-memory only.**~~ **FIXED v0.10.79** — `ZoneStateCache` persists full snapshots to Redis (`zone:{hubId}:state`, 5-min TTL); reconnecting clients receive cached state via `bootstrapLateJoiner`. | ~~Low~~ |
| ~~NET-3~~ | ~~**`Long.valueOf(cs).equals(...)` boxes a primitive Long every enemy per tick.**~~ **FIXED v0.10.79** — replaced with `getOrDefault(id, Long.MIN_VALUE) != cs` in all 3 `DeltaEncoder` hot paths. | ~~Low~~ |
| NET-4 | **No delta encoding for NPCs or bosses.** Both are always serialized in full. If NPC count is large (shops + puzzle NPCs + overflow), this adds unnecessary bandwidth every broadcast tick. | Medium |
| NET-5 | **`InventoryState` not delta-encoded.** Full 20-slot array serialized on every player state update regardless of whether inventory changed. | Low |
| ~~NET-6~~ | ~~**No schema version guard.**~~ **FIXED v0.10.79** — `WorldSnapshot.schemaVersion` (= `SCHEMA_VERSION = 1`) stamped on every snapshot; `fromMap`/`toMap` round-trips it. | ~~High~~ |
| ~~NET-7~~ | ~~**No desync detection.**~~ **FIXED v0.10.79** — `WorldSnapshot.frameHash` (CRC32 over enemies/pickups/players) computed by `ZoneSimulationLoop.computeFrameHash()` and stamped each frame. 15 regression tests in `NetworkingDesyncTest`. | ~~High~~ |
| ~~NET-8~~ | ~~**No Redis integration for authoritative world state.**~~ **FIXED v0.10.79** — `ZoneStateCache` writes full snapshots to Redis on every `FULL_SNAPSHOT_EVERY` broadcast. Enable with `-Dredis.host=<host>`. | ~~High~~ |

### Recommendations
- Add a `WorldSnapshot.schemaVersion` field (integer, default 1) and validate on both sides. Increment when fields are added.
- Replace `Long.valueOf(cs).equals(...)` with direct primitive comparison in `DeltaEncoder`.
- Add a `frameHash` field to `WorldSnapshot` (XOR of all entity positions rounded to int). Client compares against its interpolated state; mismatch triggers a full-snapshot request.
- Redis key `"zone:{hubId}:state"` → msgpack-encoded `WorldSnapshot` (full, not delta). Written every FULL_SNAPSHOT_EVERY broadcasts. Clients requesting reconnect get this cached state rather than waiting for the next broadcast cycle.

---

## 5. Inventory, Crafting, Shops

### Files
- [sim/SimInventory.java](core/src/main/java/com/indieniinja/sim/SimInventory.java)
- [sim/ItemDatabase.java](core/src/main/java/com/indieniinja/sim/ItemDatabase.java)
- [sim/RecipeBook.java](core/src/main/java/com/indieniinja/sim/RecipeBook.java)
- [sim/CraftingRecipe.java](core/src/main/java/com/indieniinja/sim/CraftingRecipe.java)
- [sim/SimShop.java](core/src/main/java/com/indieniinja/sim/SimShop.java)

### What works
- **`SimInventory`**: sparse 20-slot array, item stacking, currency field separate from slots, equip/unequip weapon+armor, consumable use with `healthRestore`.
- **`ItemDatabase`**: static `HashMap`, immutable after class load — thread-safe for all reads, 25 items across weapons/armor/consumables/currency/materials.
- **`RecipeBook`**: static list + by-id map, 8 recipes. `byCategory()` for UI grouping.
- **Rarity system**: `rarityMult()` for shop price scaling.
- **`SimInventory.toMap()`**: full msgpack-serializable representation for network state.

### Weaknesses / Failure Points

| # | Issue | Risk |
|---|-------|------|
| INV-1 | **`ItemDatabase` is hardcoded in a static initializer.** Adding a new item requires a source code change and recompile. No path to runtime item registration, external data file, or database loading. | High |
| INV-2 | **`RecipeBook` is hardcoded.** Same as INV-1 — no external data or DB backing. | High |
| INV-3 | **`SimInventory` has no PostgreSQL persistence.** Server restart = inventory loss. No `save()` / `load()` path to a database. | High |
| INV-4 | **No ability item type.** `ItemDatabase` has `weapon`, `armor`, `consumable`, `material`, `currency`, `quest_item`, `key_item` types, but no `ability` type for traversal unlocks (double jump, dash, wall climb). These must be tracked outside the item system. | Medium |
| INV-5 | **`craft_iron_from_coin` uses `coin` as a material ingredient.** Coins are tracked in `SimInventory.currency` as an integer, not a slot item. If `addItem("coin", ...)` isn't called alongside `addCurrency()`, the crafting system won't find coins in slots, and this recipe silently fails. | High |
| INV-6 | **No cache-first read path.** `ItemDatabase.get()` is a direct HashMap lookup — fine for static data, but if items are ever loaded from DB, there's no Redis cache-miss / cache-hit layer. | Medium |
| INV-7 | **`SimInventory.addItem()` is O(slots) for stack lookup.** Acceptable at 20 slots, but if MAX_SLOTS ever grows, this becomes a linear scan. | Low |
| INV-8 | **`InventoryState` not versioned.** No `version` or `lastModifiedTick` field — DB persistence can't detect stale writes or merge concurrent updates. | Medium |

### Recommendations
- Load items and recipes from a JSONB column in PostgreSQL (`item_defs` table, `recipe_defs` table). Keep `ItemDatabase`'s `HashMap` as a hot cache, populated at server startup from DB. Redis cache: `"items:all"` → serialized item list, invalidated on admin item update.
- Add `"ability"` item type and `abilityId` field to `ItemDef`. `SimPlayer` checks `inventory.hasItem("ability_double_jump")` rather than a separate boolean.
- Fix `craft_iron_from_coin`: either always sync coins to a slot (`coin` pseudo-item) or make crafting cost aware of the `currency` field directly.
- Add `SimInventory.save(playerId, conn)` / `load(playerId, conn)` methods targeting a `player_inventory` table.

---

## 6. Test Coverage Audit

### Existing tests

| Test | Coverage | Quality |
|------|----------|---------|
| `PhysicsParityTest` (6 tests) | Freefall, terminal velocity, jump cut, onGround no-gravity, constant parity | Good — Python reference values hardcoded |
| `GameSimulatorTest` (8 tests) | Smoke build, no-player step, 1000-tick determinism, snapshot contents, platform idle state, pickup alive state, physics constants | Good — determinism test is valuable |
| `ProtocolParityTest` | Wire protocol round-trip | Not read; assumed from name |

### Missing tests (required by Phase 0 spec)

| Test | Why needed |
|------|-----------|
| **BFS reachability**: all rooms reachable from start via `neighborDirs` | WorldGraph loops aren't tested — a disconnected graph silently breaks pathfinding and snapshot delivery |
| **Water drag parity** with Python | `CollisionSystem` applies `vx *= 0.82f` and `vy = min(vy, 2.0f)` — no Java↔Python parity check |
| **Lava ceiling damage trigger** | `onLava = true` on ceiling hit is in `resolveVertical` — no test exercises upward lava contact |
| **Swept collision non-tunnel** | No test sends an entity through a thin wall at dash speed (16 px/tick) and checks it doesn't pass through |
| **SpatialHash duplicate-free candidates** | Multi-chunk tiles return duplicates — collision is idempotent but duplicate handling is undocumented |
| **`ItemDatabase` unknown item returns null** | `SimInventory.addItem("nonexistent", 1)` should return false without NPE |
| **Crafting `craft_iron_from_coin` consistency** | `coin` pseudo-item vs `currency` field ambiguity (see INV-5) |
| **DeltaEncoder reset forces full re-diff** | No test verifies that after `reset()`, all entities appear in `enemiesChanged` |
| **Full snapshot on tick FULL_SNAPSHOT_EVERY** | No test drives `ZoneSimulationLoop` to the 60-broadcast mark |
| **Inventory persistence round-trip** | (Blocked until DB layer exists) save + load player inventory, verify equality |

### Verification tests to add (Phase 0 spec)

```java
// BFS reachability
@Test void allRoomsReachableFromStart() {
    WorldGraph g = WorldGraph.generate(42L, 20, WorldShape.BLOB);
    Set<String> visited = bfsVisit(g, g.startRoom());
    assertThat(visited.size()).isEqualTo(g.size());
}

// Physics multi-medium
@Test void waterDampsVelocity() {
    // Entity in WATER tile → after 5 ticks, |vx| < initial, |vy| <= 2.0f
}

// Delta encoder reset
@Test void deltaEncoderResetForcesDiff() {
    DeltaEncoder enc = new DeltaEncoder();
    List<EnemyState> enemies = List.of(makeEnemy("e1", 100f, 200f));
    enc.enemiesChanged(enemies); // populate baseline
    enc.reset();
    assertThat(enc.enemiesChanged(enemies)).hasSize(1); // must re-appear after reset
}
```

---

## 7. DB / Cache Readiness Summary

### Current state
| Layer | Status |
|-------|--------|
| PostgreSQL | **Not integrated.** No JDBC, no schema, no migrations. |
| Redis | **Not integrated.** No Jedis/Lettuce dependency. |
| In-memory | `DeltaEncoder` checksums, `ZoneInstance` state, `ItemDatabase` — all JVM-local. |

### Integration roadmap (Phase 0 hardening)

**PostgreSQL targets:**
| Table | Contents | When written |
|-------|----------|--------------|
| `player_inventory` | `SimInventory.toMap()` per player | On zone leave / periodic flush |
| `player_progress` | Max HP, unlocked abilities, arcade depth | On zone leave |
| `world_graph` | `WorldGraph` JSONB per hub_id + seed | On hub creation |
| `item_defs` | `ItemDatabase` rows | Server startup admin load |
| `recipe_defs` | `RecipeBook` rows | Server startup admin load |

**Redis targets:**
| Key pattern | Contents | TTL |
|-------------|----------|-----|
| `room_tile:{seed}:{type}:{dirs}` | `byte[][]` tile grid | 1 hour |
| `zone:{hubId}:state` | Full `WorldSnapshot` msgpack | 30 s (refreshed each full snapshot) |
| `session:{playerId}` | `PlayerRecord` essentials for reconnect | 5 min |
| `items:all` | Serialized `ItemDef` list | Indefinite (invalidated on admin update) |

---

## 8. Regression-Proof Expansion Checklist

Use this checklist whenever adding a new traversal ability, combat system, procedural room type, or UI system:

- [ ] **New Component**: implements `toMap()` (for DB persistence) and registers with `EntityLifecycleListener` (for cache invalidation).
- [ ] **New tile type**: constant added to `WorldGenerator`, handled in `CollisionSystem.resolveVertical/Horizontal`, handled in `ChunkRenderer`, parity test added.
- [ ] **New room archetype**: added to `WorldGraph.RoomType`, handled in `assignTypes()`, handled in `ZonePlanner`, handled in `RoomGenerator`, test coverage for generation + entity spawn.
- [ ] **New item/recipe**: added to DB (`item_defs` / `recipe_defs`) and Redis cache invalidated, NOT hardcoded in `ItemDatabase`/`RecipeBook` static initializers.
- [ ] **New network field**: `WorldSnapshot.schemaVersion` incremented, Python `to_dict()` updated simultaneously.
- [ ] **New physics constant**: added to `PhysicsConstants.java`, Python `physics_constants.py` updated, `PhysicsParityTest.constantsMatchPython()` updated.
- [ ] **New sim entity type**: `EntityType` enum extended, `GameSimulator` snapshot methods updated, `DeltaEncoder` coverage considered.

---

## 9. Priority Issue Summary

| Priority | ID | Issue | Affected Files |
|----------|----|-------|---------------|
| **Critical** | INV-5 | `craft_iron_from_coin` coin/currency split — recipe silently fails | `RecipeBook.java`, `SimInventory.java` |
| **Critical** | WORLD-3 | No PostgreSQL persistence — world graph regenerates on restart | `WorldGraph.java`, `ZoneSimulationLoop.java` |
| **Critical** | INV-3 | No inventory persistence — player progress lost on restart | `SimInventory.java` |
| ~~**High**~~ | ~~NET-7~~ | ~~No desync detection~~ — **DONE v0.10.79** `frameHash` + `NetworkingDesyncTest` | |
| ~~**High**~~ | ~~NET-6~~ | ~~No schema version guard~~ — **DONE v0.10.79** `WorldSnapshot.schemaVersion` | |
| **High** | WORLD-1 | No looping rooms — Metroidvania backtrack loops impossible | `WorldGraph.java` |
| **High** | INV-1/2 | `ItemDatabase`/`RecipeBook` hardcoded — can't add items without recompile | `ItemDatabase.java`, `RecipeBook.java` |
| **Medium** | PHYS-1 | `CollisionSystem` imports `WorldGenerator` — physics/world coupling | `CollisionSystem.java` |
| **Medium** | PHYS-3 | No ability-gated medium traversal — all entities get water/ice effects | `CollisionSystem.java`, `PhysicsState.java` |
| **Medium** | ECS-1 | No cache hook on entity spawn/destroy | `EntityManager.java` |
| ~~**Medium**~~ | ~~NET-3~~ | ~~`Long.valueOf` boxing in `DeltaEncoder` hot path~~ — **DONE v0.10.79** | |
| **Low** | PHYS-4 | Multi-chunk `candidates()` allocates `ArrayList` | `SpatialHash.java` |
| **Low** | ECS-3 | Tag index drift (`addTag` doesn't auto-index) | `Entity.java`, `EntityManager.java` |

---

*Generated by Phase 0 audit pass — next step: create task backlog from Priority Issue Summary and begin Phase 0 hardening loop.*
