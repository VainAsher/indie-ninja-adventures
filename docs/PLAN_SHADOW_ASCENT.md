# PLAN — Shadow Ascent: The Hollowed Ninja
## GDD Alignment & Implementation Roadmap
**Created:** 2026-04-10 | **Last updated:** 2026-04-13 21:37:26 +01:00 | **Codebase version:** v0.11.27 | **Next release target:** v0.11.28 (M6 echo trigger zones + puzzle hooks)

---

## 0A. Feedback Workloop Operating Model (Mandatory)

This plan now uses the Implementation Work Loop from:
`C:\Users\asher\.claude\projects\c--Users-asher-Vain-Asher-Gaming\memory\feedback_work_loop.md`

Every implementation cycle must follow this exact order:

| Step | Action | Required artifact |
|------|--------|-------------------|
| 1 | Review plan and current phase state | Plan status read and acknowledged in work notes |
| 2 | Create phase-specific todo list | Todo list mapped to current plan IDs |
| 3 | Execute tasks one by one | Task state moved to done in checklist/todo |
| 4 | Commit after each logical unit | Detailed commit message with plan ID references |
| 5 | Update plan | Completed items marked, decisions and next step captured |
| 6 | Push to remote | Branch updated on GitHub |
| 7 | Loop | Start next cycle from step 1 |

### Workloop rules

- Never batch all work into one end-of-day commit.
- Every meaningful implementation unit must map to at least one checklist ID below.
- Commit messages should include: `plan_id`, `scope`, `reason`, `risk`.
- Plan updates happen each loop, not only at milestone boundaries.
- Unknown scope discovered mid-loop becomes a new checklist row, not ad-hoc drift.
- All plan updates and loop notes must use full timestamps: `YYYY-MM-DD HH:mm:ss ±HH:MM` (not date-only).

### Branch and commit format

- Branch naming: `feature/shadow-ascent-<phase>-<topic>`
- Commit subject format: `<type>(<plan_id>): <summary>`
- Commit body template:
  - `What changed`
  - `Why now`
  - `Risks`
  - `Validation`
  - `Next checklist item`

### Status legend

- `[ ]` Not started
- `[~]` In progress
- `[x]` Done
- `[!]` Blocked

---

## 0B. Execution-Ordered Checklist (P0/P1/P2)

### Sprint map

- `S1-S4`: P0 (ship blockers)
- `S5-S9`: P1 (balance, tuning, content throughput)
- `S10-S14`: P2 (release hardening and full release)

Owner roles:

- `ENG-CORE`: Core sim/physics/systems
- `ENG-CLIENT`: Client/UI/rendering/input/save UX
- `ENG-NET`: Protocol/server/client message flow
- `ENG-DATA`: Missions/dialogue/items/data validation
- `DESIGN`: Balance, pacing, playtest interpretation
- `QA`: Test plans/regression/verification
- `PROD`: Planning, release process, dependency tracking

---

## P0 - Core Campaign Loop Stabilization

Goal: make campaign progression complete, testable, and safe to iterate.

