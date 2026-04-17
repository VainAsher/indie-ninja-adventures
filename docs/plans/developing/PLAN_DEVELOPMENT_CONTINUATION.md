---
doc_type: plan
status: developing
owner: core-team
last_updated: 2026-04-17
version_anchor: v0.11.59
---

# PLAN — Development Continuation: v0.11.55 Onwards
**Created:** 2026-04-17 | **Last updated:** 2026-04-17 | **Base version:** v0.11.59

This plan tracks the next development threads after the v0.11.54 closure. It is a **developing** document — items here are planned, scoped, and ready to be promoted into the active implementing plan (`PLAN_SHADOW_ASCENT.md`) as each thread becomes the active implementation focus.

---

## 0. Workloop Rules (Inherited)

All implementation loops from this plan follow the mandatory P0 workloop:

| Step | Action |
|------|--------|
| 1 | Review active plan and current phase state |
| 2 | Build scoped task list mapped to plan IDs below |
| 3 | Execute tasks one by one |
| 4 | Commit after each logical unit |
| 5 | Update this plan (or PLAN_SHADOW_ASCENT.md when promoted) |
| 6 | Push to remote |
| 7 | Loop |

Any loop touching combat, stance, Flow, or Lantern readability must also record:
- Intended player-facing feel change
- Whether it affects Passive play, Aggressive play, or both
- Whether it affects Flow entry, maintenance, or readability

---

## 1. Current State at v0.11.54

### What is complete
| Area | Status |
|------|--------|
| Java server loop + snapshot replication | ✅ Complete |
| Mission lifecycle (objectives, save/load, scripted loss) | ✅ Complete |
| Hub state machine (M5) | ✅ Complete |
| Siren-first onboarding chain + phase sprites | ✅ Complete |
| Guard/parry runtime + basic combat | ✅ Complete |
| Stance-gated traversal: Yin climb / Yang slide | ✅ Complete |
| Phase 5/6 swim tuning + water surface detection | ✅ Complete |
| Runtime keybindings + live controls overlay (F1) | ✅ Complete |
| Phase 7 interaction affordance readability bridge | ✅ Complete |
| Phase 8 posture hot-swap bridge (1/2 keys) | ✅ Complete |
| Version parity + docs freshness gates | ✅ Complete |
| CI + Release workflows (annotated tag → GH Release) | ✅ Complete |
| Echo trigger authored type (M6 partial) | ✅ Complete |

### What is in-progress
| Area | Status |
|------|--------|
| Animation integration — full moveset sprites (PLAN_ANIMATION_INTEGRATION.md) | 🔄 In progress: weapon hot-swap bridge done; sprite extraction + engine wiring pending |
| M6 Echo system — echo playback/replay | 🔄 In progress: authored trigger done; playback mechanics pending |
| P0-10 onboarding/system-guidance hardening | 🔄 In progress |

### What is pending (not yet started)
| Area |
|------|
| Audio foundations (SFX event bus, ambient, music transitions) |
| Boss pattern depth (Siren phase 4, vulnerability tuning, add-wave pacing) |
| Trials scaffolding (mastery extensions of combat/traversal language) |
| Act II content depth (second hub, authored Act II missions) |
| Act III+ campaign content |
| Combo chain system (weapon-specific moves, aerial attacks) |
| Roll mechanic (vs dash movement identity) |
| Multiplayer stance synergy display |

---

## 2. Development Threads

### Thread A — Animation Integration Continuation
**Plan reference:** `docs/plans/developing/PLAN_ANIMATION_INTEGRATION.md`
**Anchor version:** v0.11.54
**Next version target:** v0.11.55–v0.11.57

The hot-swap posture bridge (Phase 8) is complete at v0.11.54. The full sprite extraction and engine wiring remain the primary developing task in this thread.

#### A1. Sprite Extraction Pass
- [ ] Run extraction script for unarmed ZIP: copy all sheets to `assets/sprites/player/unarmed/` with canonical engine filenames
- [ ] Run extraction script for sword ZIP: copy all sheets to `assets/sprites/player/sword/`
- [ ] Verify pistol sheets land in `assets/sprites/player/pistol/` (reserved for Arcade)
- [ ] Confirm all extracted sheets match 80px height and horizontal-strip format
- [ ] Commit as `feat(assets): extract player unarmed + sword sprite sheets`

#### A2. AnimationRegistry Wiring
- [ ] Register all unarmed animation keys: `player_unarmed_idle`, `player_unarmed_run`, `player_unarmed_jump`, etc.
- [ ] Register all sword animation keys: `player_sword_idle`, `player_sword_run`, etc.
- [ ] Add `player_pistol_*` stubs (no-op / magenta fallback) so Arcade mode won't crash on access
- [ ] Validate no existing key collision with current `player_*` key set
- [ ] Commit as `feat(anim): register full unarmed + sword animation keys`

