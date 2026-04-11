# PLAN — Shadow Ascent: The Hollowed Ninja
## GDD Alignment & Implementation Roadmap
**Created:** 2026-04-10 | **Codebase version:** v0.10.84 | **Next release target:** v0.11.0 (Milestone 2 in progress)

---

## 0. Situation Summary

### Project history in brief

The full 296-commit git history tells a clear story of four technology pivots over ~101 days:

| Period | Technology | Version | What happened |
|--------|-----------|---------|---------------|
| Dec 31 2025 | Python/Pygame monolith | v0.4.0-dev | Initial commit |
| Jan 1 2026 | Python modular | v0.7.0 | Refactor into modules, 85-day silence follows |
| Mar 27–Apr 3 2026 | Python full-featured | v0.7.x–v0.9.16 | Animation, bosses, multiplayer, launcher, zones, delta encoding — all built in 8 days |
| Apr 4–10 2026 | Java (Netty + libGDX) | v0.10.0–v0.10.83 | Complete rewrite: server, simulator, client, all features ported, post-audit hardening |

The Java codebase landed on Apr 4 and reached v0.10.83 by Apr 10 — **6 days to rebuild everything**. The Apr 7 sprint alone was 53 commits.

**The fourth pivot is Shadow Ascent.** It exists in the GDD and these planning documents — not yet in a single line of game-specific Java code. The infrastructure is the most complete it has ever been. The game itself has not started.

### Current codebase state (v0.10.83)

The Phase 0 audit (Apr 9) identified ~30 structural issues. All 20 post-audit commits (Apr 10) resolved them systematically. Status:

| Area | Resolved | Still open |
|------|----------|-----------|
| ECS | EntityLifecycleListener, SerializableComponent, auto-tag index, concrete components | ECS-4 (no auto-registration, low risk) |
| Physics | TileType decoupling, GAS tile, abilityFlags, dynamicTiles in candidates, raycast API | PHYS-4/6 (documented contracts) |
| World gen | Back-edges (Metroidvania loops ready), Redis tile cache, PostgreSQL, deterministic biomes | WORLD-5/6/7 (low risk) |
| Networking | Schema version, frameHash desync detection, Redis zone cache, no boxing | NET-1 (spawn default, med), NET-4/5 (no NPC/inventory delta, low) |
| Inventory | DB-backed items/recipes, player_inventory persistence, ability type, coin recipe fix, item Redis cache | — |
| Tests | 13 test files; all previously-missing gaps covered | Lava ceiling trigger, swept non-tunnel |

**Two test gaps remain** before the physics is fully regression-proof. They belong in the already-existing `CollisionEdgeCaseTest` — two new `@Test` methods.

### What the GDD requires that doesn't exist

Four interlocking pillars define Shadow Ascent. None are started:

| Pillar | GDD section | Status |
|--------|-------------|--------|
| Yin/Yang system | §3.3 | Not started |
| Lantern system | §3.4 | Not started |
| Hub evolution state machine | §4 | `HubRegistry` is a static list; no FSM |
| Narrative Act FSM | §5 | `StoryManager` stub; no act transitions |

Secondary systems — boss AI behavioral patterns, Echo mechanic, puzzle archetypes, Act IV depression mechanics — also do not exist.

### The multiplayer vs. single-player decision

The GDD is single-player first with optional co-op. The codebase is multiplayer first.

**Decision:** Keep the networked architecture. Add an **in-process solo mode** where `GameSimulator` runs locally on the client, no socket required. The same rendering pipeline serves both paths. Multiplayer co-op becomes an optional overlay — Yin/Yang and Lantern work identically in both modes.

---

## 1. What to Keep