| Status | ID | Task | Owner | Sprint | Depends on | Deliverable | Balance / ideation hook | Exit gate |
|--------|----|------|-------|--------|------------|-------------|--------------------------|-----------|
| [ ] | P0-01 | Restore build/test baseline (fix Gradle wrapper path, ensure `./gradlew.bat test` works) | ENG-CORE + QA | S1 | None | Reproducible local test command and CI run | Enables rapid tuning safely | All existing tests run from clean checkout |
| [ ] | P0-02 | Mission objective integration for all objective types (`collect_items`, `activate_switches`, `reach_location`, `time_challenge`, `defeat_boss`, `kill_all_enemies`) | ENG-CLIENT + ENG-CORE | S1 | P0-01 | Objective event adapters and mission progress hooks | Exposes full mission pacing for tuning | 30/30 missions can progress objectives in playtest harness |
| [ ] | P0-03 | Mission completion and exit-lock behavior wiring | ENG-CLIENT | S1 | P0-02 | Mission completion trigger + unlock/lock lifecycle | Supports mission difficulty tuning | Mission state transitions pass lifecycle test matrix |
| [ ] | P0-04 | Dialogue event routing parity (handle all emitted events or remove dead authored events) | ENG-DATA + ENG-CLIENT | S1-S2 | P0-02 | Event router map + unknown-event telemetry | Enables narrative pacing experiments | Zero silent event drops in dialogue lint output |
| [ ] | P0-05 | Save/load parity hardening (active mission restore, story-act clamp fix, full liveData restore symmetry) | ENG-CLIENT + ENG-CORE | S2 | P0-03 | Migration rules + roundtrip integrity tests | Preserves tuning experiments across sessions | Save/load roundtrip loses no critical progression fields |
| [ ] | P0-06 | Scripted-loss full network pipeline (`GameSimulator` emit -> server broadcast -> client handling -> story/hub consequences) | ENG-NET + ENG-CLIENT | S2 | P0-04, P0-05 | End-to-end scripted-loss flow in MP and solo | Stabilizes narrative boss balancing | Siren sequence completes with consistent state transitions |
| [ ] | P0-07 | Mission/item contract normalization (canonical IDs, reward/item schema checks) | ENG-DATA | S2-S3 | P0-02 | Validation script and cleaned mission data | Prevents fake rewards and invalid progression tuning data | Zero missing mission-referenced item IDs |
| [ ] | P0-08 | Version/document source-of-truth consolidation (`version.json`, build file, README/changelog sync policy) | PROD + ENG-CORE | S3 | P0-01 | Release metadata sync checklist | Keeps test/balance results attributable to exact build | One authoritative version source reflected in all release docs |
| [ ] | P0-09 | Critical integration test suite for campaign loop (mission start/progress/complete, save/load, dialogue events, scripted-loss) | QA + ENG-CORE | S3-S4 | P0-06, P0-07 | Regression suite with pass/fail report | Locks in baseline before heavy balance iteration | Green suite in CI for all P0 critical flows |
| [ ] | P0-10 | P0 signoff playtest pack and blocker triage | DESIGN + QA + PROD | S4 | P0-09 | Structured playtest report with blocker decisions | Establishes tuning baseline for P1 | No open P0 blockers and approved handoff to P1 |

---

## P1 - Balance, Tuning, and Content Throughput

Goal: make gameplay feel coherent and tunable while increasing mission/story output safely.

| Status | ID | Task | Owner | Sprint | Depends on | Deliverable | Balance / ideation hook | Exit gate |
|--------|----|------|-------|--------|------------|-------------|--------------------------|-----------|
| [ ] | P1-01 | Data-driven tuning layer (movement/combat/economy/mission timing/boss parameters) | ENG-CORE + ENG-DATA | S5 | P0-10 | Config-driven tuning files and loader | Fast hypothesis testing without code churn | Core balance constants removed from hardcoded logic path |
| [ ] | P1-02 | Telemetry instrumentation (mission fail reasons, death causes, DPS in/out, completion times, economy curves) | ENG-CORE + ENG-CLIENT | S5 | P1-01 | Session telemetry logs and aggregation scripts | Quantifies tuning changes | Every playtest produces comparable metrics bundle |
| [ ] | P1-03 | Balance dashboard and target bands | DESIGN + QA | S5-S6 | P1-02 | KPI sheet with min/max target bands | Converts feel goals into measurable thresholds | Targets defined for TTK, fail-rate, mission duration, resource pressure |
| [ ] | P1-04 | Weekly balance loop (hypothesis -> change -> playtest -> metrics review -> decision log) | DESIGN + ENG-CORE | S6-S9 (recurring) | P1-03 | Weekly balance notes linked to commits | Structured ideation and tuning rhythm | 4 consecutive loops completed with logged decisions |
| [ ] | P1-05 | Story pacing pass (mission unlock cadence, act transition timing, hub evolution rhythm) | DESIGN + ENG-DATA | S6-S7 | P1-02 | Progression pacing matrix | Supports narrative ideation against measurable flow | No dead-end progression in scripted path tests |
| [ ] | P1-06 | Enemy and boss tuning pass (difficulty curves by act and mission tier) | DESIGN + ENG-CORE | S7-S8 | P1-04 | Tuning table per archetype and phase | Core combat feel iteration | Difficulty spikes within target fail-rate bands |
| [ ] | P1-07 | Economy and rewards pass (currency sinks, reward fairness, fragment pacing) | DESIGN + ENG-DATA | S8 | P1-04, P0-07 | Economy model and reward audit | Sustains long-term progression motivation | Economy inflation/shortage outside target band eliminated |
| [ ] | P1-08 | Content authoring guardrails (mission lint, dialogue event lint, schema CI) | ENG-DATA + QA | S8-S9 | P0-07 | CI content validation gates | Enables safe ideation at higher throughput | Invalid mission/dialogue content blocked pre-merge |
| [ ] | P1-09 | Client integration tests for gameplay-facing systems | QA + ENG-CLIENT | S9 | P1-08 | Expanded automated regression tests | Prevents tuning regressions from UI/client side | Critical client gameplay regressions detected in CI |
| [ ] | P1-10 | P1 signoff and release candidate criteria lock | PROD + DESIGN + QA | S9 | P1-09 | Approved P2 entry criteria | Freezes design pillars before hardening | P1 targets met and signed off by leads |

