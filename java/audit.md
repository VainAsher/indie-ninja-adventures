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

Use this checklist whenever adding a new traversal ability, combat system, procedural room type, or UI system. Each section lists every file that must change, the minimum test required, and any persistence/cache action. **A feature is not merged until every checked box is green.**

---

### 8.1 New Component

A Component is any class that attaches state/behaviour to an `Entity` (e.g. `HealthComponent`, `WallClimbComponent`, `StatusEffectComponent`).

**Files to modify:**
- [ ] Create `core/src/main/java/com/indieniinja/core/<Name>Component.java` — implement `Component` (and `toMap()` / `fromMap()` once ECS-2 is resolved)
- [ ] `core/src/main/java/com/indieniinja/core/EntityManager.java` — register the component in any future `EntityLifecycleListener` hook (ECS-1)
- [ ] `server/src/main/java/com/indieniinja/server/ZoneSimulationLoop.java` — if the component drives networked state, update snapshot assembly

**Test required:**
- [ ] One `@Test` in `server/src/test/java/com/indieniinja/server/GameSimulatorTest.java` (or a new `<Name>ComponentTest`) that: (a) attaches the component to an entity, (b) ticks, (c) asserts the expected state change

**Persistence / cache:**
- [ ] If the component holds player-persistent data (health cap, ability unlocks): add a column or JSONB key in `player_progress` and implement `save(playerId, conn)` / `load(playerId, conn)`
- [ ] Redis: if the component state must survive server restart, include it in `session:{playerId}` (TTL 5 min)

---

### 8.2 New TileType

A TileType is a new collision/physics medium (e.g. `GAS`, `CONVEYOR`, `VOID`).

**Files to modify:**
- [ ] `core/src/main/java/com/indieniinja/physics/TileType.java` — add enum constant with `id` integer matching Python
- [ ] `core/src/main/java/com/indieniinja/physics/CollisionSystem.java` — handle in `resolveVertical()` **and** `resolveHorizontal()` (at minimum: no-op if passable, or add drag/damage logic)
- [ ] `core/src/main/java/com/indieniinja/physics/SpatialHash.java` — update `isPassable()` if the tile is non-blocking for raycasts
- [ ] `client/src/main/java/com/indieniinja/client/render/ChunkRenderer.java` — add render case (color or sprite)
- [ ] Python parity: `core/collision_system.py` — update `PASSABLE_TILES` / medium-effect constants to match Java
- [ ] Python parity: `core/tile_type.py` — add matching constant with the same integer `id`

**Test required:**
- [ ] `CollisionEdgeCaseTest.java` — one test per distinct behavior: passthrough, drag, damage-on-enter, etc. Name: `<tileName>_<behavior>` (e.g. `gas_appliesDragNotDamage`)
- [ ] `PhysicsParityTest.java` — extend `constantsMatchPython()` if a new drag/damage constant is added

**Persistence / cache:**
- [ ] None (tile data lives in the procedurally generated tile grid, cached at `room_tile:{seed}:{type}:{dirs}`)

---

### 8.3 New RoomType

A RoomType is a new procedural room archetype (e.g. `ARENA`, `LIBRARY`, `FORGE`).

**Files to modify:**
- [ ] `core/src/main/java/com/indieniinja/world/WorldGraph.java` — add `RoomType` enum value; update `assignTypes()` count allocation
- [ ] `core/src/main/java/com/indieniinja/world/ZonePlanner.java` — add zone-plan logic (zone name, enemy density, loot tier)
- [ ] `core/src/main/java/com/indieniinja/world/RoomGenerator.java` — add tile-generation branch for the new archetype
- [ ] `core/src/main/java/com/indieniinja/world/postprocess/RoomPostProcessor.java` — add post-process passes if needed (ability layer, puzzle layer, entity placement)
- [ ] Python parity: `systems/megamap.py` — add `room_type` string constant matching the Java enum name (snake_case)