| System | Why it stays |
|--------|-------------|
| ECS (`EntityManager`, `EventBus`, `GameClock`) | New systems plug in as `Component` types and `EventBus` subscribers |
| `PhysicsSystem` + `CollisionSystem` | GDD movement (wall-jump, dash, grapple) already gated by `abilityFlags` |
| `SpatialHash` (including `dynamicTiles` + `raycast`) | `raycast` is ready for boss line-of-sight |
| `WorldGraph` (with back-edges) | Metroidvania loops are ready |
| `WorldGenerator` tile pipeline | GAS, LAVA, ICE, WATER, PLATFORM map directly to GDD mechanics |
| `RoomPostProcessor` pipeline (AbilityLayer, PuzzleLayer, EntityPlanner) | Foundation for all puzzle archetypes |
| `WireCodec`, `MessageType`, delta encoding | No protocol changes needed for new systems |
| `ZoneSimulationLoop` 60 Hz loop | Unchanged |
| `ZoneStateCache` + `RoomTileCache` + `ItemCache` | Unchanged |
| `InventoryRepository` + `WorldGraphRepository` (JDBC implemented) | Unchanged |
| `ItemDatabase` / `RecipeBook` (DB-backed) | Extend with new item types |
| libGDX rendering pipeline | Extend, not replace |
| `InputRecorder` / `ReplayPlayer` | Foundation for the Echo system |
| `DialogueManager` / `DialogueTree` | GDD NPC dialogue is minimal-symbolic; existing system is sufficient |
| `MissionManager` | Maps to "Accept mission / access level" in GDD core loop |

---

## 2. Historical lessons that shape the plan

**Lesson 1 — Boss tuning is always iterative.** The Python boss received 5 successive HP/damage commits in a single day (Mar 29) to go from unkillable to playable. Plan for boss AI behavioral patterns to need the same treatment — ship a working loop first, tune in follow-up commits.

**Lesson 2 — Physics onGround is hard.** It took 5 commits to stabilize Java `onGround` detection (Apr 5–6). The lava-ceiling trigger and swept non-tunnel test gaps are the same class of problem. Close them before building on top of the physics.

**Lesson 3 — The Apr 7 sprint produced foundations, not designs.** 53 commits built a complete game in a day. The save system, hub registry, crafting, and puzzle system all exist — but they weren't designed for Shadow Ascent. Each needs to be extended, not replaced. The instinct to rewrite will be wrong.

**Lesson 4 — Version numbers drift.** `version.json` is at 0.10.70, `build.gradle.kts` is at `0.10.7`, commit messages reference v0.10.83. Fix this immediately and keep it in sync going forward. A single `chore(release)` commit should keep all three in agreement.

**Lesson 5 — The Loop system was an effective sprint tool.** The numbered Loop system (Loop 3, Loop 7, etc.) drove rapid feature delivery during the Java rebuild. For Shadow Ascent milestones, use numbered **Milestone** labels in commit messages (`feat(m3):`, `feat(m4):`) to preserve the same traceability.

---

## 3. What to Build New

### 3.1 In-Process Solo Mode (pre-requisite for everything)

`GameScreen` gets an `offlineMode` path: instantiates `GameSimulator` locally, skips `NetworkClientThread`. Input feeds directly to local `sim.step()` each render frame. `WorldSnapshot` assembled locally and consumed by the same rendering pipeline.

**Files to modify:** `ModeSelectScreen.java`, `GameScreen.java`

No server code changes. Solo and networked clients use identical rendering paths.

---

### 3.2 Yin/Yang System (GDD §3.3)

**Yin (Emotion):** Reveals hidden platforms, slows time, environmental awareness
**Yang (Discipline):** Attack strength, movement precision, stamina
**Balance (`|yin − yang| < 0.15`):** Flow Mode — smooth animation blending + enhanced traversal + combat

```java
// core/src/main/java/com/indieniinja/sim/YinYangComponent.java
public final class YinYangComponent extends Component implements SerializableComponent {
    float yin;   // 0.0 – 1.0
    float yang;  // 0.0 – 1.0

    boolean isBalanced()          { return Math.abs(yin - yang) < 0.15f; }
    void absorbYin(float amount)  { yin = Math.min(1.0f, yin + amount); }
    void absorbYang(float amount) { yang = Math.min(1.0f, yang + amount); }

    @Override public Map<String, Object> toMap() { return Map.of("yin", yin, "yang", yang); }
    public static YinYangComponent fromMap(int id, Map<String, Object> m) { … }
}
```