---

## P2 - Full Release Hardening and Launch

Goal: content-complete, performance-stable, release-managed build to ship and maintain.

| Status | ID | Task | Owner | Sprint | Depends on | Deliverable | Balance / ideation hook | Exit gate |
|--------|----|------|-------|--------|------------|-------------|--------------------------|-----------|
| [ ] | P2-01 | Complete remaining roadmap systems (Echo, Act IV depression mechanics, final-act integrations) | ENG-CORE + ENG-CLIENT + DESIGN | S10-S11 | P1-10 | Feature-complete release branch | Final thematic tuning and identity cohesion | GDD must-have systems marked implemented |
| [ ] | P2-02 | Performance and stability optimization (long session, load times, memory, frame pacing) | ENG-CORE + ENG-CLIENT + QA | S11-S12 | P2-01 | Profiling reports and optimizations | Maintains feel under stress | Meets performance budgets on target hardware |
| [ ] | P2-03 | UX/accessibility and onboarding pass | ENG-CLIENT + DESIGN + QA | S12 | P2-01 | UX polish checklist and options validation | Reduces friction in first-hour tuning insights | New-player completion funnel improves vs P1 baseline |
| [ ] | P2-04 | Release candidate process (code freeze, blocker-only merges, triage SLA, rollback plan) | PROD + QA + ENG-CORE | S13 | P2-02, P2-03 | RC protocol and signoff artifacts | Locks tuned state for launch quality | RC passes full regression + playtest signoff |
| [ ] | P2-05 | Launch prep and post-launch loop setup (telemetry review cadence, hotfix path, backlog triage rules) | PROD + DESIGN + QA | S13-S14 | P2-04 | Live ops handbook | Keeps ideation alive post-launch without destabilizing game | Day-0 and Day-7 post-launch review process approved |
| [ ] | P2-06 | Final release signoff and shipping checklist | PROD + all leads | S14 | P2-05 | Final release decision record | Final confirmation of tuned and stable experience | No critical or high-severity blockers remain |

---

## 0C. Balancing, Tweaking, and Ideation Cadence (Runs Through All Phases)

### Weekly cadence

| Day | Activity | Owner | Artifact |
|-----|----------|-------|----------|
| Mon | Set hypotheses for week | DESIGN + ENG leads | `balance_hypotheses.md` |
| Tue-Wed | Implement targeted changes | ENG roles | Commits linked to plan IDs |
| Thu | Structured playtest sessions (baseline/challenge/new-player) | QA + DESIGN | Playtest observations + telemetry bundle |
| Fri | Review metrics, accept/reject hypotheses, queue next loop | DESIGN + PROD + ENG | Decision log + updated checklist status |

### Mandatory balance artifacts

- `BALANCE_LOG.md`: each parameter change, why it changed, expected effect, observed result.
- `IDEATION_BACKLOG.md`: candidate ideas with `impact`, `effort`, `risk`, `thematic_fit`.
- `PLAYTEST_REPORT_<date>.md`: qualitative notes plus quantitative telemetry.
- `RISK_REGISTER.md`: known risks, mitigations, owner, due sprint.

### Metric guardrails (initial targets, refine during P1)

| Metric | Target band | Usage |
|--------|-------------|-------|
| Mission completion rate (mainline) | 65% to 85% | Detects overtuned or undertuned progression |
| Mission fail due to unclear objective | < 10% | Signals objective readability issues |
| Average retries per boss (story path) | 2 to 6 | Controls frustration vs mastery |
| Median mission duration | 8 to 18 min | Maintains pacing consistency |
| Economy reserve at act transitions | Positive but constrained | Prevents inflation and hard-lock scarcity |
| Severe spike encounters per session | 0 to 1 | Keeps difficulty ramps intentional |

### Change-control rules for tuning