**Test required:**
- [ ] `WorldGraphGenerationTest.java` — one test: generate a graph with enough rooms to include at least one instance of the new type, assert it appears in the graph with valid `roomType`
- [ ] One smoke test: `RoomGenerator.generate(seed, RoomType.<NEW>, ...)` returns a non-null tile grid with the expected landmark tile(s)

**Persistence / cache:**
- [ ] `world_graph` PostgreSQL row is already keyed by `(hub_id, world_seed)` — new room types serialise through the existing JSONB column, no schema migration needed
- [ ] Redis `room_tile:{seed}:{type}:{dirs}` cache key automatically covers the new type

---

### 8.4 New Item or Recipe

An Item is a new `ItemDef` row; a Recipe is a new `CraftingRecipe` row.

**Files to modify:**
- [ ] **Do NOT touch `ItemDatabase.java` or `RecipeBook.java` static initializers** (INV-1/2 hardcoding policy)
- [ ] Write a SQL migration: `INSERT INTO item_defs ...` / `INSERT INTO recipe_defs ...`
- [ ] If `ItemDatabase` is still static (pre-DB integration): add to `ItemDatabase.java` with a `// TEMP: move to DB` comment; add to `RecipeBook.java` similarly
- [ ] If recipe involves `currency` field (not slot items): update `SimInventory.craft()` to check `currency` balance, not slot contents (INV-5 fix pattern)

**Test required:**
- [ ] `InventoryPersistenceTest.java` (or `CraftingTest.java`) — one `@Test` per recipe: call `simInventory.craft(recipeId)`, assert result item added and ingredient consumed
- [ ] If recipe involves `coin`/currency: assert `currency` field decremented, not a ghost slot

**Persistence / cache:**
- [ ] Redis: invalidate `items:all` and `recipes:all` keys after any admin item update
- [ ] PostgreSQL: item/recipe live in `item_defs` / `recipe_defs` tables — the `ItemDatabase` HashMap is a read-through cache populated at server start

---

### 8.5 New Network Field

A Network Field is any new key added to `WorldSnapshot`, `PlayerState`, `EnemyState`, `PickupState`, or `InventoryState`.

**Files to modify:**
- [ ] Add the field to the relevant `*State.java` class in `core/src/main/java/com/indieniinja/network/`
- [ ] Update `toMap()` — add the new key
- [ ] Update `fromMap()` — read with a safe default so old snapshots don't crash
- [ ] `core/src/main/java/com/indieniinja/network/WorldSnapshot.java` — **increment `SCHEMA_VERSION`** (integer constant)
- [ ] Python parity: update `to_dict()` / `from_dict()` in the matching Python dataclass (e.g. `network/world_snapshot.py`)
- [ ] Python parity: if the field is a new physics/game constant, update `physics_constants.py` / `game_constants.py`

**Test required:**
- [ ] `SnapshotBroadcastScheduleTest.java` or a new `<FieldName>RoundTripTest` — `toMap()` → `fromMap()` round-trip asserts the new field survives; assert the default value when the key is absent (old-client compat)

**Persistence / cache:**
- [ ] `ZoneStateCache` writes full snapshots to Redis — new fields are included automatically via `toMap()`; no additional cache action needed
- [ ] If the field is player-persistent (not transient per-frame): add it to `player_progress` PostgreSQL table

---

### 8.6 New Physics Constant

A Physics Constant is any new value in `PhysicsConstants.java` that drives simulation behavior (gravity, drag coefficients, speed caps, etc.).

**Files to modify:**
- [ ] `core/src/main/java/com/indieniinja/physics/PhysicsConstants.java` — add `public static final float <NAME> = <VALUE>;`
- [ ] `PhysicsSystem.java` or `CollisionSystem.java` — use the constant (never inline magic numbers)
- [ ] Python parity: `core/physics_constants.py` — add matching constant with identical value

