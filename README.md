# Shadow Ascent: The Hollowed Ninja

**Vain Asher Gaming** — A narrative-driven single-player Metroidvania. A hollowed ninja climbs a fractured spirit world across seven acts, guided by Yin/Yang emotional mechanics and a hub that breathes, corrupts, and recovers.

> Version: **v0.12.08** | Status: External playtest ready | Platform: Windows | Engine: Java 21 + libGDX + Netty

---

## Repository Architecture

```
VainAsher/indie-ninja-launcher   (PUBLIC)  — Launcher .exe, player guides, GitHub Pages
VainAsher/indie-ninja-adventures (PRIVATE) — Game source, CI/CD, build pipeline  ← you are here
VainAsher/indie-ninja-feedback   (PUBLIC)  — Bug reports, feature requests, feedback
VainAsher/indie-ninja-pipeline   (PRIVATE) — Dev triage, sprint planning, release management
```

---

## What's in v0.12.08 (Yin/Yang stance movement + duality prototype)

- Dash no longer sticks or tunnels up wall faces: `isDashing` is now cleared on wall contact, preventing the next frame from re-applying dash velocity after `CollisionSystem` has zeroed it. (feedback#4)

| System | Status |
| ------ | ------ |
| ECS (`EntityManager`, `EventBus`, lifecycle listeners) | Done |
| Physics + collision (AABB swept, SpatialHash, raycast API) | Done |
| Player mechanics (move/jump/dash/crouch/wall/combat, ability flags) | Done |
| Procedural world generation (7 biomes, back-edges, Metroidvania loops) | Done |
| World graph + room post-processor (AbilityLayer, PuzzleLayer, EntityPlanner) | Done |
| Authoritative server (Netty, 60 Hz, zone simulation loop) | Done |
| Delta encoding + schema versioning + frameHash desync detection | Done |
| Inventory + crafting (DB-backed, Redis cache, ability items) | Done |
| PostgreSQL persistence (HikariCP + Jackson; world graph, inventory) | Done |
| Redis zone state cache + room tile cache + item cache | Done |
| Input recording + deterministic replay (`InputRecorder`/`ReplayPlayer`) | Done |
| libGDX rendering pipeline (chunk, entity, HUD renderers) | Done |
| Dialogue + missions + story manager stubs | Done |
| 13 test files (physics, world gen, inventory, networking, collision edge cases) | Done |
| Solo/offline mode (no server required) | Milestone 2 — next |
| Yin/Yang + Lantern emotional mechanics | Milestone 4 |
| Hub evolution state machine (FSM, NPC presence) | Milestone 3 |
| Narrative Act FSM (7 acts, Act IV depression mechanics) | Milestone 7 |
| Boss AI psychological patterns (Siren, Echo Warden, Time Leech, Memory Eater) | Milestone 5 |

---

## Quick Start (Dev)

**Prerequisites:** Java 21, Gradle 8.7

```bash
git clone https://github.com/VainAsher/indie-ninja-adventures.git
cd indie-ninja-adventures/java

# Build fat JARs
./gradlew buildAll

# Run server
java -jar ../ninja-server-all.jar

# Run client
java -jar ../ninja-client-all.jar

# Run all tests
./gradlew test
```

---

## Project Structure

```
indie-ninja-adventures/
├── java/
│   ├── core/       Shared ECS, physics, world gen, network types, inventory
│   ├── server/     Netty authoritative server, zone sim loop, persistence
│   └── client/     libGDX desktop client, rendering, UI, dialogue, missions
├── docs/
│   ├── CURRENT_STATE.md         Canonical runtime/handover state
│   ├── INDEX.md                 Canonical documentation index
│   ├── plans/implementing/PLAN_SHADOW_ASCENT.md   Active implementation plan
│   ├── ROADMAP.md              Milestone plan
│   ├── CHANGELOG.md            Version history
│   └── dev/
│       └── JAVA_ARCHITECTURE.md  Comprehensive codebase reference
├── version.json    Single version source of truth
└── README.md
```

---

## Documentation

- [docs/INDEX.md](docs/INDEX.md) — canonical documentation routing
- [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md) — runtime/handover truth
- [docs/plans/implementing/PLAN_SHADOW_ASCENT.md](docs/plans/implementing/PLAN_SHADOW_ASCENT.md) — GDD alignment plan and milestone checklist
- [docs/ROADMAP.md](docs/ROADMAP.md) — Milestone plan with deliverables
- [docs/CHANGELOG.md](docs/CHANGELOG.md) — Version history
- [docs/RELEASE_VERSION_SYNC_CHECKLIST.md](docs/RELEASE_VERSION_SYNC_CHECKLIST.md) — Release metadata parity gate
- [docs/dev/JAVA_ARCHITECTURE.md](docs/dev/JAVA_ARCHITECTURE.md) — Full codebase reference (v0.11.34+)

---

## Versioning

Single source of truth: [`version.json`](version.json)

```json
{
  "version": "0.12.07",
  "build": "production",
  "build_date": "2026-04-24",
  "min_launcher_version": "1.1.0"
}
```

---

## Tech Stack

| Component | Choice |
| --------- | ------ |
| Language | Java 21 |
| Client | libGDX (desktop, OpenGL) |
| Server | Netty (authoritative, 60 Hz) |
| Protocol | msgpack + delta encoding |
| Persistence | PostgreSQL (HikariCP + Jackson) |
| Cache | Redis |
| Build | Gradle 8.7 multi-module |
| Testing | JUnit 5 + AssertJ |

---

## License

MIT — see LICENSE file.

**Vain Asher Gaming** | [Feedback](https://github.com/VainAsher/indie-ninja-feedback) | [Launcher](https://github.com/VainAsher/indie-ninja-launcher)