- Do not merge unmeasured balance changes.
- Each balance commit must reference a hypothesis ID.
- Freeze tuning 48 hours before any release candidate.
- After freeze, only blocker fixes are allowed.

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

### Current codebase state (v0.11.5)

The Phase 0 audit (Apr 9) identified ~30 structural issues. All resolved. Milestones 1–3 shipped. Infrastructure bugs discovered in the first playable sessions and fixed.

| Area | Resolved | Still open |
|------|----------|-----------|
| ECS | EntityLifecycleListener, SerializableComponent, auto-tag index, concrete components | ECS-4 (no auto-registration, low risk) |
| Physics | TileType decoupling, GAS tile, abilityFlags, dynamicTiles in candidates, raycast API; lava ceiling trigger test; swept non-tunnel test | PHYS-4/6 (documented contracts) |
| World gen | Back-edges (Metroidvania loops ready), Redis tile cache, PostgreSQL, deterministic biomes | WORLD-5/6/7 (low risk) |
| Networking | Schema version, frameHash desync detection, Redis zone cache, no boxing; NET-1 spawn default | NET-4/5 (no NPC/inventory delta, low) |
| Inventory | DB-backed items/recipes, player_inventory persistence, ability type, coin recipe fix, item Redis cache | — |
| Tests | 13 test files; all gaps closed including lava ceiling trigger + swept non-tunnel | — |
| Solo mode | In-process GameSimulator; no server required; unified world layout; 12-room megamap | — |
| Hub system | HubState FSM, HubStateMachine, NPC spawn/despawn, Act.java FSM, player_progress persistence | — |
| Save state | Full save (currency, inventory, abilities, world seed, visited rooms) via syncSaveState() | — |
| Logging | logback.xml in shadow JAR (Gradle resource-filter bug fixed); client.log written on disk | — |
| Replays | Solo InputRecorder wired into GameScreen; .ndjson files in user_data/replays/ | — |
| Launcher | cwd fixed for server Popen; replay viewer handles .ndjson; record flag wired to -Dninja.record | — |

### What shipped since plan was written (v0.11.0 → v0.11.6)

| Version | What shipped |
| ------- | ------------ |
| v0.11.0 | M1: test gaps closed, version sync; M2: solo mode in-process GameSimulator |
| v0.11.1 | M3: HubStateMachine, Act FSM, NPC roster sync, player_progress persistence |
| v0.11.2 | fix: solo multi-room world; hub NPC authority; overlay null-guards |
| v0.11.3 | fix: portal NPE in solo (networkClient null-guard); full save state (currency/inventory/abilities) |
| v0.11.4 | fix: logback.xml stripped by Gradle resource filter; server cwd missing in launcher |
| v0.11.5 | feat: solo InputRecorder + .ndjson replay files; launcher replay viewer updated |
| v0.11.6 | M4: YinYangComponent + LanternComponent + vignette + HUD bars + weapon-state animation routing; 171 player sprite sheets extracted |
| v0.11.7 | fix: vignette in solo mode (setDarkArea flag); crouch_walk + swim animation states; companion orbs scale with Yin/Yang; HUD redesign (merged stamina, lantern bottom-left) |
| v0.11.8 | fix(vignette): smoother gradient (20 layers, quadratic curve), corner overlap fix, base dim layer; build.gradle.kts version resync (0.10.83 → 0.11.8) |
| v0.11.9 | fix(vignette): critical GL blend state bug — SpriteBatch.end() disables GL_BLEND; ShapeRenderer did not re-enable it; all vignette rectangles drew as solid opaque black covering the game world. Fix: explicit glEnable(GL_BLEND) before shapes.begin() |
| v0.11.10 | feat(m5): Shadow Ascent boss AI — BossPatternLibrary (Siren/EchoWarden/TimeLechLord/MemoryEater); SCRIPTED_LOSS MessageType; enemy FLEE+GUARD states; loadEnemySheets() + stitch_enemy_frames.py; climb/ledge animation FSM routing |
| v0.11.11 | fix(m3): hub NPC authority; overlay null-guards |
| v0.11.12 | fix(m3): skip hub NPC sync at frame 0; fix CME when despawning NPCs |
| v0.11.13–15 | fix: log files, save-on-exit, save-on-room-entry; launcher black formatting CI fix |
| v0.11.16 | feat(pickups): PickupSlot respawn system (30–60 s lifetime, 15–30 s cooldown) |
| v0.11.17 | fix(rendering): bottom-anchor enemy sprites to physics feet; ENEMY_LIFT formula |
| v0.11.18 | fix(dialogue): bundle data/ into fat JAR so NPC dialogues load from classpath |
| v0.11.19 | feat(minimap): 860×680 panel; zoom 1x/2x/4x (+/-); arrow pan; per-pickup-type colours; room labels when zoomed; hitbox debug overlay (H); terrain density boost; fragments in all loot pools; pickup Y-spawn fix |

