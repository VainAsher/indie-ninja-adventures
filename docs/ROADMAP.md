---
doc_type: roadmap
status: living
owner: core-team
last_updated: 2026-04-24
version_anchor: v0.12.08
---
# Development Roadmap

Vain Asher Gaming's: **Shadow Ascent: The Hollowed Ninja**

Last Updated: 2026-04-24 | Version: v0.12.08 | Platform: Java 21 + libGDX + Netty

---

## Vision

A narrative-driven single-player Metroidvania where a hollowed ninja climbs a fractured spirit world.  
Seven acts. Four bosses. Yin/Yang emotional mechanics. A hub that breathes, corrupts, and recovers.  
Optional co-op overlay once single-player is complete.

---

## Technology (as of v0.12.06)

The project completed a full Java rewrite in 6 days (Apr 4â€“10 2026). The Python prototype (v0.7â€“v0.9) proved the game loop and is archived. All active development is on the Java stack.

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

## Milestone 1 â€” Foundation Close (v0.10.84) âœ… COMPLETE

*Physics regression-proof. Version numbers honest. No known correctness bugs.*

- [x] `CollisionEdgeCaseTest`: lava ceiling contact + swept tunnel prevention
- [x] `version.json` and `build.gradle.kts` in sync at v0.10.83 / v0.10.84
- [x] NET-1: removed `zone.spawnX != 0` fallback (grid-0,0 rooms no longer spawn at wrong position)

---

## Milestone 2 â€” In-Process Solo Mode (v0.11.0) ðŸ”¶ NEXT

*Entire game playable without a running server.*

- [ ] `ModeSelectScreen`: add "Solo" option
- [ ] `GameScreen`: offline path â€” local `GameSimulator`, no `NetworkClientThread`
- [ ] Input feeds directly to local `sim.step()` each render frame
- [ ] `WorldSnapshot` assembled locally; same rendering pipeline as multiplayer

**Deliverable:** Can start a game with no server. Multiplayer untouched.

---

## Milestone 3 â€” Hub Evolution (v0.11.1)

*The hub breathes. NPCs appear and disappear. Acts Iâ€“II playable.*

- [ ] `HubState.java` + `HubStateMachine.java`
- [ ] `HubRegistry` stores `HubStateMachine` per hub; NPC presence driven by `activeNpcIds()`
- [ ] `WorldSnapshot.hubState` field; `Act.java` FSM (Acts Iâ€“II)
- [ ] Hub 1 (Bamboo Courtyard): FULL / CORRUPTED / EMPTY with NPC rosters
- [ ] `player_progress` table with `hub_state JSONB`

---

## Milestone 4 â€” Yin/Yang & Lantern (v0.11.2)

*Core emotional mechanics functional and visible.*

- [ ] `YinYangComponent` + `LanternComponent` (server effects + client rendering)
- [ ] `HudRenderer` Yin/Yang bar + Lantern meter
- [ ] `ChunkRenderer` vignette; `EntityRenderer` hidden-platform reveal pass
- [ ] Fragment items placed by `EntityPlanner`; Siren scripted-loss wired

---

## Milestone 5 â€” Boss AI (v0.11.3)

*Four bosses with distinct psychological patterns.*

- [ ] Siren of the Veiled Vale: `SCRIPTED_LOSS` â†’ Yin/Yang â†’ 0 â†’ hub EMPTY
- [ ] Echo Warden: mirror movement 0.5 s delay
- [ ] Time Leech Lord: Lantern drain + speed burst
- [ ] Memory Eater: platform reset + door unlock erasure

---

## Milestone 6 â€” Echo System & Puzzles (v0.11.4)

*Solo play feels co-op through echoes.*

- [ ] `EchoRecorder` (600-tick ring buffer) + `SimEcho` (`ReplayPlayer`-driven)
- [ ] Puzzle archetypes: Asymmetric Ability Lock, Simultaneous Timing
- [ ] Proof token mechanic (`RoomType.LABYRINTH`, `TOKEN_GATE`)

---

## Milestone 7 â€” Full Narrative Arc (v0.11.5)

*7-act emotional arc playable end-to-end.*

- [ ] Full `Act.java` FSM â€” all 7 acts with `hudAlpha` and `lanternDefault`
- [ ] Act IV: near-invisible HUD, 0.7Ã— gravity, restricted movement
- [ ] Act V: gradual mechanical restoration
- [ ] Hub 2 (Chasm of Still Shadows): FRACTURED â†’ RECOVERING â†’ WHOLE

---

## Milestone 8 â€” Polish (v0.11.6+)

- [ ] Music / BGM (Lantern-dynamic)
- [ ] Gamepad support (`InputPoller` extension)
- [ ] Act-based palette shifts and fog density
- [ ] New game+ (remixed hub progression)
- [ ] Alternate endings based on Yin/Yang balance at Act VII

---

## Success Criteria

A player can, in a single session:

1. Start solo mode with no server
2. Play Act I in the Bamboo Courtyard (full NPC roster)
3. Collect a Yin fragment â€” hidden platforms materialise
4. Encounter the Siren â€” scripted loss, hub collapses
5. Solve a puzzle room using an echo of their past movement
6. Reach Act VII with full abilities and a populated final hub
7. Receive a narrative resolution that was felt, not told

---

Full GDD alignment plan: [docs/plans/implementing/PLAN_SHADOW_ASCENT.md](plans/implementing/PLAN_SHADOW_ASCENT.md)