**Test required:**
- [ ] `PhysicsParityTest.java` → `constantsMatchPython()` — add an `assertThat(<NAME>).isEqualTo(<python_value>)` line
- [ ] At least one behavioral test in `PhysicsParityTest.java` or `CollisionEdgeCaseTest.java` that exercises the constant's effect (e.g. terminal velocity cap, drag over N ticks)

**Persistence / cache:**
- [ ] None (constants are compile-time, no runtime cache needed)

---

### 8.7 New Sim Entity Type

A Sim Entity Type is a new `EntityType` value (e.g. `BOSS`, `NPC_VENDOR`, `PROJECTILE`).

**Files to modify:**
- [ ] `core/src/main/java/com/indieniinja/core/EntityType.java` — add enum value
- [ ] `server/src/main/java/com/indieniinja/server/GameSimulator.java` — update `buildSnapshot()` / `populateEnemies()` (or equivalent) to include the new entity type in snapshots
- [ ] `core/src/main/java/com/indieniinja/network/EnemyState.java` (or new `*State` class) — add wire type if the entity has distinct network representation
- [ ] `server/src/main/java/com/indieniinja/server/DeltaEncoder.java` — decide: delta-encoded (add checksum map) or always-sent (add to `alwaysSent` list)
- [ ] `core/src/main/java/com/indieniinja/world/WorldGraph.java` — update `collectGroundPositions()` exclusion list if entity cannot spawn on certain tile types
- [ ] Python parity: `entities/` — add matching Python entity class

**Test required:**
- [ ] `GameSimulatorTest.java` — one smoke test: zone with one entity of the new type, tick 10 frames, assert it appears in the snapshot
- [ ] `DeltaEncoderTest.java` — if delta-encoded: assert changed/removed lists populate correctly; if always-sent: assert it is present in every snapshot regardless of delta flag

**Persistence / cache:**
- [ ] If entity has persistent state (boss HP, NPC dialogue progress): add a column to `player_progress` or a new `entity_state` table
- [ ] Redis: include in `zone:{hubId}:state` snapshot automatically via `toMap()` — confirm the new state class implements `toMap()`

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

*Phase 0 hardening loop complete as of v0.10.83 (2026-04-10). All Priority Issues resolved. Next: Shadow Ascent milestones — see `docs/PLAN_SHADOW_ASCENT.md`.*

---

## 10. New Content Integration — Prompt Templates

Copy the template for the feature type you are adding, fill in the `<ANGLE_BRACKETS>`, and paste into a Claude session. The agent will follow the checklist in Section 8 automatically.

---

### Template A — New Component

```text
Agent: Implementation-Agent
Context: Module: :core / :server
Feature type: Component
Name: <ComponentName>  (e.g. WallClimbComponent)
Description: <one sentence — what state/behaviour this component adds to an entity>
Ability-gated: <yes|no>  (if yes: which PhysicsState flag or ItemDatabase ability ID gates it)
Persistent: <yes|no>  (if yes: which DB table column stores it)

Tasks:
1. Create core/src/main/java/com/indieniinja/core/<ComponentName>.java
   — implement Component; add toMap() / fromMap() returning a Map<String,Object>
2. Register with EntityLifecycleListener in EntityManager (ECS-1) if the listener exists
3. If ability-gated: check PhysicsState.abilityFlags in CollisionSystem before applying effect
4. If persistent: implement save(playerId, conn) / load(playerId, conn) targeting player_progress
5. Add @Test in GameSimulatorTest (or new <ComponentName>Test):
   attach component → tick → assert expected state
6. Commit: "feat(ecs): add <ComponentName>"

Constraints:
- Do not add magic numbers; use PhysicsConstants for any numeric values
- toMap() keys must be snake_case to match Python parity
- All existing tests must stay green before committing
```

---

### Template B — New TileType