**Server effects** in `GameSimulator.step()`:
- `yin > 0.7f` → set `ABILITY_YIN_SIGHT` on `PhysicsState.abilityFlags`; hidden-platform tiles become solid for this entity
- `yang > 0.7f` → attack damage multiplier 1.5×; dash stamina cost −30%
- `isBalanced()` → set `FLOW_MODE` flag on `PlayerState`

**Client effects** in `GameScreen.render()`:
- `yin > 0.7f` → `EntityRenderer` renders hidden-platform tiles with alpha ∝ Yin value
- `yang > 0.7f` → denser hit particles, sharper attack animations
- `FLOW_MODE` → lerp-based animation state blending
- `HudRenderer` Yin/Yang bar (currently stubbed — replace)

`PlayerState` gains: `yinValue`, `yangValue`, `flowMode`.
`WorldSnapshot.SCHEMA_VERSION` increments to 2.

**Files to create:** `core/sim/YinYangComponent.java`

**Files to modify:** `network/PlayerState.java`, `network/WorldSnapshot.java`, `sim/GameSimulator.java`, `physics/CollisionSystem.java`, `physics/PhysicsConstants.java`, `client/rendering/EntityRenderer.java`, `client/rendering/HudRenderer.java`

---

### 3.3 Lantern System (GDD §3.4)

Per-player float (0.0–1.0) persisted to `player_progress`. Global modifier for world clarity and physics.

```java
// core/src/main/java/com/indieniinja/sim/LanternComponent.java
public final class LanternComponent extends Component implements SerializableComponent {
    float value;  // 0.0 – 1.0

    void decay(float dt)      { value = Math.max(0f, value - 0.01f * dt); }
    void restore(float amount){ value = Math.min(1f, value + amount); }

    @Override public Map<String, Object> toMap() { return Map.of("lantern", value); }
    public static LanternComponent fromMap(int id, Map<String, Object> m) { … }
}
```

| Value | Physics effect | Visual |
|-------|---------------|--------|
| < 0.3 | Some PLATFORM tiles treated as SOLID | Full vignette |
| 0.3–0.7 | Normal | Partial shadow |
| > 0.7 | Jump height +20%, coyote time 4→8 ticks | Clear, warm |

**Server:** Decay −0.01/s in dark areas or on damage. Restore +0.05 per NPC interaction, +0.2 per Lantern fragment.
**Client:** `ChunkRenderer` vignette intensity ∝ `1.0 - lanternValue`. At low Lantern, re-rasterize PLATFORM as SOLID visually (matches server physics).

`PlayerState` gains: `lanternValue`.

**Files to create:** `core/sim/LanternComponent.java`

**Files to modify:** `network/PlayerState.java`, `sim/GameSimulator.java`, `client/rendering/ChunkRenderer.java`, `client/rendering/HudRenderer.java`

---

### 3.4 Fragment System

Three new `ItemDef` records in `ItemDatabase` (type `"ability"`, non-stackable):
- `"yin_fragment"` — calls `YinYangComponent.absorbYin(0.25f)` on pickup
- `"yang_fragment"` — calls `YinYangComponent.absorbYang(0.25f)` on pickup
- `"lantern_fragment"` — calls `LanternComponent.restore(0.2f)` on pickup

`EntityPlanner` places fragments in BOSS and TREASURE rooms.
Three new `ObjectiveType` values: `COLLECT_YIN_FRAGMENT`, `COLLECT_YANG_FRAGMENT`, `COLLECT_LANTERN_FRAGMENT`.

**Files to modify:** `sim/ItemDatabase.java`, `client/game/MissionManager.java`, `world/postprocess/EntityPlanner.java`

---

### 3.5 Hub Evolution System (GDD §4)

```java
// core/src/main/java/com/indieniinja/world/HubState.java
public enum HubState {
    FULL,       // Act I: All NPCs, stable environment
    CORRUPTED,  // Act II: NPCs disappearing, prices rise, areas close
    EMPTY,      // Act II end: Only Siren remains
    FRACTURED,  // Hub 2 initial state (Chasm of Still Shadows)
    RECOVERING, // Act V: NPCs return one by one
    WHOLE       // Act VI–VII: Full NPC roster, all abilities
}
```