#### A3. EntityRenderer Weapon-State Routing
- [ ] Update `EntityRenderer.resolveAnimKey(...)` to prefix with `weaponState` from `PlayerState`
- [ ] Ensure fallback chain: `player_{weaponState}_{animState}` → `player_unarmed_{animState}` → magenta dot
- [ ] Validate stance-coupled readability: Yin forces unarmed prefix; Yang uses preferred weapon prefix
- [ ] Playtest log: `[Playtest][Weapon]` events on weapon-state transitions
- [ ] Commit as `feat(anim): wire weapon-state prefix routing in EntityRenderer`

#### A4. Full Moveset Animation State Coverage
- [ ] Wire all traversal animation states: `climb`, `ledge_hang`, `ledge_climb`, `swim`, `swim_surface`, `water_exit`
- [ ] Wire all combat animation states: `block`, `block_hit`, `parry`, `interact_lever`, `interact_button`, `interact_pickup`
- [ ] Wire ninjutsu: `ninjutsu_cast` anim state for `ninjutsuCasting` flag
- [ ] Wire teleport phase: `teleport_phase` and `teleport_warp` states
- [ ] Validate all states degrade gracefully to nearest fallback if sheet missing
- [ ] Commit as `feat(anim): full moveset animation state coverage`

---

### Thread B — M6 Echo System Completion
**Plan reference:** `PLAN_SHADOW_ASCENT.md` M6
**Anchor version:** v0.11.54
**Next version target:** v0.11.58–v0.11.59

The authored `ECHO_TRIGGER` puzzle type, planner allocation, and `echo_trigger_<pid>` → `echo_door_<pid>` unlock mechanic are implemented. The Echo playback and replay mechanics are pending.

#### B1. Echo Recorder Foundation
- [ ] `EchoRecorder` (already on `SimPlayer`) — confirm last 10-second ring buffer stores full `InputCommand` history per tick
- [ ] Add `EchoRecorder.getReplay()` method returning a time-ordered snapshot slice for playback
- [ ] Unit test: 10-second ring buffer wraps correctly; replay slice returns correct command sequence
- [ ] Commit as `feat(echo): EchoRecorder ring buffer and replay slice API`

#### B2. Echo Playback Simulation
- [ ] `SimEcho` entity class: position, facing, animation state, playback cursor, duration
- [ ] `GameSimulator.stepEchoPlayback()`: advance cursor each tick, apply `InputCommand` to ghost physics
- [ ] Echo physics should use a separate read-only `PhysicsState` clone — no collision response
- [ ] Echo entities serialized into snapshot as `echo_*` entity type
- [ ] Commit as `feat(echo): SimEcho playback entity and simulation step`

#### B3. Echo Render Pass
- [ ] `EntityRenderer` renders `echo_*` entities with 40% alpha tint (ghostly visual)
- [ ] Echo uses same weapon-state and anim-state prefix routing as live player
- [ ] No HUD elements for echo entities
- [ ] Commit as `feat(echo): ghost echo render pass with alpha tint`

#### B4. Echo Puzzle Integration
- [ ] When player interacts with `echo_trigger_<pid>`, spawn echo at trigger position using current recorder snapshot
- [ ] Echo walks the recorded path; when it reaches `echo_door_<pid>` contact volume, door unlocks
- [ ] Add `[Playtest][Echo]` event logs for trigger activation and door unlock
- [ ] Commit as `feat(echo): echo puzzle trigger → door unlock flow`

---

### Thread C — Audio Foundations
**Anchor version:** pending (not yet started)
**Next version target:** v0.11.60+

No audio system exists in the Java client. This thread lays the groundwork.

#### C1. SFX Event Bus
- [ ] Define `SfxEvent` enum: `PLAYER_LAND`, `PLAYER_JUMP`, `PLAYER_ATTACK`, `PLAYER_HURT`, `PLAYER_DEATH`, `ENEMY_HURT`, `ENEMY_DEATH`, `DOOR_OPEN`, `PICKUP_COIN`, `PICKUP_HEALTH`, `BOSS_PHASE_CHANGE`
- [ ] `SfxBus` singleton: subscribes to GameScreen events; dispatches via libGDX `Sound.play()`
- [ ] Asset loader: loads `.ogg` files from `assets/sfx/` at startup
- [ ] Placeholder silence fallback when file absent (no exception)
- [ ] Commit as `feat(audio): SFX event bus and placeholder asset loader`