### What the GDD requires that doesn't exist

Four interlocking pillars define Shadow Ascent. Two are shipped:

| Pillar | GDD section | Status |
|--------|-------------|--------|
| Yin/Yang system | §3.3 | **Done** — `YinYangComponent`, decay/sight/surge, bars in HUD (v0.11.6) |
| Lantern system | §3.4 | **Done** — `LanternComponent`, vignette overlay, lantern meter (v0.11.6) |
| Hub evolution state machine | §4 | **Done** — `HubState`, `HubStateMachine`, NPC roster sync, `player_progress` (v0.11.1) |
| Narrative Act FSM | §5 | **Done** — `Act.java` FSM Acts I–VI, `StoryManager` wired to hub state (v0.11.1) |

Secondary systems — boss AI behavioral patterns, Echo mechanic, puzzle archetypes, Act IV depression mechanics — not yet built.

### The multiplayer vs. single-player decision

The GDD is single-player first with optional co-op. The codebase is multiplayer first.

**Decision:** Keep the networked architecture. Add an **in-process solo mode** where `GameSimulator` runs locally on the client, no socket required. The same rendering pipeline serves both paths. Multiplayer co-op becomes an optional overlay — Yin/Yang and Lantern work identically in both modes.

### Three game modes (as of v0.11.3)

The game ships **three distinct modes** with separate loops, tones, and world structures. The milestones below cover Campaign/Solo. Arcade and Sandbox are separate roadmap tracks.

| Mode | Loop | World | Player identity | Status |
|------|------|-------|-----------------|--------|
| **Campaign / Solo** | Narrative Metroidvania; hub → portal → mission level | Instanced; procedurally generated interconnected rooms; hub world | The Hallowed Ninja | **Active — this roadmap** |
| **Arcade** | Roguelike run; no hub; loadout + powerup/modifier builds; death ends run | Per-run generated dungeon; smaller rooms; no persistence | Unnamed Ninja (cosmetic) | Planned — separate Arcade roadmap |
| **Sandbox** | Open-ended survival/construction; player-set goals; persistent server world | Endless interconnected world; no instancing; destructible | Disciples / Acolytes (NOT the Hallowed Ninja) | Planned — separate Sandbox roadmap |

**Key design constraints that follow from this:**
- Arcade must NOT use the Metroidvania hub system — it is a separate loop entirely
- Sandbox players are not the protagonist; the world is the canvas, not the story
- Solo/Campaign can share network code with Arcade for co-op lobby, but the world generation, persistence, and narrative systems are campaign-only

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

Files that must be created (✓ = already exists):