```java
// core/src/main/java/com/indieniinja/world/HubStateMachine.java
public final class HubStateMachine {
    HubState state = HubState.FULL;
    int bossesDefeated = 0;
    Set<String> fragmentsCollected = new LinkedHashSet<>();

    public void onBossDefeated(String bossId)      { /* advance state */ }
    public void onFragmentCollected(String fragId) { /* may advance state */ }
    public HubState getState()                      { return state; }
    public List<String> activeNpcIds()             { /* NPC roster for current state */ }
    public List<String> openAreaIds()              { /* accessible areas */ }
    public Map<String, Object> toMap()             { /* for player_progress JSON */ }
    public static HubStateMachine fromMap(Map<String, Object> m) { … }
}
```

**NPC presence:** Each NPC definition in `HubRegistry` carries `visibleFromState` / `hiddenFromState`. `ZoneSimulationLoop` calls `hub.activeNpcIds()` once per second and spawns/despawns `SimNPC` via `EntityLifecycleListener`.

**`WorldSnapshot`** gains `hubState` field (bundled into SCHEMA_VERSION 2 increment with Yin/Yang fields).

**Hub 1 (Bamboo Courtyard) NPC rosters:**
- `FULL`: vendors, mentors, allies, training dummies
- `CORRUPTED`: vendors disappear, mentor dialogue shifts, prices rise
- `EMPTY`: only Siren NPC remains

**Persistence:** `HubStateMachine.toMap()` stored as JSONB in `player_progress.hub_state`. Loaded on connect.

**Files to create:** `world/HubState.java`, `world/HubStateMachine.java`

**Files to modify:** `world/HubRegistry.java`, `network/WorldSnapshot.java`, `server/ZoneSimulationLoop.java`, `server/InventoryRepository.java` (add `player_progress` table), `client/game/StoryManager.java`

---

### 3.6 Narrative Act FSM (GDD §5)

```java
// client/src/main/java/com/indieniinja/client/game/Act.java
public enum Act {
    ACT_I_RISE       (1.0f, 1.0f),  // (lanternDefault, hudAlpha)
    ACT_II_FALL      (0.6f, 1.0f),
    ACT_III_LABYRINTH(0.4f, 0.8f),
    ACT_IV_BREAK     (0.2f, 0.1f),  // near-invisible HUD, heavy world
    ACT_V_HEARTH     (0.5f, 0.7f),
    ACT_VI_ASCENT    (0.7f, 1.0f),
    ACT_VII_UPPER    (1.0f, 1.0f);

    public final float lanternDefault;
    public final float hudAlpha;
}
```

Transitions driven by: boss defeats, fragment milestones, hub state changes.

**Act IV depression mechanics** (GDD §5):
- `hudAlpha = 0.1f` → near-invisible HUD
- Gravity multiplier `0.7×` — `PlayerState` carries `gravityMult`; `PhysicsSystem` applies it
- Dash disabled, jump reduced — gated via `AbilityComponent`
- Act V: gradual mechanical restoration

**Files to create:** `client/game/Act.java`

**Files to modify:** `client/game/StoryManager.java`, `client/rendering/HudRenderer.java`, `network/PlayerState.java` (add `gravityMult`), `sim/GameSimulator.java`

---

### 3.7 Boss AI — Psychological Patterns (GDD §7)

**Note from history:** Boss tuning required 5 successive commits in the Python phase. Design for iteration, not perfection. Ship a working FSM first, tune in follow-up commits.

| Boss | Act | Psychological theme | Core mechanic |
|------|-----|--------------------|--------------||
| Siren of the Veiled Vale | II | Scripted loss | Invincible; triggers on dialogue end; strips Yin/Yang to 0 |
| Echo Warden | III | Self-doubt | Mirrors player movement with 0.5 s delay; walks into hazards if player stops |
| Time Leech Lord | IV | Burnout | Drains Lantern each tick; spawns `TIME_LEECH` enemies; speed burst at 30% HP |
| Memory Eater | VI | Identity loss | Resets platform positions each phase; erases DOOR_LOCKED unlocks |