```text
Agent: Implementation-Agent
Context: Module: :core / :client
Feature type: TileType
Name: <TILE_NAME>  (e.g. GAS, CONVEYOR, VOID)
Python id: <integer>  (must match Python tile_type.py)
Collision behaviour: <SOLID|PASSABLE|ONE_WAY>
Medium effect: <none | drag vx=<val> vy=<val> | damage per tick | push velocity>
Raycast passable: <yes|no>

Tasks:
1. Add TileType.<TILE_NAME> with id=<integer> in TileType.java
2. Handle in CollisionSystem.resolveVertical() and resolveHorizontal()
   — apply medium effect or damage; mirror Python collision_system.py logic exactly
3. Update SpatialHash.isPassable() if raycast-transparent
4. Add render case in ChunkRenderer.java (color constant or sprite key)
5. Python parity: add <TILE_NAME> = <integer> to core/tile_type.py; update PASSABLE_TILES list
6. Add @Test in CollisionEdgeCaseTest: entity in <TILE_NAME> tile → assert medium effect after 1 tick
7. Extend PhysicsParityTest.constantsMatchPython() if a new constant is introduced
8. Commit: "feat(physics): add TileType.<TILE_NAME>"

Constraints:
- The integer id must be unique and never reuse a retired id
- Python and Java constants must be numerically identical — the parity test enforces this
```

---

### Template C — New RoomType

```text
Agent: Implementation-Agent
Context: Module: :core
Feature type: RoomType
Name: <ROOM_TYPE>  (e.g. ARENA, FORGE, LIBRARY)
Count per world: <integer or range>  (how many rooms of this type per 20-room world)
Tile signature: <key tile(s) that distinguish this room, e.g. "lava floor + SOLID platforms">
Entities spawned: <entity types placed by RoomPostProcessor, or "none">
Python megamap key: <snake_case string matching RoomType.name().toLowerCase()>

Tasks:
1. Add WorldGraph.RoomType.<ROOM_TYPE>; update assignTypes() count allocation
2. Add zone-plan branch in ZonePlanner (zone name, enemy density, loot tier)
3. Add tile-generation branch in RoomGenerator.generate() for RoomType.<ROOM_TYPE>
4. Add RoomPostProcessor pass if entities or ability-layer items are placed
5. Python parity: add "<python_megamap_key>" string constant to systems/megamap.py
6. Add @Test in WorldGraphGenerationTest:
   generate graph → find at least one room with roomType==<ROOM_TYPE> → assert non-null tile grid
7. Smoke test: RoomGenerator.generate(seed, RoomType.<ROOM_TYPE>, ...) returns non-null grid
8. Commit: "feat(world): add RoomType.<ROOM_TYPE>"

Constraints:
- assignTypes() count changes must not break allRoomsReachableAfterBackEdges tests
- New room type must be reachable from start (BFS test must still pass)
```

---

### Template D — New Item or Recipe

```text
Agent: Implementation-Agent
Context: Module: :core / :server
Feature type: <Item | Recipe | Both>
Item id: <snake_case_id>  (e.g. ability_wall_climb)
Item type: <weapon|armor|consumable|material|currency|quest_item|key_item|ability>
Recipe id: <snake_case_id or "none">
Recipe inputs: <item_id:qty, ...>  (use "currency:N" for coin cost — NOT a slot item)
Recipe output: <item_id:qty>

Tasks:
1. If DB-backed (post INV-1 fix): write SQL migration INSERT INTO item_defs / recipe_defs
   If still static: add ItemDef to ItemDatabase.java and CraftingRecipe to RecipeBook.java
   with comment "// TEMP: move to DB — see INV-1"
2. If recipe uses coin cost: verify SimInventory.craft() checks currency field, not slots (INV-5)
3. Add @Test in InventoryPersistenceTest or CraftingTest:
   — add ingredients → craft → assert output item added and ingredients/currency consumed
4. Invalidate Redis keys "items:all" and "recipes:all" in the server startup load path
5. Commit: "feat(inv): add item <item_id> [+ recipe <recipe_id>]"

Constraints:
- item type "ability" must include abilityId field for PhysicsState gate lookup
- Do NOT duplicate coin/currency as both a slot item and the currency field
```

---

### Template E — New Network Field

