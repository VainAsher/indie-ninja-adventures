---
doc_type: roadmap
status: living
owner: core-team
last_updated: 2026-04-28
version_anchor: v0.12.11
---
# Development Roadmap

Vain Asher Gaming's: **Shadow Ascent: The Hollowed Ninja**

Last Updated: 2026-04-28 | Version: v0.12.11 | Platform: Java 21 + libGDX + Netty

---

## Vision

A narrative-driven single-player Metroidvania where a hollowed ninja climbs a fractured spirit world.  
Seven acts. Four bosses. Yin/Yang emotional mechanics. A hub that breathes, corrupts, and recovers.  
Optional co-op overlay once single-player is complete.

---

## Technology (as of v0.12.06)

The project completed a full Java rewrite in 6 days (Apr 4-10 2026). The Python prototype (v0.7-v0.9) proved the game loop and is archived. All active development is on the Java stack.

| Component | Choice |
| --------- | ------ |
| Language | Java 21 |
| Client | libGDX (desktop, OpenGL) |
| Server | Netty (authoritative, 60 Hz) |
| ECS | Custom (`EntityManager`, `EventBus`) |
| Physics | Custom AABB swept, `SpatialHash` |
| Protocol | msgpack + `WireCodec` + delta encoding |
| Persistence | PostgreSQL (HikariCP + Jackson JSONB) |
| Cache | Redis (zone state, room tiles, items) |
| Build | Gradle multi-module (`:core`/`:server`/`:client`) |
| Tests | JUnit 5 + AssertJ (13 test files) |

Architecture reference: [docs/dev/JAVA_ARCHITECTURE.md](dev/JAVA_ARCHITECTURE.md)

---

## Milestone 1 -- Foundation Close (v0.10.84) COMPLETE

*Physics regression-proof. Version numbers honest. No known correctness bugs.*

- [x] `CollisionEdgeCaseTest`: lava ceiling contact + swept tunnel prevention
- [x] `version.json` and `build.gradle.kts` in sync at v0.10.83 / v0.10.84
- [x] NET-1: removed `zone.spawnX != 0` fallback (grid-0,0 rooms no longer spawn at wrong position)

---

## Milestone 2 -- In-Process Solo Mode (v0.11.0) COMPLETE

*Entire game playable without a running server.*

- [x] `ModeSelectScreen`: CAMPAIGN card maps to "solo" game mode ID
- [x] `GameScreen`: offline path -- local `GameSimulator`, no `NetworkClientThread`
- [x] Input feeds directly to local `sim.step()` each render frame
- [x] `WorldSnapshot` assembled locally; same rendering pipeline as multiplayer

**Deliverable:** Can start a game with no server. Multiplayer untouched.

---

## Milestone 3 -- Hub Evolution (v0.11.1) COMPLETE

*The hub breathes. NPCs appear and disappear. Acts I-II playable.*

- [x] `HubState.java` + `HubStateMachine.java`
- [x] `HubRegistry` stores hub definitions; NPC presence driven by `activeNpcTypes()`
- [x] `WorldSnapshot.hubState` field; `Act.java` FSM (Acts I-II, all 7 acts defined)
- [x] Hub 1 (Bamboo Courtyard): FULL / CORRUPTED / EMPTY with NPC rosters
- [x] `player_progress` persistence via `SaveManager` (multi-slot, JSONB-backed)

---

## Milestone 4 -- Yin/Yang & Lantern (v0.11.2) COMPLETE

*Core emotional mechanics functional and visible.*

- [x] `YinYangComponent` + `LanternComponent` (server effects + client rendering)
- [x] `HudRenderer` Yin/Yang balance bar + Lantern meter
- [x] `ChunkRenderer` Lantern vignette overlay
- [x] Fragment items placed by `EntityPlanner`; Siren scripted-loss wired
- [ ] `EntityRenderer` hidden-platform reveal pass (ghosted tiles on high Yin balance)

---

## Milestone 5 -- Boss AI (v0.11.3) COMPLETE

*Four bosses with distinct psychological patterns.*

- [x] Siren of the Veiled Vale: `ScriptedLossPattern` -- Yin/Yang -> 0 -> hub EMPTY
- [x] Echo Warden: `EchoMirrorPattern` -- mirror movement 0.5 s delay
- [x] Time Leech Lord: `LanternDrainPattern` -- Lantern drain + speed burst
- [x] Memory Eater: `PhaseResetPattern` -- platform reset + door unlock erasure

---

## Milestone 6 -- Echo System & Puzzles (v0.11.4) IN PROGRESS

*Solo play feels co-op through echoes.*

- [x] `EchoRecorder` (600-tick ring buffer) + `SimEcho` (`ReplayPlayer`-driven)
- [x] Echo puzzle type: `PuzzleType.ECHO_TRIGGER` -- interact trigger spawns echo, unlocks echo door
- [ ] Puzzle archetypes: Asymmetric Ability Lock, Simultaneous Timing (named archetypes)
- [ ] Proof token mechanic (`RoomType.LABYRINTH`, `TOKEN_GATE` entity placed by `EntityPlanner`)

---

## Milestone 7 -- Full Narrative Arc (v0.11.5) IN PROGRESS

*7-act emotional arc playable end-to-end.*

- [x] Full `Act.java` FSM -- all 7 acts with `hudAlpha` and `lanternDefault`
- [x] Act IV: near-invisible HUD (`hudAlpha` = 0.1f)
- [x] Hub 2 (Chasm of Still Shadows): FRACTURED -> RECOVERING -> WHOLE (in `HubStateMachine`)
- [ ] Act IV: 0.7x gravity modifier + restricted movement (not yet applied by `GameSimulator`)
- [ ] Act V: gradual mechanical restoration (abilities returned incrementally per act transition)

---

## Milestone 8 -- Polish (v0.11.6+)

- [x] Music / BGM stub (`MusicManager`)
- [x] Act-based palette shifts and fog density -- Visual World System S0-S4 complete
- [ ] Music dynamic system (Lantern-reactive BGM crossfade)
- [ ] Gamepad support (`InputPoller` extension)
- [ ] New game+ (remixed hub progression)
- [ ] Alternate endings based on Yin/Yang balance at Act VII

---

## Success Criteria

A player can, in a single session:

1. Start solo mode with no server
2. Play Act I in the Bamboo Courtyard (full NPC roster)
3. Collect a Yin fragment -- hidden platforms materialise
4. Encounter the Siren -- scripted loss, hub collapses
5. Solve a puzzle room using an echo of their past movement
6. Reach Act VII with full abilities and a populated final hub
7. Receive a narrative resolution that was felt, not told

---

Full GDD alignment plan: [docs/plans/implementing/PLAN_SHADOW_ASCENT.md](plans/implementing/PLAN_SHADOW_ASCENT.md)