**Siren:** Not a traditional fight. Server sends new `SCRIPTED_LOSS` `MessageType` when Siren's dialogue sequence completes. Server sets `yin = 0`, `yang = 0` on `YinYangComponent`, calls `HubStateMachine.onBossDefeated("siren")` → hub transitions to `EMPTY`.

**Files to modify:** `sim/SimBoss.java`, `sim/BossAIState.java`, new `sim/BossPatternLibrary.java`, `network/MessageType.java`

---

### 3.8 Echo System (GDD §6)

```java
// core/src/main/java/com/indieniinja/sim/EchoRecorder.java
// 10-second (600-tick) ring buffer of InputCommand per SimPlayer.
public final class EchoRecorder {
    private static final int BUFFER = 600;
    private final InputCommand[] ring = new InputCommand[BUFFER];
    private int head = 0;
    public void record(InputCommand cmd) { ring[head++ % BUFFER] = cmd; }
    public List<InputCommand> snapshot() { /* ordered copy */ }
}

// core/src/main/java/com/indieniinja/sim/SimEcho.java
// Driven by ReplayPlayer (already exists), not InputCommand.
// recallable flag: recalling before echo completes its role fails the puzzle.
```

`WorldSnapshot` gains `echoes` list. `EntityPlanner` places echo trigger zones in PUZZLE rooms.

---

### 3.9 Proof Token Mechanic (Act III — GDD §5)

- New item: `"proof_token"` (type `key_item`, non-consumable)
- New `AbilityGate` variant: `TOKEN_GATE(n)` — requires N tokens
- New `RoomType.LABYRINTH` — Act III room archetype
- At `yin < 0.5f`: some PLATFORM tiles rendered as AIR in Act III rooms (intentionally "unfair" — server physics unchanged)

---

## 4. File Creation Checklist

Files that must be created (none currently exist):

```
core/src/main/java/com/indieniinja/
├── world/
│   ├── HubState.java
│   └── HubStateMachine.java
└── sim/
    ├── YinYangComponent.java
    ├── LanternComponent.java
    ├── SimEcho.java
    └── EchoRecorder.java

client/src/main/java/com/indieniinja/client/game/
└── Act.java
```

Files requiring significant modification:

```
core/src/main/java/com/indieniinja/
├── network/
│   ├── PlayerState.java          ← yinValue, yangValue, lanternValue, flowMode, gravityMult
│   └── WorldSnapshot.java        ← hubState, echoes; SCHEMA_VERSION → 2
├── world/
│   ├── WorldGraph.java           ← RoomType.LABYRINTH
│   └── HubRegistry.java          ← store HubStateMachine per hub
├── sim/
│   ├── GameSimulator.java         ← Yin/Yang, Lantern, Echo ticking, gravityMult
│   ├── SimBoss.java               ← 4 boss behavioral patterns
│   └── ItemDatabase.java          ← yin/yang/lantern fragments, proof_token
└── physics/
    ├── PhysicsConstants.java      ← ABILITY_YIN_SIGHT flag constant
    └── CollisionSystem.java       ← ABILITY_YIN_SIGHT hidden platform check

server/src/main/java/com/indieniinja/server/
├── ZoneSimulationLoop.java       ← hub state machine ticking, NPC spawn/despawn
├── InventoryRepository.java      ← player_progress table
└── (WorldGraphRepository — no changes needed)

client/src/main/java/com/indieniinja/client/
├── GameScreen.java               ← offline/solo mode path
├── game/StoryManager.java        ← Act FSM
├── rendering/HudRenderer.java    ← Yin/Yang bar, Lantern meter, act-alpha
├── rendering/ChunkRenderer.java  ← vignette
└── rendering/EntityRenderer.java ← hidden platform reveal pass
```

---

## 5. Milestone Plan

Commit prefix convention: `feat(m1):`, `feat(m2):`, etc. — mirrors the Loop system from the Java rebuild sprint.

---

### Milestone 1 — Foundation Close (v0.11.0)
*Fix the two remaining test gaps and the version chaos before anything else.*