#### C2. Ambient Layer
- [ ] `AmbientPlayer` class: loops ambient track for current zone type (hub / dungeon / boss / water)
- [ ] Zone transition triggers cross-fade (1.5s) to new ambient track
- [ ] Volume exposed in settings (maps from `settings.json` `audio_sfx_volume` / `audio_music_volume`)
- [ ] Commit as `feat(audio): ambient layer with zone-type cross-fade`

#### C3. Music Transitions
- [ ] Combat-state detection: enter combat music when enemies are aggro'd within current room
- [ ] Boss music: triggered by boss-phase entry event from sim snapshot
- [ ] Hub music: plays in hub room, fades when player enters first dungeon room
- [ ] Commit as `feat(audio): music state transitions (hub / combat / boss)`

---

### Thread D — Boss Pattern Depth
**Anchor version:** v0.11.54 (Siren phase 1–3 patterns implemented)
**Next version target:** v0.11.61+

Siren has a 3-phase ranged → teleport → volley pattern. Phase 4 (transformation) and vulnerability window tuning are pending.

#### D1. Siren Phase 4 Transition
- [ ] Phase 4 triggers when Siren health crosses threshold after Act I completion (scripted loss → M5 EMPTY hub state sets up narrative precondition)
- [ ] Phase 4 pattern: melee charge + teleport burst + add-wave escalation
- [ ] `boss_siren_phase4` animation key registered (sprites already in reserve)
- [ ] Phase transition broadcast via `BOSS_PHASE_CHANGE` snapshot event → client plays transition VFX
- [ ] Commit as `feat(boss): Siren phase 4 pattern and transition`

#### D2. Vulnerability Window Tuning
- [ ] Add `bossVulnerabilityWindow` to boss state: ticks where boss can receive damage after specific attack patterns
- [ ] Siren vulnerability windows: after each volley burst completes, brief open window
- [ ] Expose per-boss tuning in `data/boss_patterns.json` for playtest iteration without recompile
- [ ] Commit as `feat(boss): vulnerability window system + Siren tuning`

#### D3. Add-Wave Pacing
- [ ] Add-wave spawns tied to vulnerability window transitions (not raw phase boundaries)
- [ ] Wave density scales with active player count (solo vs. co-op)
- [ ] `[Playtest][Boss]` log events for wave spawn triggers and wave clear times
- [ ] Commit as `feat(boss): add-wave pacing tied to vulnerability windows`

---

### Thread E — Trials Scaffolding
**Anchor version:** pending
**Next version target:** v0.11.63+

Trials repurpose Arcade scaffolding as mastery extensions of the same combat/traversal language. They are standalone challenge runs, not story content.

#### E1. Trial Room Structure
- [ ] `TrialDefinition` data class: entry condition (unlocked ability), combat/traversal challenge type, par time, reward item
- [ ] `data/trials.json`: author first 3 trials (dash mastery, wall-jump mastery, parry mastery)
- [ ] World generator can allocate a `TRIAL` room type when `worldShape = TRIAL_GAUNTLET`
- [ ] Commit as `feat(trials): trial definition schema and world generator support`

#### E2. Trial Runtime Loop
- [ ] Trial start: lock room exits, spawn trial waves/obstacles, start countdown timer
- [ ] Trial end: par-time check → reward delivery → exit unlock + `[Playtest][Trial]` log
- [ ] HUD: show trial timer and wave progress during active trial
- [ ] Commit as `feat(trials): trial runtime loop with timer and reward delivery`

#### E3. Trial Unlock Flow
- [ ] Siren dialogue tree: `siren_unlock_trial_<id>` events unlock corresponding trial rooms on map
- [ ] Trials appear on minimap with `TRIAL` room label once unlocked
- [ ] Save/load persists trial completion state in `SaveData.storyFlags`
- [ ] Commit as `feat(trials): Siren-gated trial unlock flow`

---

### Thread F — Act II Content Depth
**Anchor version:** pending
**Next version target:** v0.12.0+

Act I is playable end-to-end. Act II content requires authored missions, a second hub context, and Siren phase 4 narrative integration.

#### F1. Second Hub Context
- [ ] Hub ID `hub_act2` added to `HubStateMachine`: states `LOCKED` → `ACCESSIBLE` → `CORRUPTED_DEEP`
- [ ] Act II entry triggered by Siren dialogue after Act I scripted loss
- [ ] Act II hub rendered with distinct tile palette (deeper dungeon aesthetic, water-logged geometry)
- [ ] Commit as `feat(hub): Act II hub state and entry trigger`