```text
Agent: Implementation-Agent
Context: Module: :core / :server
Feature type: NetworkField
Target class: <WorldSnapshot|PlayerState|EnemyState|PickupState|InventoryState>
Field name: <camelCase Java name>
Wire key: <snake_case key in toMap()>
Type: <int|long|float|boolean|String|List<...>>
Default (for old snapshots): <value>
Persistent across sessions: <yes|no>

Tasks:
1. Add field to <TargetClass>.java
2. Add wire_key to toMap() map
3. Add fromMap() read with safe default: <default_value>
4. Increment WorldSnapshot.SCHEMA_VERSION (always, even for non-snapshot classes)
5. Python parity: update to_dict() and from_dict() in the matching Python class
6. Add @Test in SnapshotBroadcastScheduleTest or new <FieldName>RoundTripTest:
   — toMap() → fromMap() round-trip; assert field survives
   — fromMap() with key absent returns default (old-client compat)
7. If persistent: add column to player_progress PostgreSQL table
8. Commit: "feat(net): add <FieldName> to <TargetClass> (schema v<N>)"

Constraints:
- SCHEMA_VERSION must be incremented before the commit that adds the field
- Python and Java defaults must be identical
- fromMap() must never throw on a missing key — use getOrDefault / null-safe helpers
```

---

### Template F — New Physics Constant

```text
Agent: Implementation-Agent
Context: Module: :core / :server
Feature type: PhysicsConstant
Constant name: <SCREAMING_SNAKE_CASE>  (e.g. CONVEYOR_PUSH_SPEED)
Java value: <numeric literal with f suffix if float>
Python value: <same numeric value>
Used in: <PhysicsSystem|CollisionSystem|both>
Behavioral effect: <one sentence>

Tasks:
1. Add public static final float <NAME> = <value>; to PhysicsConstants.java
2. Replace any inline magic number in PhysicsSystem/CollisionSystem with the constant
3. Add <NAME> = <value> to core/physics_constants.py
4. Extend PhysicsParityTest.constantsMatchPython():
   assertThat(PhysicsConstants.<NAME>).isEqualTo(<python_value>f);
5. Add behavioral @Test in PhysicsParityTest or CollisionEdgeCaseTest
   exercising the constant's effect (e.g. assert vy capped after N ticks)
6. Commit: "feat(physics): add PhysicsConstants.<NAME>"

Constraints:
- Java float and Python float must be bit-for-bit equal within assertj within(0.001f)
- Never inline the number after this commit — grep for the raw value to confirm
```

---

### Template G — New Sim Entity Type

```text
Agent: Implementation-Agent
Context: Module: :core / :server
Feature type: SimEntityType
EntityType name: <SCREAMING_SNAKE_CASE>  (e.g. BOSS, NPC_VENDOR)
Network representation: <reuse EnemyState | new <Name>State class>
Delta strategy: <delta-encoded | always-sent>
Persistent state: <none | field list for player_progress or entity_state table>
Python entity class: <entities/<name>.py>

Tasks:
1. Add EntityType.<NAME> to EntityType.java
2. If new State class: create network/<Name>State.java with toMap()/fromMap()
3. Update GameSimulator.buildSnapshot() to include entities of the new type
4. DeltaEncoder:
   — delta-encoded: add checksum Map<String,Long> and changed/removed lists
   — always-sent: add to the always-serialized block (alongside shurikens/platforms)
5. Update WorldGraph.collectGroundPositions() exclusion list if needed
6. Python parity: create entities/<name>.py with matching field names
7. Add @Test in GameSimulatorTest: zone with one <NAME> entity → tick 10 → assert in snapshot
8. Add @Test in DeltaEncoderTest: delta/always-sent contract verified
9. If persistent: write SQL migration for entity_state table or player_progress column
10. Commit: "feat(ecs): add EntityType.<NAME>"

Constraints:
- State class toMap() keys must be snake_case for Python parity
- If delta-encoded: reset() must include the new checksum map (verify in DeltaEncoderTest)
```