- [x] `CollisionEdgeCaseTest`: `lava_upwardContactSetsOnLavaFlag` (`lavaCeilingSetsOnLavaFlag`)
- [x] `CollisionEdgeCaseTest`: `dash_speed_doesNotTunnelThinWall` (`wallStopsEntityAtDashSpeed`)
- [x] Fix `version.json` → `0.10.83`, `build.gradle.kts` → `0.10.83`
- [x] Fix `NET-1`: remove `zone.spawnX != 0` fallback in `ZoneSimulationLoop` (grid-0,0 spawn was silently wrong)

**Deliverable:** Physics is regression-proof. Version numbers are honest. No known correctness bugs.

---

### Milestone 2 — In-Process Solo Mode (v0.11.0, same release)
*The entire game must be playable without a running server.*

- [x] `ModeSelectScreen`: add "Solo" option (4th card, purple, passes `"solo"` gameMode)
- [x] `GameScreen`: offline path — local `GameSimulator`, no `NetworkClientThread`
- [x] Input fed directly to local sim via `sim.step(Map.of(0, cmd))`; `WorldSnapshot` pushed to `GameStateBuffer`
- [x] Solo and multiplayer share the same rendering pipeline (single-room tile fallback + `stampSoloFields`)

**Deliverable:** Can start a game with no server. Multiplayer remains unchanged.

---

### Milestone 3 — Hub Evolution (v0.11.1)
*The hub breathes. NPCs appear and disappear. Acts I–II are playable.*

- [x] `HubState.java` + `HubStateMachine.java`
- [x] `HubStateMachine` stored per `ZoneInstance`; server ticks FSM at 1 Hz in `ZoneSimulationLoop`
- [x] `SimNPC` spawned/despawned via `GameSimulator.addNpc/removeNpc` driven by `activeNpcTypes()`
- [x] `WorldSnapshot.hubState` field
- [x] `Act.java` FSM — Acts I–VI wired (hub state transition triggers act change)
- [x] `StoryManager` reads `hubState` → drives act FSM; `GameScreen` wires it on every snapshot
- [x] Hub 1 (Bamboo Courtyard): FULL / CORRUPTED / EMPTY roster; Hub 2: FRACTURED / RECOVERING / WHOLE
- [x] `player_progress` table with `hub_state JSONB` column (persisted on zone leave)

**Deliverable:** Playable Acts I–II. Enter full hub, watch it corrupt, Siren trigger, hub collapses.

---

### Milestone 4 — Yin/Yang & Lantern (v0.11.2)
*The core emotional mechanics are functional and visible.*

- [ ] `YinYangComponent` (server + client effects)
- [ ] `LanternComponent` (server decay/restore + client vignette)
- [ ] `PlayerState` + `WorldSnapshot` updated (SCHEMA_VERSION → 2)
- [ ] `HudRenderer` Yin/Yang bar + Lantern meter (replace stubs)
- [ ] `ChunkRenderer` vignette
- [ ] `EntityRenderer` hidden platform reveal pass (Yin > 0.7)
- [ ] Fragment items in `ItemDatabase` + placed by `EntityPlanner`
- [ ] Siren: scripted loss → Yin/Yang → 0 → hub state → EMPTY

**Deliverable:** Collecting a fragment visibly changes the world. Low Lantern feels oppressive. Siren encounter is mechanically complete.

---

### Milestone 5 — Boss AI (v0.11.3)
*Four bosses, each with a distinct psychological pattern. Ship working FSMs first, tune after.*

- [ ] Echo Warden: mirror-movement with 0.5 s delay (`EchoRecorder` already exists for this)
- [ ] Time Leech Lord: Lantern drain + enemy spawns + speed burst at 30% HP
- [ ] Memory Eater: platform reset per phase + `SpatialHash.remove()` on door unlocks
- [ ] Siren: `SCRIPTED_LOSS` MessageType + client collapse animation
- [ ] Each boss defeat → fragment drop → `HubStateMachine.onBossDefeated()` → act advance

**Deliverable:** Acts I–VI each have a boss encounter. Expect tuning commits after first playtest.

---

### Milestone 6 — Echo System & Puzzles (v0.11.4)
*Solo play feels co-op through echoes. Puzzle rooms are distinct.*