```
core/src/main/java/com/indieniinja/
├── world/
│   ├── HubState.java          ✓ (v0.11.1)
│   └── HubStateMachine.java   ✓ (v0.11.1)
└── sim/
    ├── YinYangComponent.java  ✓ (v0.11.6)
    ├── LanternComponent.java  ✓ (v0.11.6)
    ├── SimEcho.java           ← M6
    └── EchoRecorder.java      ← M6

client/src/main/java/com/indieniinja/client/game/
└── Act.java                   ✓ (v0.11.1)
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

### Milestone 4 — Yin/Yang & Lantern (v0.11.6) ✓ SHIPPED

*The core emotional mechanics are functional and visible.*

- [x] `YinYangComponent` (server tick: decay, yin_sight flag, balanced check)
- [x] `LanternComponent` (server decay/restore, dark-room check, jump bonus)
- [x] `PlayerState` + `WorldSnapshot` updated (SCHEMA_VERSION → 2, 5 new fields)
- [x] `HudRenderer` Yin/Yang bars + Lantern meter (glow states, Flow Mode indicator)
- [x] `ChunkRenderer` vignette (12-layer screen-edge overlay, red-tint at low lantern)
- [x] `ABILITY_YIN_SIGHT` bitmask in `PhysicsConstants`; set/cleared in `GameSimulator.tickYinYang()`
- [x] Fragment items in `ItemDatabase` + placed by `EntityPlanner` in BOSS/TREASURE rooms
- [x] Weapon-state animation routing in `EntityRenderer` (`player_sword_*` prefix)
- [x] 171 player sprite sheets extracted: 81 unarmed, 90 sword (tools/extract_animations.py)
- [x] `AnimationRegistry.loadUnarmedSheets()` + `loadSwordSheets()` — 130+ animation keys
- [ ] Siren: scripted loss → Yin/Yang → 0 → hub state → EMPTY (deferred to M5)

**Deliverable:** Yin/Yang bars and Lantern meter render live. Low Lantern creates oppressive vignette. Fragments spawn in boss/treasure rooms. Full player animation set loaded from template sheets.

---

### Milestone 5 — Boss AI (v0.11.10) ✓ SHIPPED

*Four bosses, each with a distinct psychological pattern. Ship working FSMs first, tune after.*

- [x] Shadow Ascent `BossType` values: SIREN, ECHO_WARDEN, TIME_LEECH_LORD, MEMORY_EATER
- [x] `BossPatternLibrary.java` — 4 psychological patterns (ScriptedLoss, EchoMirror, LanternDrain, PhaseReset)
- [x] `SCRIPTED_LOSS` `MessageType` added; `GameSimulator.drainPendingScriptedLoss()` poll method
- [x] `GameSimulator.setHub()` injection point; narrative patterns wired in `stepBosses()`
- [x] Siren: invincible; after 6 s song sequence → zero all Yin/Yang → `hub.onSirenDefeated()` → `SCRIPTED_LOSS`
- [x] Echo Warden: 30-tick ring buffer mirrors player movement with 0.5 s delay
- [x] Time Leech Lord: drains Lantern each tick; spawns `time_leech` enemies every 8 s; speed burst at 30% HP
- [x] Memory Eater: `boss.platformReset` flag set on phase transition; `ZoneSimulationLoop` reads and acts on it
- [ ] Client collapse animation on `SCRIPTED_LOSS` receive (deferred — needs new anim state in EntityRenderer)
- [ ] Boss defeat → fragment drop → `HubStateMachine.onBossDefeated()` (fragment wiring deferred to M6)

**What shipped:** All 4 psychological patterns are live server-side. Siren scripted loss fires correctly. Echo Warden mirrors movement. Time Leech Lord drains lantern and spawns minions. Memory Eater signals platform reset per phase. Client-side collapse animation and fragment drop wiring are next-session tuning items.

Loop note (2026-04-13 21:27:17 +01:00): Enemy combat tuning pass shipped after M5:
slime attack hitbox now lunges one body-length forward, skeleton attack range is
extended by 15%, and archers now fire projectile attacks that damage players.

**Note:** Boss tuning (HP, timings, difficulty) will need iteration after first playtests — Lesson 1 from project history.

---

### Milestone 6 — Echo System & Puzzles (v0.11.11)

*Solo play feels co-op through echoes. Puzzle rooms are distinct.*

- [x] `EchoRecorder` (600-tick ring buffer on `SimPlayer`)
- [x] `SimEcho` (`ReplayPlayer`-driven, `recallable` flag)
- [ ] Echo trigger zones placed by `EntityPlanner` in PUZZLE rooms
- [ ] Puzzle archetype: **Asymmetric Ability Lock** (echo holds position)
- [ ] Puzzle archetype: **Simultaneous Timing** (echo replicates past actions)
- [ ] Proof token mechanic (`RoomType.LABYRINTH`, `TOKEN_GATE`)
- [ ] `ValidationLayer` verifies all puzzles solvable with current ability set

Loop note (2026-04-13 19:36:16 +01:00): `EchoRecorder` added in `core/sim`, integrated on `SimPlayer`,
and sampled each tick in `GameSimulator.step()`; covered by `EchoRecorderTest`.
Loop note (2026-04-13 20:03:24 +01:00): `SimEcho` added as a `ReplayPlayer`-driven entity with
`recallable` fail semantics; `GameSimulator` now supports echo spawn/tick/recall
hooks (`spawnEchoFromPlayer`, `addEcho`, `stepEchoes`, `recallEcho`), and behavior
is covered by `SimEchoTest`.

**Deliverable:** Puzzle rooms are mechanically interesting solo. Act III "unfair" platforms work.

---

### Milestone 7 — Act IV & Narrative Arc (v0.11.12)

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

### Milestone 8 — Polish (v0.11.13+)

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