#### F2. Act II Mission Set
- [ ] Author 5–7 Act II missions in `data/missions.json`: deeper objective mix (reach + switch + kill + timed)
- [ ] Mission board in Act II hub surfaces Act II mission list
- [ ] Authored `reach_location` trigger volumes for Act II rooms in `data/mission_location_triggers.json`
- [ ] Commit as `feat(missions): Act II mission set and location triggers`

#### F3. Act II Siren Presence
- [ ] Siren appears in Act II hub as phase-3/4 visual (corrupted form)
- [ ] Act II onboarding dialogue tree added to `data/dialogues.json`
- [ ] `siren_act2_intro_seen` story flag gates repeat dialogue
- [ ] Commit as `feat(onboarding): Act II Siren presence and dialogue`

---

## 3. Thread Priority Order

Based on current v0.11.54 state and the P0-10 workloop direction:

| Priority | Thread | Rationale |
|----------|--------|-----------|
| 1 | **Thread A** — Animation Integration | Active developing work in PLAN_ANIMATION_INTEGRATION.md; hot-swap bridge done, sprite extraction is the immediate next action |
| 2 | **Thread B** — M6 Echo Completion | Echo trigger is already authored; playback is the blocking gap for M6 closure |
| 3 | **Thread C** — Audio Foundations | Highest player-experience impact for playtest sessions; can be parallelized with Thread B |
| 4 | **Thread D** — Boss Pattern Depth | Required for Act II narrative to land correctly (Siren phase 4 is the Act I→II bridge) |
| 5 | **Thread E** — Trials | Depends on combat/traversal depth being stable; can begin scaffolding once Thread A is done |
| 6 | **Thread F** — Act II Content | Depends on Siren phase 4 (Thread D) and Echo completion (Thread B) |

---

## 4. Version Targets

### Delivered (v0.11.55–v0.11.59)

| Version | Delivered |
|---------|-----------|
| v0.11.55 ✅ | Thread A/B: `EchoState` wire protocol, `WorldSnapshot.echoes`, `SimEcho` animState/weaponState, `EntityRenderer.renderEcho()` ghost pass, pistol animation routing, `AnimationRegistry.loadPistolSheets()` |
| v0.11.56 ✅ | Thread F: Samson/Sophia/Marcel/Hazel three-act dialogue trees (12 IDs), shadow-echo fragments (4 IDs), Linzi hub NPC dialogue, 13 NPC side-quest missions with hub_impact, NPC disappearance wired |
| v0.11.57 ✅ | Thread C: `MusicManager` zone-based BGM with 1.5 s cross-fade, act-specific track variant resolution, `GameScreen` wiring |
| v0.11.58 ✅ | Thread D: `VeilMaidenPattern` — illusion wave spawning, invincibility-while-illusions-live, distortion projectile spread, final form at 25% HP; `SimBoss.forceInvincible()` |
| v0.11.59 ✅ | Thread E: `data/trials.json` — 5 trial definitions (samson_brothers, marcel_forge_deep, hazel_woven_root, sophia_star_ink, ember_monastery_gauntlet); `ZonePlanner` trial room type |

### Upcoming

| Version | Scope |
|---------|-------|
| v0.11.60 | Thread A: Sprite extraction pass (A1) — extract player unarmed + sword sheets |
| v0.11.61 | Thread A: AnimationRegistry full wiring + EntityRenderer weapon-state routing (A2–A3) |
| v0.11.62 | Thread B: EchoRecorder ring buffer + replay slice API (B1) |
| v0.11.63 | Thread B: Echo playback simulation + puzzle integration (B2–B4) |
| v0.11.64 | Thread D: Siren phase 4 pattern + vulnerability window system (D1–D2) |
| v0.11.65 | Thread D: Add-wave pacing (D3) |
| v0.11.66 | Thread E: Trial runtime loop with timer, wave lock, reward delivery (E2) |
| v0.11.67 | Thread E: Trial unlock flow via Siren dialogue (E3) |
| v0.12.0  | Thread F: Act II content — second hub, Act II missions, Siren phase 4 presence (F1–F3) |

These are targets, not hard commitments. Each version may shift by ±1 patch based on gate results and playtest feedback.

---

## 5. Promotion Criteria

A thread from this plan is ready to be promoted to `PLAN_SHADOW_ASCENT.md` (implementing) when:
- All developing items in the thread are authored and scoped (i.e., this document is complete for that thread)
- No external blockers remain (assets, dependencies, prior thread)
- The implementing plan has capacity (previous thread iteration is committed and pushed)

**Do not begin implementing a thread until it has been promoted.**
