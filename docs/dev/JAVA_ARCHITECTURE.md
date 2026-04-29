# Java Codebase Architecture Reference
**Indie Ninja Adventures — Shadow Ascent: The Hollowed Ninja**
**Version:** v0.11.66 | **Last updated:** 2026-04-19

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Module Layout](#2-module-layout)
3. [Core Module (`:core`)](#3-core-module-core)
   - 3.1 [ECS — Entity/Component System](#31-ecs--entitycomponent-system)
   - 3.2 [Physics & Collision](#32-physics--collision)
   - 3.3 [Simulation Entities](#33-simulation-entities)
   - 3.4 [World Generation](#34-world-generation)
   - 3.5 [Network Types (DTOs)](#35-network-types-dtos)
4. [Server Module (`:server`)](#4-server-module-server)
5. [Client Module (`:client`)](#5-client-module-client)
6. [Data Flow](#6-data-flow)
7. [Threading Model](#7-threading-model)
8. [Wire Protocol](#8-wire-protocol)
9. [Persistence Layer](#9-persistence-layer)
10. [Open Issues](#10-open-issues)

---

## 1. Project Overview

The Java codebase is a complete rewrite of the original Python/Pygame prototype. It implements a **Netty-based authoritative multiplayer server** and a **libGDX desktop client** that speak a shared msgpack wire protocol.

The Phase 0 audit (2026-04-09) identified 30+ issues. In the 20 commits since that audit (v0.10.76 → v0.10.83) every high-priority and most medium-priority issues have been resolved. The codebase is now in a sound structural state for building the Shadow Ascent gameplay systems.

**Technology stack:**

| Layer | Technology |
|-------|-----------|
| Language | Java 21 (LTS) |
| Build | Gradle 8.7 multi-module |
| Server networking | Netty 4 (NIO, boss+worker groups) |
| Client rendering | libGDX 1.12 (SpriteBatch, TextureAtlas) |
| Wire encoding | msgpack (org.msgpack.core) |
| DB connection pool | HikariCP |
| JSON (server-side) | Jackson |
| Zone state cache | Redis via Jedis (optional, `-Dredis.host=<host>`) |
| Persistence | PostgreSQL — schema defined, JDBC impl present |
| Logging | SLF4J + Logback |
| Testing | JUnit 5 + AssertJ |

**Build outputs:**
- `ninja-server-all.jar` — fat JAR, headless authoritative server
- `ninja-client-all.jar` — fat JAR, libGDX desktop client

---

## 2. Module Layout

```
java/
├── settings.gradle.kts        ← Declares :core, :shadowascent, :server, :client subprojects
├── build.gradle.kts           ← Shared dependency versions + conventions (buildAssets task)
├── core/                      ← Engine shared library — NO game-specific code
│   └── src/main/java/com/indieniinja/
│       ├── core/              ← ECS: Entity, EntityManager, EntityLifecycleListener,
│       │                          EventBus, GameClock, Component, SerializableComponent,
│       │                          EntityType, EntityTypeRegistry
│       ├── physics/           ← PhysicsSystem, CollisionSystem, SpatialHash,
│       │                          TileType (enum), TileRect, PhysicsConstants, PhysicsState
│       ├── content/           ← ContentLoader, ContentRegistry, EnemyDefinition,
│       │                          NpcDefinition, RoomTypeDefinition, GameConfig,
│       │                          ContentLoadException, ContentNotFoundException
│       └── network/           ← WorldSnapshot, PlayerState, EnemyState, InventoryState,
│                                  WireCodec, MessageType, InputCommand, …all DTOs
│                              → Published to GitHub Packages as engine-core artifact
├── shadowascent/              ← Shadow Ascent game-specific module (depends on :core via api)
│   └── src/main/java/com/indieniinja/
│       ├── sim/               ← GameSimulator + all Sim* entity classes,
│       │                          AbilityComponent, HealthComponent, InventoryComponent,
│       │                          ItemDatabase, RecipeBook, SimInventory, GameConfig refs,
│       │                          ShadowAscentEntityTypeBootstrap
│       └── world/             ← WorldGenerator, WorldGraph, RoomGenerator, ZonePlanner,
│               │                  HubRegistry, SeedHierarchy, AutotileResolver, TmxRoomLoader
│               ├── postprocess/  ← RoomPostProcessor pipeline (AbilityLayer, PuzzleLayer,
│               │                    EntityPlanner, PlacementFilter, RoomContent)
│               └── puzzle/       ← PuzzlePlanner, PuzzlePlan, AbilityGate, ValidationLayer
├── server/
│   └── src/main/java/com/indieniinja/server/
│       ├── NinjaGameServer.java         ← Entry point (main)
│       ├── ServerProtocolHandler.java   ← Netty message routing
│       ├── ZoneSimulationLoop.java      ← 60 Hz sim loop thread
│       ├── ZoneInstance.java            ← Per-zone state
│       ├── GameSession.java             ← Lobby / session registry
│       ├── PlayerRecord.java            ← Per-connection state
│       ├── DeltaEncoder.java            ← CRC32 delta snapshot encoding
│       ├── ZoneStateCache.java          ← Redis write-through for WorldSnapshot
│       ├── RoomTileCache.java           ← Redis cache for generated tile grids
│       ├── ItemCache.java               ← Redis cache for ItemDef list
│       ├── InventoryRepository.java     ← PostgreSQL: item_defs, recipe_defs, player_inventory
│       ├── InventoryDatabaseLoader.java ← Startup loader: DB rows → ItemDatabase/RecipeBook
│       └── WorldGraphRepository.java   ← PostgreSQL: world_graph table
│   └── src/test/java/com/indieniinja/server/
│       ├── PhysicsParityTest.java
│       ├── PhysicsMediumParityTest.java
│       ├── GameSimulatorTest.java
│       ├── ProtocolParityTest.java
│       ├── CollisionEdgeCaseTest.java
│       ├── DeltaEncoderTest.java
│       ├── EntityLifecycleTest.java
│       ├── NetworkingDesyncTest.java
│       ├── SnapshotBroadcastScheduleTest.java
│       ├── SpatialHashDeduplicationTest.java
│       ├── WorldGraphGenerationTest.java
│       ├── WorldGraphTest.java
│       └── InventoryPersistenceTest.java
└── client/
    └── src/main/java/com/indieniinja/client/
        ├── DesktopLauncher.java         ← Entry point (main → Lwjgl3Application)
        │
        │   ⚠ Headless test rule: any class that constructs a libGDX renderer
        │   (ShapeRenderer, BitmapFont, SpriteBatch, Texture, …) must guard
        │   with `if (Gdx.app != null)`. Client unit tests run headlessly —
        │   unconditional OpenGL construction throws NPE at test setup time.
        │   New fields on GameScreen with non-trivial constructors are high risk.
        ├── NinjaGameClient.java         ← libGDX Game, screen manager
        ├── GameScreen.java              ← Main in-game screen
        ├── GameCamera.java              ← Camera tracking + room-bound clamping
        ├── GameStateBuffer.java         ← Interpolation buffer for remote entities
        ├── InputPoller.java             ← Keyboard → InputCommand builder
        ├── audio/AudioManager.java
        ├── game/                        ← DialogueManager, MissionManager, StoryManager, SaveManager
        ├── network/NetworkClientThread.java
        ├── rendering/                   ← AnimationRegistry, ChunkRenderer, EntityRenderer,
        │                                   HudRenderer, ParticleSystem, BlobTileSet
        └── ui/                          ← MainMenuScreen, ModeSelectScreen, PauseScreen,
                                             InventoryOverlay, ShopOverlay, DialogueOverlay,
                                             MinimapRenderer, CraftingOverlay, UiStyle
```

---

## 3. Core Module (`:core`)

The `:core` module is a shared library with no entry point. Both `:server` and `:client` depend on it.

### 3.1 ECS — Entity/Component System

**Package:** `com.indieniinja.core`

#### `Component`
Base class for all entity components. Holds the owning entity's `int entityId`.

#### `SerializableComponent`
Interface implemented by components that need DB or network persistence. Requires a `toMap()` method returning a `Map<String, Object>` suitable for JSON/msgpack. Each implementing class also provides a static `fromMap(entityId, map)` factory.

Implementing components: `AbilityComponent`, `HealthComponent`, `InventoryComponent`.

#### `EntityLifecycleListener`
Interface with two callbacks:
- `onCreate(Entity)` — fired synchronously after an entity is added to `EntityManager`
- `onDestroy(Entity)` — fired synchronously before an entity is removed

Registered via `EntityManager.addLifecycleListener(listener)`. The Redis invalidation layer and PostgreSQL flush layer register here without touching the physics hot path.

#### `Entity`
Holds entity identity and state:
- `long id` — monotonically assigned by `EntityManager`
- `EntityType type` — enum (PLAYER, ENEMY, PICKUP, NPC, BOSS, PORTAL, PLATFORM, SHURIKEN)
- `PhysicsState physics` — nullable; present for all physically simulated entities
- `Map<Class<?>, Component> components` — typed component store
- `Set<String> tags` — lightweight grouping

`addTag(tag)` and `removeTag(tag)` call back to the owning `EntityManager` to keep the tag index consistent. This was a bug in the pre-audit version (ECS-3) — now fixed.

#### `EntityManager`
Manages the active entity set and the lifecycle listener chain. Key methods:
- `create(type)` → `Entity` — assigns ID, notifies lifecycle listeners
- `destroy(entity)` — notifies listeners, then removes from all maps
- `addLifecycleListener(EntityLifecycleListener)` — registers a listener
- `activeEntities()` → cached `List<Entity>` rebuilt only on spawn/destroy (zero allocation on 60 Hz path)
- `all()` → all entities including non-physics ones
- `byTag(tag)` → entities with a given tag (updated immediately by `addTag`/`removeTag`)
- `byType(type)` → entities of a given type

#### `EventBus`
Type-safe priority event bus. Subscribers run descending by priority (higher = earlier).

```java
bus.subscribe(TickEvent.class, physics::onTick, 60);    // runs first
bus.subscribe(TickEvent.class, collision::onTick, 45);  // runs second
bus.subscribe(TickEvent.class, mechanics::onTick, 40);  // runs third
```

Single-threaded — the `ZoneSimulationLoop` is the sole caller.

#### `GameClock`
Advances a fixed-timestep tick counter. `stepOne()` emits `TickEvent` on the bus.

---

### 3.2 Physics & Collision

**Package:** `com.indieniinja.physics`

#### `TileType`
Enum of collision semantics. Introduced post-audit to decouple `CollisionSystem` from `WorldGenerator` (PHYS-1 fix). Values:

| Constant | id | Behavior |
|----------|----|---------|
| AIR | 0 | Passable, no collision |
| SOLID | 1 | Blocks all movement |
| PLATFORM | 2 | One-way, blocks only downward |
| ICE | 3 | Solid, near-zero friction |
| WATER | 4 | Passable liquid; `vx *= 0.82`, `vy = min(vy, 2.0)` per tick |
| LAVA | 5 | Solid; 1 HP damage per tick on contact |
| DOOR_LOCKED | 6 | Solid; removable at runtime via `SpatialHash.remove()` |
| GAS | 7 | Passable; lighter drag than water; `ABILITY_GAS_RESIST` flag bypasses |

`TileType.of(byte id)` provides a safe lookup returning `AIR` for unknown values.

#### `PhysicsConstants`
Central constants. Java runtime values are authoritative in this repository; legacy prototype parity values live in `VainAsher/indie-ninja-prototype`.

| Constant | Value |
|----------|-------|
| `FIXED_DT` | 1/60 s |
| `GRAVITY` | 980 px/s² |
| `TERMINAL_VELOCITY` | 600 px/s |
| `JUMP_VELOCITY` | −400 px/s |
| `DASH_SPEED` | 960 px/s |
| `ROOM_WIDTH_TILES` | 128 |
| `ROOM_HEIGHT_TILES` | 128 |
| `TILE_SIZE` | 16 px |

#### `PhysicsState`
Mutable per-entity physics state:
- `float x, y` — position (pixels, Y-down)
- `float vx, vy` — velocity (px/s)
- `boolean onGround, onWall, onLava, onIce` — contact flags
- `int abilityFlags` — bitmask for per-entity physics overrides

`abilityFlags` constants (defined in `PhysicsConstants`):
- `ABILITY_WATER_WALK` — skip water drag
- `ABILITY_GAS_RESIST` — skip GAS drag
- `ABILITY_ICE_GRIP` — skip ice friction

This was added post-audit (PHYS-3 fix) — medium effects are now per-entity, not universal.

#### `PhysicsSystem`
Integrates velocity into position. Priority 60. Each tick:
1. Apply `GRAVITY` to `vy`
2. Clamp `vy` to `TERMINAL_VELOCITY`
3. `x += vx * dt`, `y += vy * dt`

#### `CollisionSystem`
Resolves tile collisions. Priority 45. Uses `TileType` enum (not `WorldGenerator` constants) — the PHYS-1 coupling is gone. Per-entity `abilityFlags` gate medium effects. Pipeline:
1. Query `spatialHash.candidates(entity.aabb)` (includes dynamic tiles)
2. Resolve horizontal overlap per tile
3. Resolve vertical overlap per tile
4. Set contact flags
5. Apply medium effects gated by `abilityFlags`

**Swept sub-step collision:** At speeds > 8 px/tick (dash = 16 px/tick), the step is subdivided to prevent tunnelling.

**Corner smoothing:** 4–14 px overlap on ledge corners is nudged to slide past.

#### `SpatialHash`
Chunk-based spatial partitioning (chunk size = 320 px = 10 tiles × 32 px). Key: `(chunkX, chunkY)` packed into a `long` — avoids boxing. Built once per room, read-only thereafter.

**`dynamicTiles` overlay (PHYS-5 fix):** Moving and falling platforms are injected each tick via `setDynamicTiles(List<TileRect>)`. Both `candidates()` and `raycast()` include them.

**`raycast(x0, y0, x1, y1)` (PHYS-7 fix):** Returns the first `TileRect` intersecting the line segment, or `null` if clear. Used for enemy AI line-of-sight and projectile traces.

**Duplicate contract (PHYS-4/6, documented):** Tiles spanning chunk boundaries appear in `candidates()` once per chunk. `CollisionSystem` is idempotent so this is safe. `SpatialHashDeduplicationTest` pins this contract explicitly.

---

### 3.3 Simulation Entities

**Package:** `com.indieniinja.sim`

#### `GameSimulator`
Orchestrates one zone's simulation. Holds per-zone lists of all entity types.

**Step pipeline (60 Hz):**
1. `applyInputs(inputs)` — update each `SimPlayer` from `InputCommand`
2. `clock.stepOne()` → `bus.emit(TickEvent)` → PhysicsSystem (60) + CollisionSystem (45) fire
3. `stepPlatforms(dt)` — advance falling/moving platform state machines; inject into `SpatialHash`
4. `stepEnemyAI(dt)` — patrol/chase/attack FSMs
5. `stepCombat()` — enemy→player damage
6. `stepPickups(dt)` — pickup lifetime tick + collection

**Snapshot assembly:** `getSnapshot(frame)` serializes all entity lists to `WorldSnapshot` for broadcast.

#### `AbilityComponent` (implements `SerializableComponent`)
Tracks unlocked traversal abilities: `"double_jump"`, `"dash"`, `"wall_jump"`, `"shuriken"`, `"teleport"`, `"ninjutsu"`. Also accepts `"ability_*"` prefixed IDs from `ItemDatabase`. `toMap()` → `{"unlocked_abilities": [...]}`. Static `fromMap()` for DB/network restore.

#### `HealthComponent` (implements `SerializableComponent`)
Tracks `hp`, `maxHp`, and invincibility frame counter. `toMap()` / `fromMap()` for persistence.

#### `InventoryComponent` (implements `SerializableComponent`)
Wraps a `SimInventory` reference; provides `toMap()` by delegating to `SimInventory.toMap()`.

#### `SimPlayer`
Server-side player. Holds `PhysicsState`, `HealthComponent`, `AbilityComponent`, `InventoryComponent`, and slot (0-3).

#### `SimEnemy`
Server-authoritative enemy with `EnemyAIState` FSM: `PATROL → CHASE → ATTACK → STUNNED`.

#### `SimBoss`
Multi-phase enemy with `BossAIState`. Phase infrastructure exists; no behavioral patterns implemented yet.

#### `SimNPC`
Non-combat entity. May be a shop (registered in `GameSimulator.shops`), dialogue trigger, or hub character. State exposed via `NPCState` in snapshots.

#### `SimPickup`
Time-limited pickup. Server tracks collection authoritatively.

#### `SimShuriken`
Projectile. Always sent in full (not delta-encoded) — 2s TTL < full-snapshot interval.

#### `SimMovingPlatform` / `FallingPlatform`
Dynamic tiles. Injected into `SpatialHash.setDynamicTiles()` before each physics tick.

#### `InputRecorder` / `ReplayPlayer`
Ring-buffer input recording and deterministic replay. Foundation for the Echo system.

#### `ItemDatabase`
`HashMap<String, ItemDef>` of all item definitions. **Post-audit state:** Now loaded from PostgreSQL at server startup via `InventoryDatabaseLoader`. Static initializer provides fallback defaults (tagged `// SEED-DATA: move to DB`). `reload(List<ItemDef>)` replaces the map atomically. Supports item types: `weapon`, `armor`, `consumable`, `material`, `currency`, `quest_item`, `key_item`, `ability`. Thread-safe for reads after `reload()`.

#### `RecipeBook`
List of `CraftingRecipe`. Same DB-load path as `ItemDatabase` via `InventoryDatabaseLoader.loadRecipeDefs()`. `reload(List<CraftingRecipe>)` replaces atomically.

#### `SimInventory`
Per-player inventory: 20-slot sparse array + `currency` integer. Post-audit fixes:
- `craft_iron_from_coin` now checks `currency` balance directly (not slot contents) — INV-5 fixed
- `toMap()` / `fromMap()` for PostgreSQL round-trip
- `save(playerId, conn)` / `load(playerId, conn)` target `player_inventory` table

---

### 3.4 World Generation

**Package:** `com.indieniinja.world`

#### `WorldGenerator`
Generates a deterministic tile grid for one room. `generate(seed, cols, rows)` → `byte[rows][cols]`.

**Generation passes:**
1. Boundary SOLID fill
2. Door openings on neighboured edges (DOOR_HALF = 4; total opening = 9 tiles)
3. Layered horizontal platforms (biome-dependent density)
4. Mid-structures: pillars, ledges
5. LAVA / WATER / ICE / GAS sections by biome

**Tile constants:** `AIR=0, SOLID=1, PLATFORM=2, ICE=3, WATER=4, LAVA=5, DOOR_LOCKED=6, GAS=7` — mirror `TileType` enum ids.

#### `WorldGraph`
Multi-room graph generator. `WorldGraph.generate(seed, numRooms, WorldShape)` returns a graph of `RoomNode` objects.

**Post-audit additions:**
- **Back-edges (WORLD-1 fix):** After BFS, adjacent room pairs that are not yet connected are given back-edges with configurable probability (~15%). This creates the graph cycles needed for Metroidvania backtracking.
- **Deterministic biomes (WORLD-4 fix):** `biomeForDepth()` now uses a stable hash (`(seed ^ (depth * 2654435761L)) % BIOME_COUNT`) — adding biomes no longer shifts existing room biomes for the same seed.
- **`fromRooms(rooms, startRoom, exitRoom)` factory:** Reconstructs a `WorldGraph` from a deserialized room map (PostgreSQL load path).

**`RoomType` enum:** `START, EXIT, SHOP, COMBAT, PLATFORM, TREASURE, BOSS`

**`WorldShape` enum:** `SNAKE, BRANCHY, BLOB, SPIRAL, TREE, GRID` (with `rev` and `straight` biases)

#### Progression Graph (`world/progression/`)

Pure macro progression layer above `WorldGraph`. This is implemented for
deterministic modelling, validation, and snapshot export now; later
section/layout slices will consume it for room placement.

| Class | Role |
|-------|------|
| `WorldProgressionGraph` | Immutable container for central hub, region hubs, dungeon nodes, optional branches, critical path, and snapshot serialization. |
| `WorldProgressionGenerator` | Deterministically creates macro progression from world seed. |
| `ProgressionValidator` | Walks reachable progression nodes while accumulating grants; fails if any required node remains blocked. |
| `ProgressionValidationResult` | Validation outcome, reachable ids, collected grants, and blocked required node ids. |

Current graph levels are `CENTRAL_HUB`, `REGION_HUB`, and `DUNGEON`.
Requirements/grants use the same ability-id vocabulary as runtime progression
systems (`double_jump`, `dash`, `wall_jump`, `shuriken`, `teleport`,
`ninjutsu`), but this layer does not yet mutate player state or server
persistence.

#### `RoomGenerator`
Generates tile content for a specific `RoomType`, delegating to `WorldGenerator` for base layout then stamping room-type-specific content.

#### `ZonePlanner`
Maps `RoomType` → zone metadata: zone name, enemy density, loot tier, biome override.

#### `HubRegistry`
Static definitions of hub worlds (Bamboo Courtyard, Chasm of Still Shadows). Each entry specifies: hub ID, world seed, room count, world shape, NPC roster, ability unlock gates. Foundation for the GDD hub evolution system — state machines not yet implemented.

#### `SeedHierarchy`
Derives deterministic sub-seeds: `(worldSeed, hubIndex, roomIndex)` → unique room seed.

#### `AutotileResolver`
Determines blob-tileset variant index for each tile based on 8 neighbours. Used by client `ChunkRenderer`.

#### Post-Processing Pipeline (`world/postprocess/`)

Applied per-room by `RoomPostProcessor`:
1. **`AbilityLayer`** — stamps ability gates based on room depth and player abilities
2. **`PuzzleLayer`** — places `DOOR_LOCKED` tiles at `PuzzlePlan` positions
3. **`EntityPlanner`** — selects enemy types, pickup positions, NPC placements
4. **`PlacementFilter`** — validates spawn points don't overlap solid tiles or lava
5. **`RoomContent`** — immutable result DTO (tile grid + all placements)
6. **`RoomContentDebugger`** — ASCII map to stdout for local testing

`ZoneSimulationLoop.NEW_PIPELINE_ENABLED = true` activates this pipeline by default.

#### Puzzle System (`world/puzzle/`)

| Class | Role |
|-------|------|
| `PuzzleType` | `CHAIN_REACTION, SIMULTANEOUS_TIMING, ASYMMETRIC_LOCK, MEMORY_SEQUENCE, SPLIT_PATH` |
| `Puzzle` | Type + trigger positions + solution state + reward (ability gate unlock) |
| `PuzzlePlan` | All puzzles for one room + door positions |
| `PuzzlePlanner` | Generates `PuzzlePlan` for a room based on type and depth |
| `AbilityGate` | A locked door requiring a specific named ability |
| `ValidationLayer` | Verifies a `PuzzlePlan` is solvable given an ability set |

---

### 3.5 Network Types (DTOs)

**Package:** `com.indieniinja.network`

All DTOs use `toMap()` / `fromMap(Map)` for msgpack serialization through `WireCodec`. All `fromMap()` calls use `getOrDefault` with safe defaults for backward compatibility.

| Class | Contents | Delta-encoded |
|-------|----------|---------------|
| `WorldSnapshot` | All entity states + frame metadata | Full every 60 broadcasts; delta otherwise |
| `PlayerState` | position, velocity, animation, HP, abilities, inventory | No (always sent) |
| `EnemyState` | id, position, HP, AI state, type | Yes (CRC32 per enemy) |
| `PickupState` | id, position, type, alive | Yes (CRC32 per pickup) |
| `NPCState` | id, position, dialogue state, shop flag | No (no delta — see NET-4) |
| `BossState` | id, position, HP, phase, AI state | No (no delta) |
| `ShurikenState` | id, position, velocity, owner | No (always sent — short TTL) |
| `PlatformState` | id, position, type, state | No (always sent — moves each tick) |
| `MovingPlatformState` | id, position, waypoints | No |
| `PortalState` | id, position, destination zone | No |
| `InventoryState` | 20-slot array + currency | No (full each update — see NET-5) |
| `ShopState` | NPC id, item list, prices | No |
| `InputCommand` | tick, dx/dy, jump/dash/attack flags | N/A (client → server) |
| `WorldRoomDescriptor` | roomType, gridX/Y, neighborDirs, biome | N/A (megamap only) |

**`WorldSnapshot` metadata (post-audit):**
- `schemaVersion` — integer constant `SCHEMA_VERSION = 1`; validated on decode; bumped on breaking DTO changes (NET-6 fix)
- `frameHash` — CRC32 over all enemy/pickup/player positions; client compares for desync detection (NET-7 fix)
- `isDelta` — `true` for delta snapshots; `false` for full. Full snapshots include `worldRooms`, `shops`, `portals`; delta snapshots omit them

**`WireCodec`:** Handles msgpack encode/decode. Frame format: `[4-byte big-endian uint32 length][msgpack body]`.

**`MessageType`:** String constants matching Python `network/protocol.py`: `CONNECT, DISCONNECT, INPUT, SNAPSHOT, FULL_SNAPSHOT, ZONE_CHANGE, CHAT, PING, PONG`

---

## 4. Server Module (`:server`)

**Entry point:** `NinjaGameServer.main(args)`

### Startup sequence

```
NinjaGameServer.run(port, seed)
├── new GameSession(seed)
│   └── creates initial ZoneInstance for hub-0
├── optional: HikariDataSource (if -Dpg.url=<url>)
│   ├── InventoryRepository.ensureSchema()
│   ├── WorldGraphRepository.ensureSchema()
│   └── InventoryDatabaseLoader.loadAll()  ← populates ItemDatabase + RecipeBook
├── optional: JedisPool (if -Dredis.host=<host>)
│   ├── new ZoneStateCache(pool)           ← full snapshot write-through
│   ├── new RoomTileCache(pool)            ← tile grid cache-aside
│   └── new ItemCache(pool)               ← item def cache-aside
├── new ServerProtocolHandler(session)
└── Netty ServerBootstrap
    ├── bossGroup(1)   ← accepts connections
    └── workerGroup()  ← 2×CPU I/O threads
```

### `GameSession`
Top-level server state:
- `ConcurrentHashMap<String, ZoneInstance> zones` — active zones keyed by hub ID
- Optional: `ZoneStateCache`, `RoomTileCache`, `ItemCache`, `InventoryRepository`, `WorldGraphRepository`
- World seed for the session

### `ZoneInstance`
Per-zone state container:
- `WorldGraph` for this hub
- `GameSimulator` instance
- `ConcurrentHashMap<String, PlayerRecord> players`
- `DeltaEncoder deltaEncoder`
- `int fullSnapCountdown` — tracks how many broadcasts until next forced full snapshot

### `ZoneSimulationLoop`
Dedicated platform thread (one per active zone). Key constants:

| Constant | Value | Meaning |
|----------|-------|---------|
| `TICK_NS` | 16,666,666 ns | 60 Hz target |
| `BROADCAST_EVERY` | 3 | Broadcasts at 20 Hz |
| `FULL_SNAPSHOT_EVERY` | 60 | Full re-diff every ~3 s |
| `IDLE_TTL_MS` | 120,000 ms | Tears down empty zones after 2 min |

**Tick loop:**
```
while (!shutdown) {
    long deadline = now() + TICK_NS;
    collectInputs();                    ← read InputCommands from all PlayerRecords
    sim.step(inputs, dt);               ← advance GameSimulator one tick
    tickCount++;
    if (tickCount % BROADCAST_EVERY == 0) {
        snapshot = sim.getSnapshot(tickCount);
        snapshot.frameHash = computeFrameHash(snapshot);
        if (fullSnapshot) deltaEncoder.reset();
        encoded = WireCodec.encode(applyDelta(snapshot));
        broadcast(encoded);             ← same ByteBuf to all channels (zero-copy)
        if (redisEnabled) zoneStateCache.write(zoneId, snapshot);
    }
    LockSupport.parkNanos(deadline - now());
}
```

`LockSupport.parkNanos` provides sub-millisecond sleep precision on Windows (avoids `Thread.sleep(16)` quantization at ~15ms minimum).

### `PlayerRecord`
Per-connection state:
- `Channel channel` — Netty channel for writing
- `AtomicReference<InputCommand> latestInput` — lock-free: Netty I/O thread writes, sim loop reads
- `float posX, posY` — spawn position
- `boolean explicitSpawnSet` — guards against default 0,0 spawn (NET-1, still open)

### `ServerProtocolHandler`
Netty `ChannelInboundHandler`. Routes decoded `WireMessage` by `MessageType`:
- `CONNECT` → register player, assign zone, start `ZoneSimulationLoop` if needed
- `INPUT` → write `InputCommand` to `PlayerRecord.latestInput`
- `DISCONNECT` → remove player, schedule zone teardown if empty
- `PING` → reply `PONG`

### `DeltaEncoder`
Tracks CRC32 checksums of last-broadcast entity state. Post-audit: hot path uses `getOrDefault(id, Long.MIN_VALUE) != cs` — no `Long.valueOf()` boxing (NET-3 fix).
- `enemiesChanged(enemies)` → only changed entries
- `pickupsChanged(pickups)` → only changed entries
- `platformsChanged(platforms)` → only changed entries
- `reset()` → clears baselines; next call returns all entities

### `ZoneStateCache`
Redis write-through for `WorldSnapshot` (NET-8 fix):
- Key: `zone:{hubId}:state`, TTL: 30 s, refreshed each full-snapshot broadcast
- `bootstrapLateJoiner(hubId)` → sends cached snapshot to reconnecting client immediately

### `RoomTileCache`
Redis cache-aside for generated tile grids (WORLD-2 fix):
- Key: `room_tile:{seed}:{roomType}:{sortedNeighborDirs}`, TTL: 1 hour
- Binary format: 4-byte rows + 4-byte cols + rows×cols tile bytes
- Returns `null` on miss; caller generates and calls `put()`

### `ItemCache`
Redis cache-aside for item definitions (INV-6 fix):
- Key: `items:all`, no TTL (admin-invalidated)
- `invalidate()` called whenever an item is updated via the admin path

### `InventoryRepository`
PostgreSQL implementation (JDBC + HikariCP). Tables managed: `item_defs`, `recipe_defs`, `player_inventory`. Methods:
- `ensureSchema()` — idempotent CREATE TABLE IF NOT EXISTS
- `loadItemDefs()` → `List<ItemDef>` (fed to `ItemDatabase.reload()`)
- `loadRecipeDefs()` → `List<CraftingRecipe>` (fed to `RecipeBook.reload()`)
- `saveInventory(playerId, SimInventory)` — upserts `player_inventory` row
- `loadInventory(playerId)` → `SimInventory` or null

### `InventoryDatabaseLoader`
Startup orchestrator: calls `InventoryRepository.loadItemDefs()` + `loadRecipeDefs()`, then calls `ItemDatabase.reload()` and `RecipeBook.reload()`. Falls back to static seed data if DB is unavailable.

### `WorldGraphRepository`
PostgreSQL implementation for world graph persistence (WORLD-3 fix). Table: `world_graph (hub_id PK, seed, shape, rooms JSONB)`. Methods:
- `ensureSchema()` — idempotent
- `save(hubId, WorldGraph)` — serializes `allRooms()` to JSONB
- `load(hubId)` → `WorldGraph` via `WorldGraph.fromRooms()`, or null if not found

---

## 5. Client Module (`:client`)

**Entry point:** `DesktopLauncher.main(args)` → `new Lwjgl3Application(new NinjaGameClient(), config)`

### Screen flow

```
NinjaGameClient (Game)
├── MainMenuScreen   ← title + play/quit
├── ModeSelectScreen ← single-player / multiplayer / arcade
└── GameScreen       ← main game loop (transitions back on disconnect)
```

### `GameScreen`
Orchestrates all client subsystems:
- `NetworkClientThread` — background thread receiving `WorldSnapshot` updates
- `InputPoller` — polls keyboard each frame, builds `InputCommand`
- `GameStateBuffer` — ring buffer of recent snapshots for interpolation
- `GameCamera` — follows local player, clamped to room bounds
- `ChunkRenderer` — tile grid using `BlobTileSet` autotile sprites
- `EntityRenderer` — players, enemies, pickups, NPCs via `AnimationRegistry`
- `HudRenderer` — HP bar, ability indicators, Yin/Yang stub, Lantern stub
- `ParticleSystem` — dust, hit sparks, pickup glow

**Render loop (`libGDX render()`):**
1. Accumulate delta; step physics accumulator
2. Poll input → send `InputCommand` via `NetworkClientThread`
3. Pull latest `WorldSnapshot` from `GameStateBuffer`
4. `ChunkRenderer.render(batch, camera, tileGrid, autotileIndices)`
5. `EntityRenderer.render(batch, snapshot, localPlayerSlot)`
6. `HudRenderer.render()` + `MinimapRenderer.render()`
7. Overlays if active: `InventoryOverlay`, `ShopOverlay`, `DialogueOverlay`
8. `PauseScreen` if paused

### `GameStateBuffer`
Ring buffer of recent `WorldSnapshot` objects. `interpolate(renderTime)` returns a blended snapshot for smooth rendering between server ticks. Implements dead-reckoning for missing ticks. `synchronized` ring buffer — safe across `NetworkClientThread` write and render read.

### `NetworkClientThread`
Background `Thread`. Reads length-prefixed msgpack frames from TCP socket, decodes via `WireCodec`, pushes to `GameStateBuffer`. Sends outgoing `InputCommand` messages on demand.

### `InputPoller`
Maps keyboard to `InputCommand`:
- Arrow / WASD → `dx, dy`
- Space / W / Up → `jump`
- Shift → `dash`
- Z / Ctrl → `attack`
- E → `interact`
- I → `inventory`
- ESC → pause

### `AnimationRegistry`
Loads `TextureAtlas`. Maps `(entityType, animationState)` → `Animation<TextureRegion>`.

### `ChunkRenderer`
Divides tile grid into 16×16-tile chunks. Renders only viewport-intersecting chunks. Uses `AutotileResolver` to select correct `BlobTileSet` sprite variant per tile.

### `HudRenderer`
Draws HP bar and ability icons. Yin/Yang bar and Lantern meter are stubbed — field reads from `PlayerState` but renders as blank placeholders until those systems are implemented.

### `MinimapRenderer`
Scaled room map with door indicators. Updated from `WorldRoomDescriptor` list on full snapshots.

### Game Logic (`client/game/`)

| Class | Role |
|-------|------|
| `DialogueManager` | Tracks `DialogueTree` state; advances on `interact` |
| `DialogueNode` / `DialogueChoice` | Branching dialogue data model |
| `MissionManager` | Tracks active `MissionDefinition`; checks `MissionObjective` completion |
| `MissionState` / `ObjectiveType` | FSM state + objective type enum |
| `StoryManager` | Tracks act progression, hub state, NPC roster — stub, no Act FSM yet |
| `SaveManager` / `SaveData` | Local JSON save read/write (client-side only) |

---

## 6. Data Flow

### Input path (client → server)
```
Keyboard
  └─ InputPoller.poll()
       └─ InputCommand{tick, dx, dy, jump, dash, attack, …}
            └─ NetworkClientThread.send(WireCodec.encode(cmd))
                 └─ TCP → ServerProtocolHandler.channelRead()
                      └─ PlayerRecord.latestInput.set(cmd)   ← AtomicReference
```

### Snapshot path (server → client)
```
ZoneSimulationLoop (60 Hz)
  └─ sim.step(inputs, dt)
       └─ tickCount % BROADCAST_EVERY == 0:
            └─ sim.getSnapshot()          ← WorldSnapshot assembly
                 └─ DeltaEncoder.diff()   ← CRC32 delta
                      └─ snapshot.frameHash = computeFrameHash()
                           └─ WireCodec.encode()   ← one ByteBuf
                                ├─ broadcast()      ← all player channels (zero-copy)
                                └─ ZoneStateCache.write()  ← Redis
                                     └─ TCP → NetworkClientThread.receive()
                                          └─ GameStateBuffer.push(snapshot)
                                               └─ GameScreen.render()
                                                    └─ interpolate + draw
```

---

## 7. Threading Model

| Thread | Owner | Responsibility |
|--------|-------|----------------|
| Netty boss (×1) | `NioEventLoopGroup(1)` | Accept TCP connections |
| Netty worker (×2n CPU) | `NioEventLoopGroup()` | Read/write per channel; call `ServerProtocolHandler` |
| Zone sim (×1 per zone) | `ExecutorService` platform thread | 60 Hz `ZoneSimulationLoop` |
| libGDX render | LWJGL3 | Render loop + input poll |
| Network client (×1) | `NetworkClientThread` | TCP read + `GameStateBuffer.push()` |

**Netty I/O ↔ sim loop:** `PlayerRecord.latestInput` is `AtomicReference<InputCommand>` — Netty writes, sim reads. No lock.

**Network client ↔ render:** `GameStateBuffer` is `synchronized` — `NetworkClientThread.push()` and `GameScreen.interpolate()` synchronize on the buffer instance.

---

## 8. Wire Protocol

**Frame format:** `[4-byte big-endian uint32 length][msgpack body]`

**Netty decode pipeline:** `LengthFieldDecoder → MsgpackBodyDecoder → ServerProtocolHandler`

**`WireMessage` (msgpack map):**
```
{ "type": "snapshot", "payload": { … } }
```

**Compatibility invariants:**
- `PROTOCOL_VERSION = "2"` — must match on all Java and Python participants
- `WorldSnapshot.SCHEMA_VERSION = 1` — incremented on breaking DTO change; validated on decode
- All `fromMap()` uses `getOrDefault` with safe defaults (old client receives new snapshot → no crash)

---

## 9. Persistence Layer

### Current state (v0.10.83)

| Store | Status |
|-------|--------|
| PostgreSQL | **Integrated.** `InventoryRepository` (item_defs, recipe_defs, player_inventory) and `WorldGraphRepository` (world_graph) are fully implemented. Enabled with `-Dpg.url=jdbc:postgresql://…` |
| Redis | **Integrated (optional).** `ZoneStateCache` (zone snapshots), `RoomTileCache` (tile grids), `ItemCache` (item defs). Enabled with `-Dredis.host=<host>` |
| Client JSON saves | **Working.** `SaveManager` reads/writes local JSON |

### PostgreSQL schema

```sql
-- Managed by InventoryRepository.ensureSchema()
CREATE TABLE IF NOT EXISTS item_defs (
    id            TEXT    PRIMARY KEY,
    type          TEXT    NOT NULL,
    rarity        TEXT    NOT NULL,
    name          TEXT    NOT NULL,
    description   TEXT    NOT NULL DEFAULT '',
    max_stack     INT     NOT NULL DEFAULT 1,
    value         INT     NOT NULL DEFAULT 0,
    consumable    BOOLEAN NOT NULL DEFAULT FALSE,
    attack_bonus  INT     NOT NULL DEFAULT 0,
    defense_bonus INT     NOT NULL DEFAULT 0,
    speed_bonus   FLOAT   NOT NULL DEFAULT 0,
    health_bonus  INT     NOT NULL DEFAULT 0,
    ability_id    TEXT,   -- non-null for type='ability'
    health_restore INT    NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS recipe_defs (
    id         TEXT  PRIMARY KEY,
    result_id  TEXT  NOT NULL,
    result_qty INT   NOT NULL DEFAULT 1,
    cost_gold  INT   NOT NULL DEFAULT 0,
    ingredients JSONB NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS player_inventory (
    player_id TEXT    PRIMARY KEY,
    slots     JSONB   NOT NULL DEFAULT '[]',
    currency  INT     NOT NULL DEFAULT 0,
    equipped_weapon TEXT,
    equipped_armor  TEXT
);

-- Managed by WorldGraphRepository.ensureSchema()
CREATE TABLE IF NOT EXISTS world_graph (
    hub_id TEXT    PRIMARY KEY,
    seed   BIGINT  NOT NULL,
    shape  TEXT    NOT NULL,
    rooms  JSONB   NOT NULL
);
```

### Redis key patterns

| Key | Contents | TTL |
|-----|----------|-----|
| `zone:{hubId}:state` | Full `WorldSnapshot` msgpack | 30 s (refreshed each full broadcast) |
| `room_tile:{seed}:{type}:{dirs}` | Binary tile grid | 1 hour |
| `items:all` | JSON array of `ItemDef` | No TTL (admin-invalidated) |

---

## 10. Open Issues

The Phase 0 audit identified ~30 issues. After 20 post-audit commits the following remain open. All high-priority issues are resolved.

### Still open

| ID | Issue | Risk | Notes |
|----|-------|------|-------|
| NET-1 | Default 0,0 spawn if `explicitSpawnSet` not set before first tick | Med | `PlayerRecord.explicitSpawnSet` guards this; risk is at connect race condition |
| NET-4 | NPCs and bosses not delta-encoded | Med | Full serialization each broadcast; acceptable until NPC counts grow large |
| NET-5 | `InventoryState` full-serialized every player state update | Low | No `version`/`lastModifiedTick` field for dirty detection |
| WORLD-5 | New room archetypes require manual `assignTypes()` update | Med | No registration mechanism for `RoomType` count allocation |
| WORLD-6 | `collectGroundPositions()` O(rows×cols) per call | Low | 16,384 checks at 128×128; acceptable now |
| WORLD-7 | `RoomNode.neighborDirs` mutated during generation | Low | Data race if generation is ever parallelized |
| ECS-4 | No auto-registration for new component types | Low | Future cache/DB registry requires manual wiring |

### Documented contracts (not bugs)

| ID | Contract | Test |
|----|----------|------|
| PHYS-4 | Multi-chunk `candidates()` allocates `ArrayList` (not zero-allocation) | `SpatialHashDeduplicationTest` |
| PHYS-6 | `candidates()` may return a tile twice when it spans chunk boundaries | `SpatialHashDeduplicationTest` |

### Test coverage still missing

| Test | Why needed |
|------|-----------|
| Lava ceiling damage trigger | `onLava = true` on upward contact in `resolveVertical` — not covered |
| Swept collision non-tunnel | No test sends entity through thin wall at dash speed (16 px/tick) |

### Resolved (for reference)

All ECS issues (ECS-1/2/3/5), all physics issues (PHYS-1/2/3/5/7), all world gen issues (WORLD-1/2/3/4), all networking issues (NET-2/3/6/7/8), and all inventory issues (INV-1/2/3/4/5/6) were resolved in commits v0.10.76–v0.10.83.