- [ ] `EchoRecorder` (600-tick ring buffer on `SimPlayer`)
- [ ] `SimEcho` (`ReplayPlayer`-driven, `recallable` flag)
- [ ] Echo trigger zones placed by `EntityPlanner` in PUZZLE rooms
- [ ] Puzzle archetype: **Asymmetric Ability Lock** (echo holds position)
- [ ] Puzzle archetype: **Simultaneous Timing** (echo replicates past actions)
- [ ] Proof token mechanic (`RoomType.LABYRINTH`, `TOKEN_GATE`)
- [ ] `ValidationLayer` verifies all puzzles solvable with current ability set

**Deliverable:** Puzzle rooms are mechanically interesting solo. Act III "unfair" platforms work.

---

### Milestone 7 — Act IV & Narrative Arc (v0.11.5)
*The 7-act emotional arc is playable end-to-end.*

- [ ] Full `Act.java` FSM — all 7 acts with `hudAlpha` and `lanternDefault`
- [ ] `HudRenderer` alpha driven by `currentAct.hudAlpha` (Act IV → 0.1)
- [ ] `gravityMult` on `PlayerState`; `PhysicsSystem` applies it (Act IV → 0.7×)
- [ ] Dash/jump restricted in Act IV
- [ ] Act V: gradual mechanical restoration per tick
- [ ] Act VII: full abilities, full HUD, complete hub
- [ ] Hub 2 (Chasm of Still Shadows): FRACTURED → RECOVERING → WHOLE wired

**Deliverable:** A player can experience the full emotional arc from Act I through Act VII in one session.

---

### Milestone 8 — Polish (v0.11.6+)

- [ ] Music / BGM hooks (Lantern-dynamic music system)
- [ ] Gamepad support (`InputPoller` extension)
- [ ] Act-based palette shifts and fog density in `ChunkRenderer`
- [ ] New game+ (remixed hub progression)
- [ ] Alternate endings based on Yin/Yang balance at Act VII
- [ ] Fix `version.json`, `build.gradle.kts`, and `README.md` in sync after each release

---

## 6. Design Decisions

| Question | Decision |
|----------|----------|
| Solo mode | `GameScreen` offline path: local `GameSimulator`, no socket. Toggle via `ModeSelectScreen`. |
| Co-op Yin/Yang | Each player has own Yin/Yang. Flow Mode requires both balanced. Zone Lantern = average. |
| Hub state persistence | `HubStateMachine.toMap()` in `player_progress.hub_state JSONB`. Loaded on connect. |
| Siren encounter | Not a traditional fight. `SCRIPTED_LOSS` message sent when dialogue completes. |
| Act III hidden platforms | Server treats tiles as PLATFORM (authoritative). Client hides sprite when `yin < 0.5f`. Intentional. |
| Echo moral tension | `recallable` flag. Recalling before completion fails the puzzle. Player chooses. |
| SCHEMA_VERSION timing | Increment to 2 when Milestone 4 fields land. Bundle all new `PlayerState` fields in one bump. |
| Commit prefix | `feat(m1):`, `feat(m2):` etc. — mirrors Loop system, maintains git traceability. |
| Version discipline | After every milestone release: `version.json`, `build.gradle.kts`, and `README.md` must match. |

---

## 7. Success Criteria

Complete when a player can, in a single session:

1. Start solo mode with no server
2. Play Act I in the Bamboo Courtyard with the full NPC roster
3. Collect a Yin fragment — watch hidden platforms materialise
4. Collect a Yang fragment — watch attack strength increase
5. Encounter the Siren, lose in a scripted sequence, watch the hub collapse
6. Enter Hub 2 (Chasm of Still Shadows) and watch NPCs return through Acts III–V
7. Solve a puzzle room using an echo of their own past movement
8. Collect enough fragments in Act VI to trigger Flow Mode
9. Reach Act VII with full abilities, a populated final hub
10. Receive a narrative resolution that was felt, not told

---

*Living document. Update milestone checkboxes as work progresses. Archive completed milestones to `docs/archive/`.*
