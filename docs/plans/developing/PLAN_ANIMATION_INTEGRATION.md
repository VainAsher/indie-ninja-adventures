---
doc_type: plan
status: developing
owner: core-team
last_updated: 2026-04-16
version_anchor: v0.11.54
---
# PLAN â€” Animation Integration: Full Moveset Implementation
**Created:** 2026-04-11 | **Last updated:** 2026-04-16 01:36:22 +01:00 | **Base version:** v0.11.4 | **Current version:** v0.11.54

---

## 0. Situation Summary

### What we have

| Layer | Current state |
|-------|--------------|
| Engine | Java / libGDX client-server. `AnimationRegistry` loads 80Ã—80 px horizontal-strip PNGs, slices them, and serves frames via `anims.getFrame(key, stateTime, fps)` |
| Animation keys | `EntityRenderer` constructs keys as `"player_" + animState`. Currently ~18 keys wired (idle, run, dash, jump, fall, wall_slide, crouch, crouch_walk, attack/slash1-3, throw, teleport, hurt, death) |
| Player state machine | `GameSimulator.stepPlayerAnimationState()` sets `animState` string via priority chain: teleport â†’ dash â†’ attack â†’ throw â†’ wall_slide â†’ jump/fall â†’ crouch â†’ run â†’ idle |
| Combat | Single-hit melee: `isAttacking` bool, 8-tick active window, 0.4 s cooldown. No combo chain, no weapon state |
| Traversal | Dash, double-jump, wall-slide, wall-jump, crouch all implemented in `SimPlayer`. **No** climb, swim, prone, roll, or slide states |
| Assets | All player sheets are **placeholder** â€” engine runs but looks wrong |

### What we have from the ZIPs

Two ZIPs (unarmed + sword) provide **fully production-ready sprite sheets** already in the engine's native format: 80 px tall, RGBA, horizontal strips. Confirmed by dimension check:
```
001-Standing Idle-Sheet.png  â†’  640Ã—80 px  =  8 frames Ã— 80 px  âœ… exact match
001-Run-Sheet.png            â†’  640Ã—80 px  =  8 frames Ã— 80 px  âœ… exact match
001-Jump-Sheet.png           â†’  800Ã—80 px  = 10 frames Ã— 80 px  âœ… exact match
```
**No pixel conversion is needed.** Extract, rename, drop into assets.

### ZIP bonus content
`002 Player Template Moves - Sword.zip` contains three complete weapon sets:
1. Unarmed (re-export of ZIP 001 â€” ignore duplicates)
2. **Sword** (fully re-animated for all states, plus sword-specific `Dash Attack`)
3. **Pistol** (bonus â€” not in GDD; reserve for Arcade Mode loadout system)

---

## 0.1 Global Rules (carry over from animation_pipeline_plan.md)

- Do NOT break existing gameplay logic
- Do NOT load or transform images inside the render loop
- Do NOT introduce per-frame allocations
- ALL assets loaded and processed at startup via `AnimationRegistry`
- Weapon-state switching must not cause a frame stutter
- Placeholder fallback must survive missing sheets (magenta dot stays in)
- All new `SimPlayer` fields must be serialised via `PlayerState` network schema

---

## 0.2 Asset Name Mapping Reference

Full ZIP animation â†’ engine filename â†’ animation key table. **This is the contract for the extraction script.**

### Unarmed â€” `assets/sprites/player/unarmed/`

| ZIP name | Engine filename | Key(s) registered | Frames | FPS | Loop |
|----------|----------------|-------------------|--------|-----|------|
| Standing Idle | `idle_spritesheet.png` | `player_idle` | 8 | 8 | yes |
| Standing Fighting | `combat_idle_spritesheet.png` | `player_combat_idle` | 8 | 8 | yes |
| Standing Idly | `fidget_spritesheet.png` | `player_fidget` | 8 | 6 | yes |
| Standing Walk | `walk_spritesheet.png` | `player_walk`, `player_slow_walk` | 8 | 10/8 | yes |
| Standing Direct Punch Combo | `punch1_spritesheet.png` | `player_punch1` | 6 | 15 | no |
| Standing Cross Punch Combo | `punch2_spritesheet.png` | `player_punch2` | 8 | 15 | no |
| Standing Kick | `kick_spritesheet.png` | `player_kick` | 6 | 15 | no |
| Standing Block Idle | `block_idle_spritesheet.png` | `player_block` | 8 | 8 | yes |
| Standing Block Hit (Normal) | `block_hit_normal_spritesheet.png` | `player_block_hit` | 3 | 15 | no |
| Standing Block Hit (Hard) | `block_hit_hard_spritesheet.png` | `player_parry` | 6 | 15 | no |
| Standing Hit Upper Body | `hurt_upper_spritesheet.png` | `player_hurt` | 4 | 12 | no |
| Standing Hit Lower Body | `hurt_lower_spritesheet.png` | `player_hurt2` | 4 | 12 | no |
| Standing Death A | `death_spritesheet.png` | `player_death` | 7 | 12 | no |
| Standing Death A Getting Up | `revive_spritesheet.png` | `player_revive` | 6 | 12 | no |
| Standing Death B | `death2_spritesheet.png` | `player_death2` | 7 | 12 | no |
| Standing Death B Getting Up | `revive2_spritesheet.png` | `player_revive2` | 6 | 12 | no |
| Run | `run_spritesheet.png` | `player_run` | 8 | 12 | yes |
| Run Skid Turn | `skid_spritesheet.png` | `player_skid` | 4 | 15 | no |
| Run Flying Kick | `run_kick_spritesheet.png` | `player_run_kick` | 6 | 15 | no |
| Run Stop | `run_stop_spritesheet.png` | `player_run_stop` | 3 | 15 | no |
| Jump (10f) | `jumpfall_spritesheet.png` | `player_jump` (f0-4), `player_fall` (f5-9) | 10 | 10 | no |
| Jump Front Flip | `flip_spritesheet.png` | `player_flip` | 6 | 12 | no |
| Jump Direct Punch Combo | `air_punch1_spritesheet.png` | `player_air_punch1` | 6 | 15 | no |
| Jump Cross Punch Combo | `air_punch2_spritesheet.png` | `player_air_punch2` | 8 | 15 | no |
| Jump Kick | `air_kick_spritesheet.png` | `player_air_kick` | 6 | 15 | no |
| Jump Block Idle | `air_block_spritesheet.png` | `player_air_block` | 10 | 8 | yes |
| Jump Block Hit | `air_block_hit_spritesheet.png` | `player_air_block_hit` | 3 | 15 | no |
| Crouch Idle | `crouch_idle_spritesheet.png` | `player_crouch` | 9 | 8 | yes |
| Crouch Walk | `crouch_walk_spritesheet.png` | `player_crouch_walk` | 8 | 10 | yes |
| Crouch Punch | `crouch_punch_spritesheet.png` | `player_crouch_punch` | 5 | 15 | no |
| Crouch Kick | `crouch_kick_spritesheet.png` | `player_crouch_kick` | 6 | 15 | no |
| Crouch Block Idle | `crouch_block_spritesheet.png` | `player_crouch_block` | 8 | 8 | yes |
| Crouch Block Hit | `crouch_block_hit_spritesheet.png` | `player_crouch_block_hit` | 3 | 15 | no |
| Crouch Hit | `crouch_hurt_spritesheet.png` | `player_crouch_hurt` | 4 | 12 | no |
| Climb Idle (Back) | `climb_idle_back_spritesheet.png` | `player_climb_idle_back` | 4 | 6 | yes |
| Climb Idle (Side) | `climb_idle_side_spritesheet.png` | `player_climb_idle_side`, `player_wall_hang` | 8 | 6 | yes |
| Climb Up/Down (Back) | `climb_back_spritesheet.png` | `player_climb_back` | 6 | 10 | yes |
| Climb Up/Down (Side) | `climb_side_spritesheet.png` | `player_climb_side` | 6 | 10 | yes |
| Climb (Right) | `climb_right_spritesheet.png` | `player_climb_right` | 6 | 10 | yes |
| Climb (Left) | `climb_left_spritesheet.png` | `player_climb_left` | 6 | 10 | yes |
| Climb Ledge Grab (Back) | `ledge_grab_back_spritesheet.png` | `player_ledge_grab_back` | 2 | 10 | no |
| Climb Ledge Idle (Back) | `ledge_idle_back_spritesheet.png` | `player_ledge_idle_back` | 4 | 6 | yes |
| Climb Ledge Climbing (Back) | `ledge_climb_back_spritesheet.png` | `player_ledge_climb_back` | 4 | 12 | no |
| Climb Ledge Grab (Side) | `ledge_grab_spritesheet.png` | `player_ledge_grab` | 2 | 10 | no |
| Climb Ledge Idle (Side) | `ledge_idle_spritesheet.png` | `player_ledge_idle` | 8 | 6 | yes |
| Climb Ledge Climbing (Side) | `ledge_climb_spritesheet.png` | `player_ledge_climb` | 4 | 12 | no |
| Water Surface Idle | `swim_surface_idle_spritesheet.png` | `player_swim_surface_idle` | 8 | 6 | yes |
| Water Surface Swimming | `swim_surface_spritesheet.png` | `player_swim_surface` | 6 | 10 | yes |
| Water Bottom Idle | `swim_idle_spritesheet.png` | `player_swim_idle` | 8 | 6 | yes |
| Water Bottom Swimming (Front) | `swim_spritesheet.png` | `player_swim` | 6 | 10 | yes |
| Water Bottom Swimming (Up) | `swim_up_spritesheet.png` | `player_swim_up` | 6 | 10 | yes |
| Water Bottom Swimming (Down) | `swim_down_spritesheet.png` | `player_swim_down` | 6 | 10 | yes |
| Prone Idle | `prone_idle_spritesheet.png` | `player_prone` | 9 | 6 | yes |
| Prone Crawling | `prone_walk_spritesheet.png` | `player_prone_walk` | 8 | 10 | yes |
| Prone Hit | `prone_hurt_spritesheet.png` | `player_prone_hurt` | 4 | 12 | no |
| Prone Death | `prone_death_spritesheet.png` | `player_prone_death` | 5 | 12 | no |
| Prone Death Waking Up | `prone_revive_spritesheet.png` | `player_prone_revive` | 5 | 12 | no |
| Dash | `dash_spritesheet.png` | `player_dash` | 11 | 20 | no |
| Roll | `roll_spritesheet.png` | `player_roll` | 8 | 15 | no |
| Slide | `slide_spritesheet.png` | `player_slide` | 12 | 15 | no |
| Wall Jump Land | `wall_land_spritesheet.png` | `player_wall_land` | 4 | 15 | no |
| Wall Jump Slide | `wall_slide_spritesheet.png` | `player_wall_slide` | 4 | 8 | yes |
| Push-Pull Idle | `push_idle_spritesheet.png` | `player_push_idle` | 8 | 8 | yes |
| Push | `push_spritesheet.png` | `player_push` | 8 | 10 | yes |
| Pull | `pull_spritesheet.png` | `player_pull` | 8 | 10 | yes |
| Door Enter | `door_enter_spritesheet.png` | `player_door_enter` | 19 | 12 | no |
| Door Exit | `door_exit_spritesheet.png` | `player_door_exit` | 17 | 12 | no |
| Push Button (Side) | `button_spritesheet.png` | `player_button` | 9 | 12 | no |
| Lever | `lever_spritesheet.png` | `player_lever` | 18 | 12 | no |
| Pickup Standing | `pickup_spritesheet.png` | `player_pickup` | 5 | 12 | no |
| Pickup Crouch | `pickup_crouch_spritesheet.png` | `player_pickup_crouch` | 4 | 12 | no |
| Open Chest (Back) | `chest_back_spritesheet.png` | `player_chest_back` | 12 | 10 | no |
| Open Chest (Side) | `chest_side_spritesheet.png` | `player_chest_side` | 11 | 10 | no |
| Rope Hanging Idle | `rope_idle_spritesheet.png` | `player_rope` | 4 | 6 | yes |
| Rope Swinging | `rope_swing_spritesheet.png` | `player_rope_swing` | 7 | 10 | yes |
| Sitting | `sit_spritesheet.png` | `player_sit` | 12 | 8 | yes |
| Asleep | `sleep_spritesheet.png` | `player_sleep` | 19 | 6 | yes |
| Talking | `talk_spritesheet.png` | `player_talk` | 9 | 10 | yes |
| Victory | `victory_spritesheet.png` | `player_victory` | 10 | 10 | no |
| Drink | `drink_spritesheet.png` | `player_drink` | 19 | 8 | no |
| Dance Twerk | `dance_spritesheet.png` | `player_dance` | 12 | 10 | yes |

### Sword â€” `assets/sprites/player/sword/`

| ZIP name | Engine filename | Key(s) registered | Frames | FPS |
|----------|----------------|-------------------|--------|-----|
| Standing Idle - Sword | `idle_spritesheet.png` | `player_sword_idle` | 8 | 8 |
| Standing Idly - Sword | `fidget_spritesheet.png` | `player_sword_fidget` | 8 | 6 |
| Standing Walk - Sword | `walk_spritesheet.png` | `player_sword_walk`, `player_sword_slow_walk` | 8 | 10/8 |
| Standing Attack Combo - Sword (sheet 1 of 8) | `attack_combo_d0_spritesheet.png` | `player_sword_attack` | 35 | 15 |
| Standing Attack Combo - Sword (sheets 2-8) | `attack_combo_d1..d7_spritesheet.png` | `player_sword_attack_d1..d7` | 35 | 15 |
| Standing Attack Stab - Sword | `stab_spritesheet.png` | `player_sword_stab` | 5 | 15 |
| Standing Block Idle - Sword | `block_idle_spritesheet.png` | `player_sword_block` | 8 | 8 |
| Standing Block Hit (Normal) - Sword | `block_hit_normal_spritesheet.png` | `player_sword_block_hit` | 3 | 15 |
| Standing Block Hit (Hard) - Sword | `block_hit_hard_spritesheet.png` | `player_sword_parry` | 6 | 15 |
| Standing Hit Upper Body - Sword | `hurt_upper_spritesheet.png` | `player_sword_hurt` | 4 | 12 |
| Standing Hit Lower Body - Sword | `hurt_lower_spritesheet.png` | `player_sword_hurt2` | 4 | 12 |
| Run - Sword | `run_spritesheet.png` | `player_sword_run` | 8 | 12 |
| Run Skid Turn - Sword | `skid_spritesheet.png` | `player_sword_skid` | 4 | 15 |
| Run Stop - Sword | `run_stop_spritesheet.png` | `player_sword_run_stop` | 3 | 15 |
| Jump - Sword | `jumpfall_spritesheet.png` | `player_sword_jump` (f0-4), `player_sword_fall` (f5-9) | 10 | 10 |
| Jump Front Flip - Sword | `flip_spritesheet.png` | `player_sword_flip` | 6 | 12 |
| Jump Attack Combo - Sword (sheet 1 of 5) | `air_attack_d0_spritesheet.png` | `player_sword_air_attack` | 17 | 15 |
| Jump Attack Combo - Sword (sheets 2-5) | `air_attack_d1..d4_spritesheet.png` | `player_sword_air_attack_d1..d4` | 17 | 15 |
| Jump Stab - Sword | `air_stab_spritesheet.png` | `player_sword_air_stab` | 5 | 15 |
| Jump Block Idle - Sword | `air_block_spritesheet.png` | `player_sword_air_block` | 10 | 8 |
| Jump Block Hit - Sword | `air_block_hit_spritesheet.png` | `player_sword_air_block_hit` | 3 | 15 |
| Crouch Idle - Sword | `crouch_idle_spritesheet.png` | `player_sword_crouch` | 9 | 8 |
| Crouch Walk - Sword | `crouch_walk_spritesheet.png` | `player_sword_crouch_walk` | 8 | 10 |
| Crouch Attack Combo - Sword (sheet 1 of 5) | `crouch_attack_d0_spritesheet.png` | `player_sword_crouch_attack` | 17 | 15 |
| Crouch Attack Combo - Sword (sheets 2-5) | `crouch_attack_d1..d4_spritesheet.png` | `player_sword_crouch_attack_d1..d4` | 17 | 15 |
| Crouch Stab - Sword | `crouch_stab_spritesheet.png` | `player_sword_crouch_stab` | 5 | 15 |
| Crouch Block Idle - Sword | `crouch_block_spritesheet.png` | `player_sword_crouch_block` | 8 | 8 |
| Crouch Block Hit - Sword | `crouch_block_hit_spritesheet.png` | `player_sword_crouch_block_hit` | 3 | 15 |
| Crouch Hit - Sword | `crouch_hurt_spritesheet.png` | `player_sword_crouch_hurt` | 4 | 12 |
| Dash - Sword | `dash_spritesheet.png` | `player_sword_dash` | 11 | 20 |
| Dash Attack - Sword | `dash_attack_spritesheet.png` | `player_sword_dash_attack` | 11 | 15 |
| Roll - Sword | `roll_spritesheet.png` | `player_sword_roll` | 8 | 15 |
| Slide - Sword | `slide_spritesheet.png` | `player_sword_slide` | 10 | 15 |
| Wall Jump Land - Sword | `wall_land_spritesheet.png` | `player_sword_wall_land` | 4 | 15 |
| Wall Jump Slide - Sword | `wall_slide_spritesheet.png` | `player_sword_wall_slide` | 4 | 8 |
| Prone Idle - Sword | `prone_idle_spritesheet.png` | `player_sword_prone` | 9 | 6 |
| Prone Crawling - Sword | `prone_walk_spritesheet.png` | `player_sword_prone_walk` | 8 | 10 |
| Prone Hit - Sword | `prone_hurt_spritesheet.png` | `player_sword_prone_hurt` | 4 | 12 |
| Prone Death - Sword | `prone_death_spritesheet.png` | `player_sword_prone_death` | 5 | 12 |
| Prone Death Waking Up - Sword | `prone_revive_spritesheet.png` | `player_sword_prone_revive` | 5 | 12 |
| All Climb/Ledge - Sword (12 anims) | Same filenames under `sword/` | `player_sword_climb_*`, `player_sword_ledge_*` | (same as unarmed) | â€” |
| All Swim - Sword (6 anims) | Same filenames under `sword/` | `player_sword_swim_*` | (same as unarmed) | â€” |
| Push-Pull Idle/Push/Pull - Sword | `push_idle / push / pull_spritesheet.png` | `player_sword_push_idle`, etc. | 8 | 8/10 |
| Door Enter/Exit - Sword | `door_enter / door_exit_spritesheet.png` | `player_sword_door_enter`, etc. | 9/10 | 12 |
| Push Button Back - Sword | `button_back_spritesheet.png` | `player_sword_button_back` | 4 | 12 |
| Push Button Side - Sword | `button_spritesheet.png` | `player_sword_button` | 5 | 12 |
| Lever - Sword | `lever_spritesheet.png` | `player_sword_lever` | 9 | 12 |
| Pickup Standing/Crouch - Sword | `pickup / pickup_crouch_spritesheet.png` | `player_sword_pickup`, `player_sword_pickup_crouch` | 5/4 | 12 |
| Open Chest Back/Side - Sword | `chest_back / chest_side_spritesheet.png` | `player_sword_chest_back`, `player_sword_chest_side` | 6/5 | 10 |
| Rope Idle/Swing - Sword | `rope_idle / rope_swing_spritesheet.png` | `player_sword_rope`, `player_sword_rope_swing` | 4/7 | 6/10 |
| Sitting/Asleep/Talking/Victory/Drink - Sword | (same filenames under `sword/`) | `player_sword_sit`, etc. | (same counts) | â€” |

> **Pistol set** (present in ZIP 002 but not assigned here): stage to `assets/sprites/player/pistol/` now; wire to engine in the Arcade Mode milestone.

---

## 0.3 Phases at a Glance

| Phase | Title | Dependencies | Status |
|-------|-------|-------------|--------|
| 1 | Asset Extraction & Folder Setup | None | **Done v0.11.6** â€” 81 unarmed + 90 sword sheets extracted |
| 2 | Sprite Sheet Spec Update | Phase 1 | **Done v0.11.6** â€” frame counts verified (80Ã—80 px uniform) |
| 3 | AnimationRegistry Expansion | Phase 2 | **Done v0.11.6** â€” `loadUnarmedSheets()` + `loadSwordSheets()` (130+ keys) |
| 4 | EntityRenderer Key Routing | Phase 3 | **Done v0.11.6** â€” `player_sword_*` prefix fallthrough routing |
| 5 | Locomotion & Traversal Animations | Phase 4 | **Done v0.11.10** â€” climb/ledge/climb_idle states wired; `isClimbing`/`isOnLedge` flags on SimPlayer; detection logic is Phase 6 |
| 6 | Climb & Swim State Machine | Phase 5 | **Partial v0.11.51** â€” corner ledge grab/hang/climb and water-surface + side-bank water exit logic are live in `GameSimulator`; explicit `CLIMBABLE` tagging plus stance-gated wall contact (Yin climb attach, Yang wall slide) are implemented, with stance-sensitive swim tuning + blocked-bank/surface-jump handling now added |
| 7 | Interaction Animations | Phase 6 | **Partial v0.11.53** - runtime interaction animation bridge added for puzzle/objective markers (`lever`, `button`, `echo_trigger`) and pickup feedback, with deterministic fixture + regression coverage; broader door/chest/push-pull state families still pending |
| 8 | Weapon State System | Phase 4 | **Partial v0.11.54** â€” `weaponState` routing remains stance-coupled and now supports explicit runtime hot-swap input (`select_weapon_1`/`select_weapon_2`) with persistent Yang posture preference; combo-chain/combat-state integration remains |
| 9 | Unarmed Combo Chain | Phase 8 | Not started |
| 10 | Sword Combat System | Phase 8 | Not started |
| 11 | Block / Parry System | Phase 9-10 | **Partial v0.11.39** - runtime guard/parry input schema + front-facing block/parry behavior live; hold/toggle rebinding and full combat-state polish still pending |
| 12 | Social / Emote Animations | Phase 7 | Not started |
| 13 | Death, Revive & Prone System | Phase 5 | Not started |
| 14 | Testing & Validation | All | **Partial v0.11.51** â€” dedicated traversal fixtures + regression tests cover climb-tag gating, stance wall behavior, ledge-grab climb-out, water-exit snap, water-surface jump, and blocked-bank non-snap behavior |
| 15 | Complete Keybinding Scheme | Phase 8 | **Partial v0.11.52** - GDD baseline key map is now runtime-authoritative in Java (`KeyBindings` defaults + settings overrides + legacy `key_*` fallback); controller-path and full UI-side rebind surfaces remain |
| 16 | KeyBindings System (Configurable) | Phase 15 | **Partial v0.11.52** - `KeyBindings` now drives `InputPoller` and gameplay hotkey paths from `user_data/settings/settings.json`; in-game rebind UX and extended action-family wiring still pending |
| 17 | Controls Overlay (In-Game HUD) | Phase 16 | **Partial v0.11.52** - `F1` controls overlay now renders live bound keys from runtime `KeyBindings`; broader overlay/context parity remains in progress |

---

## 0.4 P0 Blocker Realignment Addendum (`2026-04-14 22:31:21 +01:00`)

This plan now explicitly supports `P0-10` blocker closure, not only asset/moveset breadth.

### Confirmed P0 blockers from current playtest loop

- No explicit, discoverable Yin/Yang stance-switch interaction in live input flow.
- Mission selection depends on dialogue/event routes that are not consistently discoverable.
- `activate_switches` objectives can be authored without guaranteed in-room switch affordances.
- Controller-path controls are underspecified in runtime behavior, even when keyboard fallback works.

### P0 animation/input bridge goals

1. Make stance state changes visible and testable from minute one.
2. Make mission start/select available without hidden dialogue dependencies.
3. Make objective interactions visually represented (or debug-visible) whenever required.
4. Align runtime controls behavior with GDD `10.3` before handing off to P1 tuning.

### Execution track (P0-A to P0-D)

| ID | Work item | Owner | Deliverable | Exit gate |
|----|-----------|-------|-------------|-----------|
| `P0-A` | Stance input + animation readability bridge | ENG-CORE + ENG-CLIENT | Deterministic stance-switch input route and visible stance posture/readability state | Tester can switch stance on demand and observe immediate visual/readability change |
| `P0-B` | Mission menu discoverability hardening | ENG-CLIENT | Direct mission-overlay entry path plus dialogue-route fallback | Tester can open mission list and start a mission in under 30 seconds from hub |
| `P0-C` | Objective interaction affordance pass | ENG-CORE + ENG-CLIENT | Guaranteed switch/objective contact affordances, with debug hitboxes when enabled | `activate_switches` objectives remain completable even when procedural switch NPCs are absent |
| `P0-D` | Controls matrix sync pass | ENG-CLIENT + DESIGN | Runtime controls table synchronized with GDD `10.3` and overlay labels | `F1` overlay and player expectations doc show the same actionable controls |

### Progress update (`2026-04-15 03:18:26 +01:00`)

- Extended P0 controls/combat runtime bridge:
  - `InputCommand.block` added and wired through input/replay logging paths.
  - Guard/parry live behavior added in simulator with directional front-block checks and parry stun response.
  - Block hit reaction animation states (`block_hit` / `block_hit_hard`) now route through runtime animation selection.
- Boss-fight stability fixes tied to P0-10 playtest blockers:
  - Time Leech minions now spawn with canonical type wire (`time_leech`) and active-cap guard.
  - Siren shield/add checks now scope to arena-local adds to avoid cross-room contamination.

### Progress update (`2026-04-15 21:40:12 +01:00`)

- Pivot implementation pass aligned to GDD stance-expression goals:
  - Alignment reference: GDD `§3.3` (Yin/Yang stance model) and `§10.3.5` / `§10.3.5 Jump, Wall Jump, and Swim Input Rules`.
  - Added deterministic stance-to-posture bridge in `GameSimulator`:
    - Yin stance now forces `weaponState=unarmed`.
    - Yang stance defaults to armed posture (`sword` fallback, `pistol` when equipped weapon implies pistol).
  - Added HUD readability cue in `HudRenderer`:
    - Lantern panel now shows `STANCE: <...>  POSTURE: <...>` for immediate tester feedback.
- Traversal-context bridge implemented for climb/swim onboarding readability:
  - Added corner ledge detection and state flow (`ledge_grab` -> `ledge_idle` -> `ledge_climb`).
  - Added water-surface detection (`atWaterSurface`) for distinct surface/submerged animation routing.
  - Added side-bank water exit resolver so jump near a solid bank snaps to reachable solid ground.
- Playtest logging coverage added:
  - `[Playtest][Posture]` events on runtime posture changes.
  - `[Playtest][Traversal]` events for ledge-grab, ledge-climb begin, and water-exit-bank transitions.

### Progress update (`2026-04-15 22:30:17 +01:00`)

- Traversal surface contract hardening (Phase 6 closure slice):
  - Added canonical `CLIMBABLE` tile id (`TileType.CLIMBABLE` / `WorldGenerator.CLIMBABLE`).
  - World generation now tags deterministic climb surfaces via `tagClimbableSurfaces(...)`.
  - Climb activation now requires contact with tagged climbable tiles (no generic solid-wall climb latch).
- Authored regression fixture pass (Phase 14 test-path stabilization):
  - Added dedicated layouts for traversal edge-cases:
    - `LevelLayout.buildTraversalLedgeFixtureLayout(...)`
    - `LevelLayout.buildWaterExitFixtureLayout(...)`
  - Added targeted regression tests in `GameSimulatorTest`:
    - `climbOnlyActivatesOnClimbableTaggedWalls`
    - `ledgeGrabTransitionsIntoLedgeClimbAndTopOut`
    - `waterExitSnapsPlayerToSolidBank`
- Client/debug visibility parity:
  - `CLIMBABLE` tiles now render distinctly in minimap/debug outputs and are treated as solid for standing/contact checks.

### Progress update (`2026-04-15 22:43:18 +01:00`)

- Stance-wall behavior pass completed for traversal readability:
  - `YIN` wall contact now attaches to climb state on tagged `CLIMBABLE` surfaces and supports up/down traversal.
  - `YANG` wall contact now routes to wall-slide behavior only (no climb attach).
- Regression coverage extended:
  - updated `climbOnlyActivatesOnClimbableTaggedWalls` to assert `YIN` stance semantics.
  - added `yangWallContactSlidesInsteadOfClimbing` for explicit `YANG` routing checks.

### Progress update (`2026-04-15 23:44:06 +01:00`)

- Phase 6 swim-tuning bridge pass:
  - Added stance-sensitive water movement caps/tuning in `GameSimulator` (`YIN` tighter control, `YANG` higher burst allowances).
  - Added playtest traversal log events for `water_surface_jump` and `water_exit_blocked`.
  - Added blocked-bank fallback guard so failed side-bank exits do not force invalid top-out placement.
- Dedicated fixture expansion for traversal edge coverage:
  - `LevelLayout.buildWaterSurfaceFixtureLayout(...)`
  - `LevelLayout.buildBlockedWaterExitFixtureLayout(...)`
- Regression coverage additions:
  - `waterSurfaceJumpBurstWorksWithoutBankExit`
  - `blockedWaterExitFallsBackToSurfaceJump`

### Progress update (`2026-04-15 23:58:40 +01:00`)

- Phase 16 runtime keybinding pass:
  - Added `KeyBindings` runtime layer in Java client.
  - `InputPoller` now consumes `KeyBindings` instead of hardcoded key constants.
  - `KeyBindings` supports both `settings.json` `keybindings` overrides and legacy fallback fields (`key_left`, `key_right`, `key_jump`, `key_dash`, `key_crouch`).
- Game hotkey integration pass:
  - `GameScreen` inventory/mission/map/debug/interact/pause routes now use the same binding table as player input polling.
  - Map routing now supports both shared tap/hold binding and split quick/full map bindings when authored.
- Phase 17 overlay parity pass:
  - `HudRenderer.renderControlsOverlay(...)` now renders live bound keys from runtime bindings.
- Regression coverage:
  - Added `KeyBindingsTest` for default mapping, override parsing, and legacy fallback parsing.

### Progress update (`2026-04-16 00:53:55 +01:00`)

- Phase 7 interaction readability bridge pass:
  - Added `SimPlayer` interaction state timers (`interactionState` / `interactionTimer`) and deterministic duration constants.
  - `GameSimulator` now queues interaction animations on objective affordance actions:
    - lever markers (`lever_*`) -> `lever`
    - button markers (`btn_*`) and echo-trigger markers (`echo_trigger_*`) -> `button`
    - pickup collection -> `pickup`
  - Interaction state now applies immediate same-tick animation readability and logs:
    - `[Playtest][Interaction] ... type=lever|button|echo_trigger`
- Fixture/test-path stabilization:
  - Added `LevelLayout.buildInteractionMarkerFixtureLayout(...)`.
  - Added `GameSimulatorTest` regressions:
    - `leverInteractionQueuesLeverAnimationFeedback`
    - `buttonInteractionQueuesButtonAnimationFeedback`
- Renderer pacing parity:
  - Added explicit interaction FPS routing in `EntityRenderer.playerFps(...)` for `lever`/`button`/`pickup` and related interaction keys.

### Progress update (`2026-04-16 01:36:22 +01:00`)

- Phase 8 runtime hot-swap closure slice:
  - Added additive wire fields to `InputCommand`: `select_weapon_1` and `select_weapon_2`.
  - `InputPoller` now emits posture hot-swap input from `KeyBindings` actions.
  - `KeyBindings` defaults now include `1`/`2` posture bindings and expose them in controls preset summaries.
- Stance/posture behavior hardening:
  - Added `SimPlayer.yangPreferredWeaponState` so Yang posture preference persists across ticks and stance cycles.
  - `GameSimulator` now applies direct posture select input with `[Playtest][PostureInput]` traces while preserving Yin hard-lock to unarmed posture.
  - Inventory equip/unequip now clears temporary Yang posture override to avoid stale posture state.
- Readability + regression updates:
  - `F1` controls overlay now includes posture select bindings.
  - Added regression tests for Yang hot-swap persistence and Yin-lock behavior.
  - Added `InputCommandTest` roundtrip coverage for new additive input fields.

### Validation additions for this plan

- Add a smoke-test path that verifies:
  - stance switching input is accepted and mirrored in HUD/debug readouts;
  - mission overlay can be opened and mission started without special dialogue branching;
  - at least one `activate_switches` objective is completable in a fresh campaign session.
- Update animation QA to include readability checks:
  - stance silhouette clarity while idle/moving/attacking;
  - clear distinction between interaction affordances (switch/lever/mission contact volumes).

---

## PHASE 1 â€” Asset Extraction & Folder Setup

**Goal:** Get all sprite sheets out of the ZIPs and into the engine asset tree with correct names.

### 1.1 Create folder structure

```
java/client/src/main/resources/assets/sprites/player/
â”œâ”€â”€ unarmed/          â† all unarmed sheets (renamed per Â§0.2 table)
â”œâ”€â”€ sword/            â† all sword sheets (renamed per Â§0.2 table)
â””â”€â”€ pistol/           â† extracted but not yet wired (Arcade Mode later)
```

### 1.2 Write extraction script

Create `tools/extract_animations.py`. This script:
- Opens both ZIPs
- Iterates over all `*-Sheet.png` entries
- Applies the mapping table (Â§0.2) to rename each file
- Writes to `java/client/src/main/resources/assets/sprites/player/unarmed/` or `/sword/` or `/pistol/`
- Skips duplicate sheets (ZIP 002 re-exports all unarmed sheets â€” skip if unarmed/ already populated)
- Prints a report: total extracted, skipped, unmapped

**Key mappings the script must handle:**

```python
UNARMED_MAP = {
    "001-Standing Idle-Sheet.png":                "idle_spritesheet.png",
    "002-Standing Fighting-Sheet.png":            "combat_idle_spritesheet.png",
    "003-Standing Idly-Sheet.png":                "fidget_spritesheet.png",
    "002-Standing Walk-Sheet.png":                "walk_spritesheet.png",
    "001-Standing Direct Punch Combo-Sheet.png":  "punch1_spritesheet.png",
    "002-Standing Cross Punch Combo-Sheet.png":   "punch2_spritesheet.png",
    "003-Standing Kick-Sheet.png":                "kick_spritesheet.png",
    "001-Standing Block Idle-Sheet.png":          "block_idle_spritesheet.png",
    "001-Standing Block Hit (Normal)-Sheet.png":  "block_hit_normal_spritesheet.png",
    "001-Standing Block Hit (Hard)-Sheet.png":    "block_hit_hard_spritesheet.png",
    "001-Standing Hit Upper Body-Sheet.png":      "hurt_upper_spritesheet.png",
    "002-Standing Hit Lower Body-Sheet.png":      "hurt_lower_spritesheet.png",
    "001-Standing Death(Defeat) A-Sheet.png":     "death_spritesheet.png",
    "001-Standing Death A Getting Up-Sheet.png":  "revive_spritesheet.png",
    "001-Standing Death(Defeat) B-Sheet.png":     "death2_spritesheet.png",
    "001-Standing Death(Defeat) B Getting Up-Sheet.png": "revive2_spritesheet.png",
    "001-Run-Sheet.png":                          "run_spritesheet.png",
    "002-Run Skid Turn-Sheet.png":                "skid_spritesheet.png",
    "001-Run Flying Kick-Sheet.png":              "run_kick_spritesheet.png",
    "004-Run Stop-Sheet.png":                     "run_stop_spritesheet.png",
    "001-Jump-Sheet.png":                         "jumpfall_spritesheet.png",
    "002-Jump Front Flip-Sheet.png":              "flip_spritesheet.png",
    "001-Jump Direct Punch Combo-Sheet.png":      "air_punch1_spritesheet.png",
    "002-Jump Cross Punch Combo-Sheet.png":       "air_punch2_spritesheet.png",
    "003-Jump Kick-Sheet.png":                    "air_kick_spritesheet.png",
    "001-Jump Block Idle-Sheet.png":              "air_block_spritesheet.png",
    "002-Jump Block Hit-Sheet.png":               "air_block_hit_spritesheet.png",
    "001-Crouch Idle-Sheet.png":                  "crouch_idle_spritesheet.png",
    "002-Crouch Walk-Sheet.png":                  "crouch_walk_spritesheet.png",
    "001-Crouch Punch-Sheet.png":                 "crouch_punch_spritesheet.png",
    "003-Crouch Kick-Sheet.png":                  "crouch_kick_spritesheet.png",
    "001-Crouch Block Idle-Sheet.png":            "crouch_block_spritesheet.png",
    "002-Crouch Block Hit-Sheet.png":             "crouch_block_hit_spritesheet.png",
    "005-Crouch Hit-Sheet.png":                   "crouch_hurt_spritesheet.png",
    "001-Climb Idle (Back)-Sheet.png":            "climb_idle_back_spritesheet.png",
    "002-Climb Idle (Side)-Sheet.png":            "climb_idle_side_spritesheet.png",
    "001-Climb (Up) (Down) (Back)-Sheet.png":     "climb_back_spritesheet.png",
    "002-Climb (Up) (Down) (Side)-Sheet.png":     "climb_side_spritesheet.png",
    "003-Climb (Right)-Sheet.png":                "climb_right_spritesheet.png",
    "004-Climb (Left)-Sheet.png":                 "climb_left_spritesheet.png",
    "001-Climb Ledge Grab (Back)-Sheet.png":      "ledge_grab_back_spritesheet.png",
    "002-Climb Ledge Idle (Back)-Sheet.png":      "ledge_idle_back_spritesheet.png",
    "003-Climb Ledge Climbing (Back)-Sheet.png":  "ledge_climb_back_spritesheet.png",
    "004-Climb Ledge Grab (Side)-Sheet.png":      "ledge_grab_spritesheet.png",
    "005-Climb Ledge Idle (Side)-Sheet.png":      "ledge_idle_spritesheet.png",
    "006-Climb Ledge Climbing (Side)-Sheet.png":  "ledge_climb_spritesheet.png",
    "001-Water Surface Idle-Sheet.png":           "swim_surface_idle_spritesheet.png",
    "002-Water Surface Swimming-Sheet.png":       "swim_surface_spritesheet.png",
    "001-Water Bottom Idle-Sheet.png":            "swim_idle_spritesheet.png",
    "002-Water Bottom Swimming (Front)-Sheet.png":"swim_spritesheet.png",
    "003-Water Bottom Swimming (Up)-Sheet.png":   "swim_up_spritesheet.png",
    "004-Water Bottom Swimming (Down)-Sheet.png": "swim_down_spritesheet.png",
    "001-Prone Idle-Sheet.png":                   "prone_idle_spritesheet.png",
    "002-Prone Crawling-Sheet.png":               "prone_walk_spritesheet.png",
    "003-Prone Hit-Sheet.png":                    "prone_hurt_spritesheet.png",
    "001-Prone Death(Defeat)-Sheet.png":          "prone_death_spritesheet.png",
    "002-Prone Death(Defeat) Waking Up-Sheet.png":"prone_revive_spritesheet.png",
    "009-Dash-Sheet.png":                         "dash_spritesheet.png",
    "010-Roll-Sheet.png":                         "roll_spritesheet.png",
    "011-Slide-Sheet.png":                        "slide_spritesheet.png",
    "001-Wall Jump Land-Sheet.png":               "wall_land_spritesheet.png",
    "002-Wall Jump Slide-Sheet.png":              "wall_slide_spritesheet.png",
    "001-Push-Pull Idle-Sheet.png":               "push_idle_spritesheet.png",
    "002-Push-Sheet.png":                         "push_spritesheet.png",
    "003-Pull-Sheet.png":                         "pull_spritesheet.png",
    "001-Door Enter-Sheet.png":                   "door_enter_spritesheet.png",
    "002-Door Exit-Sheet.png":                    "door_exit_spritesheet.png",
    "002-Push Button (Side)-Sheet.png":           "button_spritesheet.png",
    "003-Lever-Sheet.png":                        "lever_spritesheet.png",
    "001-Pickup Standing-Sheet.png":              "pickup_spritesheet.png",
    "002-Pickup Crouch-Sheet.png":                "pickup_crouch_spritesheet.png",
    "001-Open Chest (Back)-Sheet.png":            "chest_back_spritesheet.png",
    "002-Open Chest (Side)-Sheet.png":            "chest_side_spritesheet.png",
    "001- Rope Hanging Idle-Sheet.png":           "rope_idle_spritesheet.png",
    "002- Rope Swinging-Sheet.png":               "rope_swing_spritesheet.png",
    "001-Sitting-Sheet.png":                      "sit_spritesheet.png",
    "002-Asleep-Sheet.png":                       "sleep_spritesheet.png",
    "003-Talking-Sheet.png":                      "talk_spritesheet.png",
    "004-Victory-Sheet.png":                      "victory_spritesheet.png",
    "005-Drink-Sheet.png":                        "drink_spritesheet.png",
    "001- Dance Twerk-Sheet.png":                 "dance_spritesheet.png",
}
```

For the sword `Standing Attack Combo` (8 sub-sheets), the script must detect and enumerate them:
```python
# Sheets named identically, in different parent folders (numbered 1-8 in path)
# Extract as: attack_combo_d0..d7_spritesheet.png
```

### 1.3 Verification checklist

After running the script, verify manually:
- [ ] All unarmed files present and non-zero size
- [ ] All sword files present and non-zero size
- [ ] Pistol files staged in `/pistol/` (not yet wired)
- [ ] No ZIP Sheet.png left unmapped (script reports this)
- [ ] Spot-check: open 3 sheets in an image viewer, confirm 80 px tall, RGBA, transparent background

### 1.4 Test: launcher visual smoke test

```
python launcher/launcher.py
```
- Launch the game
- Confirm no crash on startup (AnimationRegistry loads all sheets)
- Confirm placeholder fallback still active (sheets are in place but not registered yet â€” engine uses magenta dot)

---

## PHASE 2 â€” Sprite Sheet Spec Update

**Goal:** Update `docs/sprite_sheet_spec.md` to be the authoritative contract for all new animations.

### Changes to `docs/sprite_sheet_spec.md`

1. **Update frame sizes table** â€” Player canvas is confirmed `80Ã—80 px` (consistent with existing spec, confirmed by ZIP dimension check). No change needed to the format rules.

2. **Replace the Player animations table** with the full table from Â§0.2 of this plan. This is the source of truth for:
   - File path
   - Frame count
   - FPS
   - Loop behaviour

3. **Add weapon subfolder layout:**
```
assets/sprites/player/
â”œâ”€â”€ unarmed/          (79 sheets)
â”œâ”€â”€ sword/            (74 sheets)
â””â”€â”€ pistol/           (reserved â€” Arcade Mode)
```

4. **Add a `jumpfall_spritesheet.png` split note** â€” 10-frame sheet: frames 0-4 = jump arc, frames 5-9 = fall arc. `registerJumpFall()` in `AnimationRegistry` handles the slice.

5. **Add combo sheet note** â€” Standing Attack Combo (sword) is 8 sub-sheets Ã— 35 frames each. Registered as separate directional keys `player_sword_attack` through `player_sword_attack_d7`.

No code changes in this phase â€” documentation only.

---

## PHASE 3 â€” AnimationRegistry Expansion

**Goal:** Register all new animation keys so the engine can serve any frame on request.

**File:** `java/client/src/main/java/com/indieniinja/client/rendering/AnimationRegistry.java`

### 3.1 Add `loadUnarmedSheets(FileHandle unarmedDir)` method

This replaces/extends the existing `loadSpriteSheets()`. It registers all 79 unarmed keys using `sliceAndRegister()` and `sliceSubsetAndRegister()`.

Critical registrations:
```java
// Jump/Fall â€” split the 10-frame sheet at frame boundary 5
sliceSubsetAndRegister(unarmedDir, "player_jump", "jumpfall_spritesheet.png", 10, 0, 5);
sliceSubsetAndRegister(unarmedDir, "player_fall", "jumpfall_spritesheet.png", 10, 5, 5);

// Aliases that share sheets
frames.put("player_slow_walk",    frames.get("player_walk"));
frames.put("player_wall_hang",    frames.get("player_climb_idle_side"));
frames.put("player_air_spin",     frames.get("player_flip"));
```

All 79 keys from the unarmed section of Â§0.2 must be explicitly registered. Missing sheets still fall through to the magenta placeholder.

### 3.2 Add `loadSwordSheets(FileHandle swordDir)` method

Registers all 74 sword keys from the sword section of Â§0.2.

Critical: the 8 combo sub-sheets for `Standing Attack Combo` and the 5 sub-sheets for air/crouch combos. Each is a separate 35-frame (or 17-frame) PNG:
```java
for (int d = 0; d <= 7; d++) {
    String fname = "attack_combo_d" + d + "_spritesheet.png";
    String key   = (d == 0) ? "player_sword_attack" : "player_sword_attack_d" + d;
    sliceAndRegister(swordDir, key, fname, 35);
}
for (int d = 0; d <= 4; d++) {
    String fname = "air_attack_d" + d + "_spritesheet.png";
    String key   = (d == 0) ? "player_sword_air_attack" : "player_sword_air_attack_d" + d;
    sliceAndRegister(swordDir, key, fname, 17);
}
// Same pattern for crouch combos
```

Sword locomotion aliases:
```java
frames.put("player_sword_slow_walk",   frames.get("player_sword_walk"));
frames.put("player_sword_wall_hang",   frames.get("player_sword_climb_idle_side"));
```

### 3.3 Update `playerFps()` in `EntityRenderer`

`EntityRenderer.playerFps(String animState)` maps state strings to FPS. Add all new states from Â§0.2 (climb, swim, prone, roll, slide, block, combo attacks, interactions, emotes). The method is a `switch` â€” add a case per state.

### 3.4 Update startup call in `GameScreen`

```java
// In GameScreen.create() or wherever AnimationRegistry is initialised:
FileHandle sprites = Gdx.files.internal("assets/sprites/player");
anims.loadUnarmedSheets(sprites.child("unarmed"));
anims.loadSwordSheets(sprites.child("sword"));
// loadEnemySprites and loadNpcSprites remain unchanged
```

### 3.5 Test: registry content dump (debug mode only)

Add a temporary debug log call on startup:
```java
// Gdx.app.log("AnimReg", "Loaded " + frames.size() + " animation keys");
```
Expected: ~160 keys (79 unarmed + 74 sword + ~7 shared/existing). Confirm count in console.

---

## PHASE 4 â€” EntityRenderer Key Routing

**Goal:** Make `EntityRenderer` select the correct key based on weapon state, without changing any state machine logic.

**File:** `java/client/src/main/java/com/indieniinja/client/rendering/EntityRenderer.java`

### 4.1 Add `WeaponState` to `PlayerState`

`PlayerState` (in `core/network/`) is the network-serialised player snapshot. Add:
```java
public String weaponState = "unarmed"; // "unarmed" | "sword" | "pistol"
```

This must be populated in `GameSimulator` from `SimPlayer.weaponState` (see Phase 8).

### 4.2 Update key construction in `EntityRenderer.renderPlayer()`

Current:
```java
String animKey = "player_" + state;
```

Replace with:
```java
String prefix = "player";
if ("sword".equals(p.weaponState)) {
    String swordKey = "player_sword_" + state;
    if (anims.hasKey(swordKey)) {
        prefix = "player_sword";
    }
    // Fall through to unarmed if sword key not registered yet
}
String animKey = prefix + "_" + state;
```

Add `AnimationRegistry.hasKey(String key)`:
```java
public boolean hasKey(String key) {
    return frames.containsKey(key) && frames.get(key) != null;
}
```

This makes the weapon state transparent to the animation state machine â€” the state machine only sets `animState = "idle"`, `"run"`, etc. The renderer prepends the weapon prefix. No state machine changes required in this phase.

### 4.3 Test

- [ ] Launch game, move player â€” confirm all locomotion states render unarmed sprites (sword key falls through to unarmed until Phase 8 wires weaponState)
- [ ] No NPE or missing key crash
- [ ] Facing flip still works (check left/right movement)
- [ ] Particle effects (run dust, jump puff, land puff) still fire at correct positions

---

## PHASE 5 â€” Locomotion & Traversal Animations

**Goal:** Replace all placeholder locomotion sprites with real ones and verify they sync correctly with physics states.

### 5.1 Animations to verify in this phase

These states already exist in `stepPlayerAnimationState()` â€” just confirm the new sheets render correctly:

| State string | Key | New sheet | Notes |
|---|---|---|---|
| `idle` | `player_idle` | `idle_spritesheet.png` | 8f at 8 fps |
| `run` | `player_run` | `run_spritesheet.png` | 8f at 12 fps |
| `slow_walk` | `player_slow_walk` | (alias of walk) | â€” |
| `dash` | `player_dash` | `dash_spritesheet.png` | 11f at 20 fps â€” was 7f, now 11f, update frame count |
| `jump` | `player_jump` | `jumpfall_spritesheet.png` f0-4 | New split logic |
| `fall` | `player_fall` | `jumpfall_spritesheet.png` f5-9 | New state â€” currently "jump" handles both |
| `wall_slide` | `player_wall_slide` | `wall_slide_spritesheet.png` | 4f, same count |
| `crouch` | `player_crouch` | `crouch_idle_spritesheet.png` | 9f â€” was reusing idle, now dedicated |
| `crouch_walk` | `player_crouch_walk` | `crouch_walk_spritesheet.png` | 8f |

### 5.2 Add `fall` as a distinct state

Currently `stepPlayerAnimationState()` uses `"jump"` for all airborne states. Split it:
```java
// In GameSimulator.stepPlayerAnimationState():
if (!p.onGround && !sp.isWallSliding) {
    sp.animState = (p.vy < 0f) ? "jump" : "fall";  // vy < 0 = ascending
}
```

Add `player_fall` FPS to `EntityRenderer.playerFps()`:
```java
case "fall" -> 10f;
```

### 5.3 Add new locomotion states not currently in state machine

Add to `stepPlayerAnimationState()` (in priority order â€” these sit between existing checks):

```java
// After wall_slide check, before jump/fall:
if (sp.isRolling) { sp.animState = "roll"; return; }
if (sp.isSliding) { sp.animState = "slide"; return; }

// After idle check:
if (sp.animState.equals("idle") && sp.prevAnimState.equals("run") && !cmd.left && !cmd.right) {
    sp.animState = "run_stop";  // brief non-looping stop
}
```

Add `isRolling` and `isSliding` booleans to `SimPlayer` (see Phase 6 for full movement wiring).

### 5.4 Test â€” Locomotion Checklist

Launch via `python launcher/launcher.py`. Confirm each state visually:

- [ ] Idle: 8-frame loop, no jitter
- [ ] Walk left/right: 8-frame loop, correct facing flip
- [ ] Run (hold opposite direction briefly to test): skid animation fires (4 frames, then transition)
- [ ] Run stop: 3-frame non-looping animation plays on decelerate
- [ ] Dash: 11-frame non-looping burst â€” confirm it does not loop
- [ ] Jump ascent: frames 0-4 of jumpfall sheet
- [ ] Jump descent (apex â†’ fall): transitions to frames 5-9 of jumpfall sheet
- [ ] Crouch: 9-frame idle while crouched
- [ ] Crouch walk: 8-frame loop while moving crouched
- [ ] Wall slide: 4-frame loop against wall
- [ ] Double-jump front flip: 6-frame non-looping flip on second jump input

---

## PHASE 6 â€” Climb & Swim State Machine

**Goal:** Wire the new climb and swim animation states to physics, since neither exists in the current state machine.

### 6.1 Add climb/ledge/water-context fields to `SimPlayer`

```java
// SimPlayer.java â€” runtime context fields:
public boolean isClimbing      = false;  // on a climbable surface
public boolean isOnLedge       = false;  // hanging from ledge edge
public boolean atWaterSurface  = false;  // at water surface level
public boolean isLedgeClimbing = false;  // climbing up from a ledge hang
public float   ledgeTargetX    = 0f;     // target top-out x
public float   ledgeTargetY    = 0f;     // target top-out y
public float   ledgeHangY      = 0f;     // suspended y while hanging
public float   ledgeClimbTimer = 0f;     // climb-up animation timer
```

Current implementation computes climb/ledge/water context in `GameSimulator` each tick using
tile probes from `SpatialHash` plus existing `PhysicsState` flags (`inWater`, `onWall`, `onGround`).
Full authored `CLIMBABLE` tile tagging remains a follow-up.

### 6.2 Add climb/swim/ledge branches to `stepPlayerAnimationState()`

Insert after wall-slide check and before airborne check:

```java
// LEDGE
if (sp.isOnLedge) {
    sp.animState = "ledge_idle";
    return;
}
if (sp.isLedgeClimbing) {
    sp.animState = "ledge_climb";
    return;
}

// CLIMBING
if (sp.isClimbing) {
    sp.animState = Math.abs(p.vy) > 0.1f ? "climb" : "climb_idle";
    return;
}

// SWIMMING
if (p.inWater) {
    if (sp.atWaterSurface) {
        sp.animState = (Math.abs(p.vx) > 0.1f) ? "swim_surface" : "swim_surface_idle";
    } else {
        if (Math.abs(p.vy) > 0.15f) sp.animState = p.vy < 0f ? "swim_up" : "swim_down";
        else                        sp.animState = Math.abs(p.vx) > 0.1f ? "swim" : "swim_idle";
    }
    return;
}
```

### 6.3 Swim physics stub

Current status:
- Existing medium physics drag/cap behavior remains authoritative.
- New runtime bridge adds:
  - `atWaterSurface` detection for surface animation routing.
  - jump-at-surface upward burst behavior.
  - banked water exit snapping to nearby valid solid ground.

Follow-up remains open:
- explicit buoyancy/gravity model for submerged movement tuning.
- authored water movement constants per stance for final GDD feel pass.

### 6.4 Test â€” Climb & Swim Checklist

- [ ] Approach climbable wall: `climb_idle_side` animation plays
- [ ] Press up on climbable wall: `climb_side` animation plays (6f loop)
- [ ] Press left/right on climbable wall: `climb_left` / `climb_right` plays
- [ ] Reach top of wall: `ledge_grab` â†’ `ledge_idle` â†’ `ledge_climb` (pull-up) sequence
- [ ] Walk into water: transition to `swim_surface_idle`
- [ ] Move in water: `swim_surface` plays
- [ ] Dive: `swim_idle` plays
- [ ] Move horizontally underwater: `swim` plays
- [ ] Press up underwater: `swim_up` plays
- [ ] Press down underwater: `swim_down` plays
- [ ] Exit water: transition back to `idle` / `jump`

---

## PHASE 7 â€” Interaction Animations

**Goal:** Play interaction animations when the player uses E on interactive objects (doors, levers, chests, buttons, pickups).

### 7.1 Add `interactionState` to `SimPlayer`

```java
public String interactionState = "";    // "", "door_enter", "door_exit", "lever", "button", "chest_side", "chest_back", "pickup", "pickup_crouch", "push_idle", "push", "pull"
public float  interactionTimer = 0f;    // counts down duration; 0 = finished
```

When `interactionTimer > 0`, the state machine returns `interactionState` and blocks all other state changes.

### 7.2 Wire to E-key interactions in `GameSimulator`

When an interaction fires (player presses E near interactive object):
```java
sp.interactionState = resolveInteractionAnim(objectType, sp.isCrouching);
sp.interactionTimer = getInteractionDuration(sp.interactionState);
// freeze position during interaction (optional: lock input for half the duration)
```

Helper tables:
```
door_enter  â†’  19 frames / 12 fps = 1.58 s
door_exit   â†’  17 frames / 12 fps = 1.42 s
lever       â†’  18 frames / 12 fps = 1.50 s
button      â†’   9 frames / 12 fps = 0.75 s
chest_back  â†’  12 frames / 10 fps = 1.20 s
chest_side  â†’  11 frames / 10 fps = 1.10 s
pickup      â†’   5 frames / 12 fps = 0.42 s
pickup_crouch â†’ 4 frames / 12 fps = 0.33 s
```

### 7.3 Push/pull states

`push_idle`, `push`, `pull` are looping â€” they remain active while the player holds against a pushable object. These are controlled by physics contact, not a timer.

### 7.4 Add interaction states to `stepPlayerAnimationState()`

Insert at highest priority (top of method, before teleport):
```java
if (sp.interactionTimer > 0f) {
    sp.interactionTimer -= DT;
    sp.animState = sp.interactionState;
    if (sp.interactionTimer <= 0f) sp.interactionState = "";
    return;
}
if (sp.isPushing) { sp.animState = "push"; return; }
if (sp.isPulling) { sp.animState = "pull"; return; }
if (sp.isPushIdle) { sp.animState = "push_idle"; return; }
```

### 7.5 Test â€” Interaction Checklist

- [ ] Walk through a door: `door_enter` plays full 19 frames, then room transition fires
- [ ] Exit door: `door_exit` plays 17 frames
- [ ] Activate lever (E): `lever` plays 18 frames, lever toggles at frame 9
- [ ] Push button (E): `button` plays 9 frames, trigger fires at frame 5
- [ ] Open chest facing side: `chest_side` plays 11 frames
- [ ] Open chest facing back: `chest_back` plays 12 frames
- [ ] Pick up item standing: `pickup` plays 5 frames, item added to inventory
- [ ] Pick up item crouching: `pickup_crouch` plays 4 frames
- [ ] Push crate (hold into it): `push_idle` â†’ `push` loop

---

## PHASE 8 â€” Weapon State System

**Goal:** Allow the player to equip/unequip a sword, and have all animations switch to the sword set transparently.

### 8.1 Runtime posture field in `SimPlayer`

```java
// SimPlayer.java
public String weaponState = "unarmed"; // "unarmed" | "sword" | "pistol"
```

### 8.2 Equip logic in `GameSimulator`

Current bridge logic is stance-first for readability:

```java
if ("yin".equals(sp.stanceMode)) return "unarmed";
String equipped = weaponStateFromEquippedItem(sp.inventory.equippedWeapon);
return "unarmed".equals(equipped) ? "sword" : equipped;
```

`syncWeaponStateForStance(sp)` is called during input processing and after equip/unequip actions.
This gives deterministic posture feedback while preserving equipped-item awareness.

### 8.3 Propagate to `PlayerState` network schema

```java
// In GameSimulator snapshot builder:
ps.weaponState = sp.weaponState; // "unarmed" / "sword" / "pistol"
```

`PlayerState.weaponState` field added in Phase 4.1.

### 8.4 Test â€” Weapon State Checklist

- [ ] Default spawn: unarmed animations play
- [ ] Switch stance to Yang: posture switches to armed (`sword` fallback or equipped weapon posture)
- [ ] Switch stance to Yin: posture switches back to unarmed
- [ ] Equip pistol item while in Yang: posture resolves to pistol
- [ ] Weapon state persists across death/respawn (check `SaveManager`)
- [ ] In co-op: each player can have a different weapon state; confirm they render independently

---

## PHASE 9 â€” Unarmed Combo Chain

**Goal:** Replace the single-hit `isAttacking` system with a full 3-hit ground combo, 3-hit air combo, and 2-hit crouch combo.

### 9.1 New `SimPlayer` combo fields

```java
public int   comboStep       = 0;     // 0=none, 1=hit1, 2=hit2, 3=hit3
public float comboWindow     = 0f;    // time remaining to chain next hit
public float attackAnimTimer = 0f;    // tracks current hit animation duration
public boolean isBlocking    = false;
public float blockTimer      = 0f;
```

Constants (add to `PhysicsConstants`):
```java
public static final float COMBO_WINDOW     = 0.22f;  // 13 ticks â€” input window after each hit
public static final float COMBO_HIT1_DUR   = 6f / 15f;   // 6 frames @ 15 fps = 0.40 s
public static final float COMBO_HIT2_DUR   = 8f / 15f;   // 8 frames @ 15 fps = 0.53 s
public static final float COMBO_HIT3_DUR   = 6f / 15f;   // 6 frames @ 15 fps = 0.40 s
public static final float COMBO_RESET_COOL = 0.5f;       // full cooldown after hit 3
```

### 9.2 Combo state machine in `GameSimulator.stepPlayerInput()`

Replace current `attackJustPressed` block:

```java
if (attackJustPressed) {
    if (comboStep == 0 && comboWindow == 0f) {
        // Begin combo
        startComboHit(sp, p, 1);
    } else if (comboStep == 1 && comboWindow > 0f) {
        startComboHit(sp, p, 2);
    } else if (comboStep == 2 && comboWindow > 0f) {
        startComboHit(sp, p, 3);
    }
}

// Tick combo timers
if (sp.attackAnimTimer > 0f) {
    sp.attackAnimTimer -= DT;
    if (sp.attackAnimTimer <= 0f) {
        sp.comboWindow = COMBO_WINDOW;  // open window for next hit
        sp.isAttacking = false;
    }
}
if (sp.comboWindow > 0f) {
    sp.comboWindow -= DT;
    if (sp.comboWindow <= 0f) sp.comboStep = 0;  // window expired, reset
}
```

```java
private void startComboHit(SimPlayer sp, PhysicsState p, int step) {
    sp.comboStep       = step;
    sp.isAttacking     = true;
    sp.comboWindow     = 0f;
    sp.attackAnimTimer = switch (step) {
        case 1 -> COMBO_HIT1_DUR;
        case 2 -> COMBO_HIT2_DUR;
        case 3 -> COMBO_HIT3_DUR;
        default -> 0f;
    };
    // Hitbox: same 48Ã—40 px reach as before; step 3 (kick) gets +8 px vertical
    applyMeleeHitbox(sp, p, step);
}
```

### 9.3 Map combo steps to animation states

Update `stepPlayerAnimationState()` â€” in the `isAttacking` branch:
```java
if (sp.isAttacking) {
    boolean inAir    = !p.onGround;
    boolean crouched = cmd.crouch && p.onGround;
    sp.animState = switch (sp.comboStep) {
        case 1 -> crouched ? "crouch_punch"  : (inAir ? "air_punch1"  : "punch1");
        case 2 -> crouched ? "crouch_kick"   : (inAir ? "air_punch2"  : "punch2");
        case 3 -> crouched ? "crouch_kick"   : (inAir ? "air_kick"    : "kick");
        default -> "punch1";
    };
    return;
}
```

### 9.4 Hitbox scaling per step

| Step | Reach (X) | Height (Y) | Notes |
|------|-----------|------------|-------|
| 1 (Direct Punch) | 40 px | 40 px | Forward jab |
| 2 (Cross Punch) | 48 px | 40 px | Wider hook |
| 3 (Kick) | 52 px | 52 px | Extended leg |
| Air Kick (step 3 in air) | 48 px | 60 px | Downward arc |
| Crouch Punch (step 1) | 36 px | 28 px | Low reach |
| Crouch Kick (step 2) | 48 px | 30 px | Sweep |

### 9.5 Test â€” Unarmed Combo Checklist

- [ ] Press attack once: `punch1` plays (6 frames), hitbox active frames 2-5
- [ ] Press attack during combo window after hit 1: `punch2` plays (8 frames), hitbox active frames 2-6
- [ ] Press attack during combo window after hit 2: `kick` plays (6 frames), hitbox active frames 2-5
- [ ] No press during combo window: combo resets to step 0 after window expires
- [ ] Press attack during attack animation (not window): input buffered, fires when window opens
- [ ] Combo while airborne: `air_punch1` â†’ `air_punch2` â†’ `air_kick` sequence
- [ ] Combo while crouched: `crouch_punch` â†’ `crouch_kick` (2-hit only)
- [ ] Run + attack: `run_kick` plays as standalone (no combo, single hit)
- [ ] Enemy takes correct damage per hit (1 HP each)
- [ ] Stun on hit 3 is longer than on hit 1 (3-hit combo ends with a knockback kick)

---

## PHASE 10 â€” Sword Combat System

**Goal:** Implement the sword combat system using the new sword animation set. Three attack configurations: ground (8-direction combo + stab), air (5-direction + air stab), crouch (5-direction + crouch stab). Plus the sword-exclusive `Dash Attack`.

### 10.1 Sword combo state additions

Extend the combo system from Phase 9 to handle directional attacks. Add:
```java
public int attackDirection = 0;  // 0=forward, 1=up, 2=down, 3=diag-up, 4=diag-down
                                 // (5-7 used for wide arc variants)
```

`attackDirection` is set at the moment of attack input from the current `cmd.up` / `cmd.down` + `cmd.left` / `cmd.right` combination:
```java
if (cmd.up && cmd.right)   sp.attackDirection = 3;  // diag-up-forward
else if (cmd.up)           sp.attackDirection = 1;  // straight up
else if (cmd.down)         sp.attackDirection = 2;  // straight down
else                       sp.attackDirection = 0;  // forward
```

### 10.2 Map sword directions to animation keys

```java
// In stepPlayerAnimationState() when weaponState == SWORD and isAttacking:
String dirSuffix = (sp.attackDirection > 0) ? "_d" + sp.attackDirection : "";
sp.animState = switch (sp.comboStep) {
    case 1, 2, 3 -> "sword_attack" + dirSuffix;    // maps to player_sword_attack or player_sword_attack_d1..d7
    case 99 -> "sword_stab";                        // stab: triggered by down+attack while not moving
    default -> "sword_attack";
};
```

For finisher (stab), trigger when: `cmd.attack` + !`cmd.left` + !`cmd.right` + `cmd.down` and `comboStep == 3`.

### 10.3 Sword Dash Attack

The Dash Attack is unique to the sword â€” only fires when the player is actively dashing and presses attack:
```java
if (sp.isDashing && attackJustPressed && sp.weaponState == SWORD) {
    sp.isAttacking     = true;
    sp.attackAnimTimer = 11f / 15f;  // 11 frames @ 15 fps
    sp.comboStep       = 99;         // special step for dash attack
    sp.animState       = "sword_dash_attack";
    // Hitbox: extends full dash reach (16 px/tick Ã— 0.16 s = ~80 px forward)
    applyMeleeHitbox(sp, p, 99);
}
```

### 10.4 Sword hitbox values

| Attack | Reach (X) | Height | Notes |
|--------|-----------|--------|-------|
| Ground combo (forward) | 64 px | 44 px | Longer than unarmed |
| Ground combo (up) | 44 px | 72 px | Upward arc |
| Ground combo (down) | 36 px | 28 px | Downward sweep |
| Air combo | 56 px | 60 px | Air slash |
| Crouch combo | 52 px | 30 px | Low sweep |
| Stab | 72 px | 28 px | Long narrow thrust |
| Dash attack | 80 px | 40 px | Full dash length |

### 10.5 Test â€” Sword Combat Checklist

- [ ] Equip sword (Phase 8), then attack: `player_sword_attack` (35-frame sheet) plays
- [ ] Attack + up: `player_sword_attack_d1` plays (upward slash direction)
- [ ] Attack + down: `player_sword_attack_d2` plays (downward slash)
- [ ] Air sword attack: `player_sword_air_attack` plays (17-frame sheet)
- [ ] Crouch sword attack: `player_sword_crouch_attack` plays (17-frame sheet)
- [ ] Down + attack (stationary, grounded): `player_sword_stab` plays (5 frames)
- [ ] Dash â†’ attack (sword): `player_sword_dash_attack` plays (11 frames) with extended hitbox
- [ ] Enemy hit by sword takes 1 HP damage
- [ ] All 8 directional sub-sheets are visually distinct (open an image viewer to confirm before code test)

---

## PHASE 11 â€” Block / Parry System

**Goal:** Wire the existing block animations to a defensive mechanic with a parry window.

### 11.1 Add block state to `SimPlayer`

```java
public boolean isBlocking    = false;
public float   blockHeldTime = 0f;   // how long block has been held
public boolean isParrying    = false;
public float   parryWindow   = 0f;   // short invincible parry flash (0.1 s)
```

Block is held with a new key â€” assign to `cmd.block` (add to `InputCommand` and wire to `InputPoller` key `G`). See Phase 15 for the full keybinding rationale; `Q` is reserved for consumables.

### 11.2 Block logic in `GameSimulator`

```java
boolean blockHeld = cmd.block;
if (blockHeld) {
    sp.isBlocking     = true;
    sp.blockHeldTime += DT;
    // Parry window: first 0.1 s of block
    sp.isParrying = (sp.blockHeldTime < 0.10f);
    sp.parryWindow = sp.isParrying ? (0.10f - sp.blockHeldTime) : 0f;
} else {
    sp.isBlocking    = false;
    sp.blockHeldTime = 0f;
    sp.isParrying    = false;
}
```

When an enemy attack hits a blocking player:
```java
if (sp.isParrying) {
    // Perfect parry: no damage, attacker stunned 0.8 s
    animState = "parry";   // player_parry  (Block Hit Hard, 6 frames)
    emitParryVFX(p.x, p.y);
} else if (sp.isBlocking) {
    // Normal block: halved damage, Block Hit Normal (3 frames)
    animState = "block_hit";
    damage = Math.max(0, damage - 1);
}
```

### 11.3 Block animation states

Update `stepPlayerAnimationState()`:
```java
if (sp.isBlocking) {
    boolean inAir    = !p.onGround;
    boolean crouched = cmd.crouch && p.onGround;
    sp.animState = inAir ? "air_block" : (crouched ? "crouch_block" : "block");
    return;
}
```

Hit reactions during block are set by the damage handler, not the state machine.

### 11.4 Test â€” Block / Parry Checklist

- [ ] Hold `Q`: `player_block` (8-frame loop) plays
- [ ] Take hit while blocking: `player_block_hit` (3 frames) plays, damage halved
- [ ] Take hit within first 0.1 s of blocking: `player_parry` (6 frames) plays, no damage, parry VFX fires
- [ ] Block while airborne: `player_air_block` plays
- [ ] Block while crouched: `player_crouch_block` plays
- [ ] Sword block: `player_sword_block` plays (same logic, different sprites)
- [ ] Block does not cancel mid-combo (block input during combo is ignored until combo resets)

---

## PHASE 12 â€” Social / Emote Animations

**Goal:** Wire the hub-social animations (sitting, sleeping, talking, victory, drink) to NPC interaction events and hub logic.

### 12.1 Add emote state to `SimPlayer`

```java
public String emoteState = "";     // "sit", "sleep", "talk", "victory", "drink", "dance"
public float  emoteTimer = 0f;     // -1 = looping until cancelled
```

### 12.2 Trigger points

| Emote | Trigger | Duration |
|-------|---------|----------|
| `sit` | Player presses E near a bench/chair | Loop until E pressed again |
| `sleep` | Player stands idle in bed area | Loop â€” auto-triggers after 3 s idle in rest zone |
| `talk` | NPC dialogue is open | Loop during dialogue sequence |
| `victory` | Level complete event fires | 10 frames, play once |
| `drink` | Player uses consumable item | 19 frames, play once |
| `dance` | Player presses emote key (default: `V`) | Loop until cancelled |

### 12.3 Animation state priority

Emotes sit at low priority â€” they can be cancelled by any movement input:
```java
// Bottom of stepPlayerAnimationState(), after idle:
if (!sp.emoteState.isEmpty() && sp.emoteTimer != 0f) {
    sp.animState = sp.emoteState;
    if (sp.emoteTimer > 0f) {
        sp.emoteTimer -= DT;
        if (sp.emoteTimer <= 0f) sp.emoteState = "";
    }
}
```

Any movement input clears the emote:
```java
if (cmd.left || cmd.right || cmd.jump || cmd.dash || cmd.attack) {
    sp.emoteState = "";
    sp.emoteTimer = 0f;
}
```

### 12.4 Test â€” Social Animation Checklist

- [ ] Sit near bench (E): `player_sit` loops
- [ ] Press E again: returns to idle
- [ ] Open NPC dialogue: `player_talk` loops during conversation
- [ ] Collect level-complete item: `player_victory` plays once
- [ ] Use health potion: `player_drink` plays 19 frames, item consumed at frame 10
- [ ] Press `V`: `player_dance` loops
- [ ] Move during dance: dance cancelled, returns to run

---

## PHASE 13 â€” Death, Revive & Prone System

**Goal:** Replace the single `player_death` state with the full two-variant death system plus the prone subsystem for stealth/knockdown.

### 13.1 Death variant selection

Add `deathVariant` to `SimPlayer`:
```java
public int deathVariant = 0;  // 0 = variant A, 1 = variant B
```

On player death, pick randomly:
```java
sp.deathVariant = (random.nextInt(2));
sp.animState    = (sp.deathVariant == 0) ? "death" : "death2";
```

Revive animation plays on respawn:
```java
sp.animState = (sp.deathVariant == 0) ? "revive" : "revive2";
// Only transition back to idle after revive animation completes
sp.reviveTimer = 6f / 12f;  // 6 frames @ 12 fps = 0.5 s
```

### 13.2 Prone system

Prone is entered via a dedicated input (e.g., hold `S` + crouch) or by being knocked down by a heavy-hit enemy:

```java
public boolean isProne        = false;
public boolean isProneMoving  = false;
public float   proneTimer     = 0f;    // for forced knockdown duration
```

State machine entries:
```java
if (sp.isProne) {
    sp.animState = sp.isProneMoving ? "prone_walk" : "prone";
    return;
}
```

Prone-death and prone-revive are triggered by the same death handler when `sp.isProne == true`.

### 13.3 Test â€” Death & Revive Checklist

- [ ] Player dies: either `player_death` or `player_death2` plays (random)
- [ ] Respawn: matching `player_revive` or `player_revive2` plays before control is returned
- [ ] Death while prone: `player_prone_death` plays (5 frames)
- [ ] Revive from prone: `player_prone_revive` plays (5 frames)
- [ ] Hold S+Ctrl: player enters prone state, `player_prone` (9-frame loop) plays
- [ ] Move while prone: `player_prone_walk` (8-frame loop) plays
- [ ] Take hit while prone: `player_prone_hurt` (4 frames) plays
- [ ] Stand up from prone: transition to `idle` is instant (no stand-up anim â€” use `revive` as a workaround or accept snap)

---

## PHASE 14 â€” Testing & Validation

**Goal:** Confirm all systems are integrated, performant, and do not regress existing gameplay.

### 14.1 Full animation state coverage test

Create `AnimationIntegrationTest.java` in `client/src/test/`. This test:
1. Instantiates `AnimationRegistry`
2. Calls `loadUnarmedSheets()` and `loadSwordSheets()` with real asset paths
3. Asserts that every key in the Â§0.2 mapping table returns a non-null frame array
4. Asserts frame array length matches the expected frame count

```java
@Test
public void allUnarmedKeysRegistered() {
    AnimationRegistry reg = new AnimationRegistry();
    reg.loadUnarmedSheets(Gdx.files.internal("assets/sprites/player/unarmed"));
    String[] expected = {
        "player_idle", "player_walk", "player_run", "player_dash", /* ... all 79 ... */
    };
    for (String key : expected) {
        assertNotNull("Missing key: " + key, reg.getFrame(key, 0f, 8f));
    }
}

@Test
public void allSwordKeysRegistered() { /* same pattern */ }
```

### 14.2 State machine exhaustion test

Create `PlayerAnimStateMachineTest.java` in `core/src/test/`. This test:
1. Creates a `SimPlayer` and `PhysicsState` with mock inputs
2. Steps `GameSimulator.stepPlayerAnimationState()` through each major state
3. Asserts the correct `animState` string is set in each case

Cover:
- Idle, walk, run, dash, jump, fall, wall_slide, crouch, crouch_walk
- Climbing (all 6 variants)
- Swimming (all 6 variants)
- Each combo step (1, 2, 3) for unarmed and sword
- Directional sword attack (directions 0-7)
- Dash attack (sword only)
- Block (all stances)
- Each interaction state
- Each emote state
- Death variants (0 and 1)
- Prone and prone-walk

### 14.3 Transition integrity test

For each pair of states, confirm the stateTime resets to 0 when the state changes. This prevents non-looping animations from freezing on the wrong frame.

In `EntityRenderer.renderPlayer()`, stateTime is already tracked per-entity via `stateTimes`. Confirm:
- `stateTime` resets when `animKey` changes
- Non-looping animations clamp to last frame (not loop back to frame 0)

Add assertion in test:
```java
// Transition idle â†’ attack â†’ idle: stateTime should reset to 0 at each transition
```

### 14.4 Performance validation

Run the existing performance baseline suite:
```
python launcher/launcher.py --headless --record perf_run_post_anim.json
```

Compare against `docs/perf_baseline.csv`. Accept if:
- `frame_total` p95 â‰¤ 16 ms (60 fps budget)
- `render` section did not increase by more than 0.5 ms median
- No GC spikes (AnimationRegistry must not allocate per-frame)

### 14.5 Visual parity walkthrough

Launch via `python launcher/launcher.py`. Conduct manual walkthrough:

**Act I (Tutorial zone):**
- [ ] All unarmed locomotion states readable and smooth
- [ ] Combo chain fires in sequence with visible attack arcs
- [ ] Death + revive plays correctly
- [ ] Door enter/exit in hub plays full animation

**Sword pickup:**
- [ ] Equip sword: sprite set switches to sword variants
- [ ] All sword locomotion states match unarmed framing and scale
- [ ] Sword combo (ground, air, crouch) all play correctly
- [ ] Dash attack triggers from dash
- [ ] Unequip sword: switches back cleanly

**Traversal:**
- [ ] Climb wall animation plays during wall-press
- [ ] Ledge grab, idle, pull-up sequence works
- [ ] Swim surface idle + surface swim loop
- [ ] Underwater swim in all 4 directions

**Hub social:**
- [ ] Talking animation while NPC dialogue open
- [ ] Sitting near hub furniture
- [ ] Victory animation on mission complete

### 14.6 Regression check

Run the full existing test suite to confirm nothing broke:
```bash
cd java && ./gradlew test
```

All pre-existing tests must pass. Pay special attention to:
- `CollisionEdgeCaseTest` â€” physics must be unaffected
- `PhysicsSystemTest` â€” no velocity/hitbox regressions
- `GameSimulatorTest` â€” attack hitbox timings must not change for existing tests

---

## Appendix A â€” Workarounds for Missing Animations

| Missing | Required for | Workaround |
|---------|-------------|------------|
| Charged attack wind-up | Yang system (Â§3.2) | Freeze frame 0 of `player_sword_attack` + pulsing VFX shader; release fires combo from frame 1 |
| Phase Shift teleport body | Phase through walls (Â§6.2) | VFX dissolve only; body holds `idle` pose during cursor mode |
| Stand-to-prone transition | Stealth entry | Tween physics AABB height 0.15 s; animation snaps to `prone` on arrival |
| Prone-to-stand | Stealth exit | Play `prone_revive` reversed (5 frames played backward via negative stateTime delta) |
| Water entry dive | Swimming entry | Hard-cut to `swim_surface_idle` at water threshold + splash VFX; no body animation |
| Water exit | Swimming exit | `ledge_climb_back` if wall present; snap to `idle` + VFX drip otherwise |
| Grapple throw | Rope mechanic (Â§3.1) | VFX hook projectile; body plays first 3 frames of `air_punch1` as throw gesture |
| Wall-hang idle (looping) | Wall jump system | Freeze last frame of `wall_slide` + 1-pixel breathing offset in code |
| Backstep / evade | Parry window | `roll` played at 1.5Ã— speed toward `facing == -1` direction reads as a backstep |

---

---

## PHASE 15 â€” Complete Keybinding Scheme

**Goal:** Define the authoritative default control scheme covering all actions â€” existing, new (block, weapon select, emote, prone), and UI. This phase is documentation and design; code changes happen in Phase 16.

### 15.1 Existing state audit

Two problems exist before any new bindings are added:

| Problem | Detail |
|---------|--------|
| `settings.json` / `InputPoller` disconnect | `settings.json` has `key_left`, `key_right`, `key_jump`, `key_dash`, `key_crouch` but `InputPoller.java` never reads them â€” all bindings are hardcoded. The settings fields are dead. |
| `key_crouch` mismatch | `settings.json` says `"key_crouch": "down"` (arrow key); `InputPoller` uses `CTRL`. These disagree. |
| Missing new-action fields | `block`, `selectWeapon1`, `selectWeapon2`, `emote`, `prone` do not exist in `InputCommand` yet. |

Phase 16 resolves all three. This phase establishes what the correct values should be.

### 15.2 Default Keybinding Scheme â€” Keyboard

#### Movement group

| Action | `InputCommand` field | Primary key | Secondary key | Notes |
| ------ | ------------------- | ----------- | ------------- | ----- |
| Move left | `left` | `A` | `â†` | |
| Move right | `right` | `D` | `â†’` | |
| Move up (climb / swim / aim) | `up` | `W` | `â†‘` | |
| Move down (crouch / swim / aim) | `down` | `S` | `â†“` | |
| Jump | `jump` | `SPACE` | â€” | Double-jump, wall-jump reuse same field |
| Dash | `dash` | `LEFT SHIFT` | `RIGHT SHIFT` | Held; unlockable ability |
| Slow walk | `slowWalk` | `LEFT ALT` | â€” | Hold for precision movement |
| Crouch | `crouch` | `LEFT CTRL` | `RIGHT CTRL` | Hold; fixes the `settings.json` mismatch (was "down") |

#### Combat group

| Action | `InputCommand` field | Primary key | Secondary key | Notes |
| ------ | ------------------- | ----------- | ------------- | ----- |
| Attack (combo) | `attack` | `J` | `Left Mouse` | Directional with WASD held |
| Block (hold) | `block` *(new)* | `G` | â€” | First 0.1 s = parry window; see Phase 11 |
| Throw projectile | `throwShuriken` | `K` | â€” | Existing |
| Teleport (hold to aim) | `teleport` | `F` | `T` | Hold; release warps; existing |
| Ninjutsu (hold to cast) | `ninjutsu` | `L` | â€” | Hold; existing |

**Why `G` for block:** `G` sits one key right of the left-hand movement cluster â€” reachable by the left index finger without leaving WASD. `Q` is consumable. `K` is throw. No existing binding occupied `G`.

#### Weapon select group *(all new)*

| Action | `InputCommand` field | Primary key | Notes |
| ------ | ------------------- | ----------- | ----- |
| Equip unarmed | `selectWeapon1` *(new)* | `1` | Switches to unarmed animation set |
| Equip sword | `selectWeapon2` *(new)* | `2` | Switches to sword animation set |

Number row weapon switching is the universal game convention (`1`/`2`/`3`). Wire as `isKeyJustPressed`.

#### Traversal group *(new)*

| Action | `InputCommand` field | Primary key | Notes |
| ------ | ------------------- | ----------- | ----- |
| Enter / exit prone | `prone` *(new)* | `Z` | `Z` is menu-confirm but only in menu contexts; safe during gameplay |

`Z` is currently bound to `menuConfirm` via `isKeyJustPressed`. That only fires on the menu screen. During gameplay `Z` is idle â€” safe to reuse for prone without context conflict.

#### Interaction group

| Action | `InputCommand` field | Primary key | Secondary key | Notes |
| ------ | ------------------- | ----------- | ------------- | ----- |
| Interact / use | `interact` | `E` | â€” | Existing; triggers door, lever, chest, NPC |
| Consumable | `consumable` | `Q` | â€” | Existing; keep as-is |
| Inventory | `inventory` | `I` | `TAB` | Existing |

#### Social / emote group *(new)*

| Action | `InputCommand` field | Primary key | Notes |
| ------ | ------------------- | ----------- | ----- |
| Emote (dance / toggle) | `emote` *(new)* | `V` | `V` is unused; press to start, press again or move to cancel |

#### UI and debug group

| Action | `InputCommand` field | Primary key | Secondary key | Notes |
| ------ | ------------------- | ----------- | ------------- | ----- |
| Minimap toggle | `minimap` | `M` | â€” | Existing |
| Full map | `fullmap` | `N` | â€” | Existing |
| Controls overlay | `controlsOverlay` | `F1` | â€” | Existing field; overlay rendering added Phase 17 |
| Debug overlay | `debugOverlay` | `F3` | â€” | Existing |
| Camera cycle | `cycleCamera` | `C` | â€” | Existing |
| Procedural toggle | `toggleProc` | `P` | â€” | Existing; dev tool |
| Pause / menu back | `menuBack` | `ESC` | `X` | Existing |
| Menu confirm | `menuConfirm` | `ENTER` | `Z` | Existing; `Z` is menu-context only |

### 15.3 Complete `settings.json` keybinding schema

The settings file gains a full `keybindings` block. This replaces the loose top-level `key_*` fields (which are removed in Phase 16):

```json
{
  "volume_master": 1.0,
  "volume_music": 0.7,
  "volume_sfx": 0.0,
  "fullscreen": false,
  "vsync": true,
  "window_width": 1920,
  "window_height": 1080,
  "screenshake": true,
  "particles": true,
  "camera_smoothing": 0.1,
  "show_fps": true,
  "show_hitboxes": false,
  "log_level": "INFO",
  "keybindings": {
    "left":           ["A",     "LEFT"],
    "right":          ["D",     "RIGHT"],
    "up":             ["W",     "UP"],
    "down":           ["S",     "DOWN"],
    "jump":           ["SPACE"],
    "dash":           ["SHIFT_LEFT", "SHIFT_RIGHT"],
    "crouch":         ["CONTROL_LEFT", "CONTROL_RIGHT"],
    "slow_walk":      ["ALT_LEFT"],
    "attack":         ["J",     "BUTTON_LEFT"],
    "block":          ["G"],
    "throw":          ["K"],
    "teleport":       ["F",     "T"],
    "ninjutsu":       ["L"],
    "select_weapon_1":["1"],
    "select_weapon_2":["2"],
    "prone":          ["Z"],
    "interact":       ["E"],
    "consumable":     ["Q"],
    "inventory":      ["I",     "TAB"],
    "emote":          ["V"],
    "minimap":        ["M"],
    "fullmap":        ["N"],
    "controls_overlay":["F1"],
    "debug_overlay":  ["F3"],
    "cycle_camera":   ["C"],
    "toggle_proc":    ["P"],
    "menu_confirm":   ["ENTER", "Z"],
    "menu_back":      ["ESCAPE","X"]
  }
}
```

Key string values match libGDX `Input.Keys` constant names exactly â€” `KeyBindings.java` (Phase 16) resolves them via `Input.Keys.valueOf(name)`.

### 15.4 Gamepad stub (future â€” not in this phase)

No gamepad implementation in this phase. Reserve the following layout for when controller support is added:

| Action | Controller button (Xbox layout) |
| ------ | ------------------------------ |
| Move | Left stick |
| Jump | A |
| Dash | B / Right shoulder |
| Attack | X |
| Block | Left trigger (hold) |
| Throw | Y |
| Teleport | Right trigger (hold) |
| Interact | A (context) |
| Inventory | Select / Back |
| Weapon 1/2 | D-pad left/right |
| Emote | D-pad up |

Add a `"gamepad_bindings": {}` block to `settings.json` as a reserved empty object now, so the schema is forward-compatible.

### 15.5 Test â€” Scheme completeness checklist

No code yet â€” verify the scheme design only:

- [ ] Every `InputCommand` field (existing + new) has an entry in the scheme table
- [ ] No two in-gameplay actions share the same key in the same context
- [ ] `Z` / `menuConfirm` context separation documented and understood
- [ ] `settings.json` schema validated as legal JSON (run through `python -m json.tool`)
- [ ] All key string values in `keybindings` block are valid libGDX `Input.Keys` names

---

## PHASE 16 â€” KeyBindings System

**Goal:** Replace `InputPoller`'s hardcoded bindings with a loaded, configurable `KeyBindings` class. Wire all new `InputCommand` fields. Fix the `settings.json` disconnect.

### 16.1 Add new fields to `InputCommand`

**File:** `java/core/src/main/java/com/indieniinja/network/InputCommand.java`

Add after `ninjutsu`:
```java
public boolean block;          // hold to block / parry
public boolean selectWeapon1;  // equip unarmed
public boolean selectWeapon2;  // equip sword
public boolean prone;          // enter / exit prone
public boolean emote;          // toggle emote
```

Update `toMap()` â€” append in the correct protocol order:
```java
m.put("block",          block);
m.put("select_weapon_1",selectWeapon1);
m.put("select_weapon_2",selectWeapon2);
m.put("prone",          prone);
m.put("emote",          emote);
```

Update `fromMap()` â€” add corresponding reads:
```java
c.block          = bool(m, "block");
c.selectWeapon1  = bool(m, "select_weapon_1");
c.selectWeapon2  = bool(m, "select_weapon_2");
c.prone          = bool(m, "prone");
c.emote          = bool(m, "emote");
```

> **Protocol note:** `toMap()` / `fromMap()` must stay in sync with any Python client still running on the same server. Add the new fields at the end of both maps so older clients send `false` for missing fields without breaking deserialization.

### 16.2 Create `KeyBindings.java`

**File:** `java/client/src/main/java/com/indieniinja/client/KeyBindings.java`

```java
package com.indieniinja.client;

import com.badlogic.gdx.Input;
import com.badlogic.gdx.files.FileHandle;
import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;

import java.util.*;

/**
 * Loads player keybindings from settings.json and resolves them to
 * libGDX Input.Keys integer codes.
 *
 * Each action maps to a list of key codes (primary + optional secondary).
 * InputPoller queries this class instead of hardcoding keys directly.
 */
public final class KeyBindings {
    

    /** Action name â†’ list of resolved libGDX key codes. */
    private final Map<String, int[]> bindings = new HashMap<>();

    /** Defaults matching the scheme in Phase 15. Applied when no file is present. */
    private static final Map<String, String[]> DEFAULTS = new LinkedHashMap<>();
    static {
        DEFAULTS.put("left",            new String[]{"A",            "LEFT"});
        DEFAULTS.put("right",           new String[]{"D",            "RIGHT"});
        DEFAULTS.put("up",              new String[]{"W",            "UP"});
        DEFAULTS.put("down",            new String[]{"S",            "DOWN"});
        DEFAULTS.put("jump",            new String[]{"SPACE"});
        DEFAULTS.put("dash",            new String[]{"SHIFT_LEFT",   "SHIFT_RIGHT"});
        DEFAULTS.put("crouch",          new String[]{"CONTROL_LEFT", "CONTROL_RIGHT"});
        DEFAULTS.put("slow_walk",       new String[]{"ALT_LEFT"});
        DEFAULTS.put("attack",          new String[]{"J"});           // mouse handled separately
        DEFAULTS.put("block",           new String[]{"G"});
        DEFAULTS.put("throw",           new String[]{"K"});
        DEFAULTS.put("teleport",        new String[]{"F",            "T"});
        DEFAULTS.put("ninjutsu",        new String[]{"L"});
        DEFAULTS.put("select_weapon_1", new String[]{"1"});
        DEFAULTS.put("select_weapon_2", new String[]{"2"});
        DEFAULTS.put("prone",           new String[]{"Z"});
        DEFAULTS.put("interact",        new String[]{"E"});
        DEFAULTS.put("consumable",      new String[]{"Q"});
        DEFAULTS.put("inventory",       new String[]{"I",            "TAB"});
        DEFAULTS.put("emote",           new String[]{"V"});
        DEFAULTS.put("minimap",         new String[]{"M"});
        DEFAULTS.put("fullmap",         new String[]{"N"});
        DEFAULTS.put("controls_overlay",new String[]{"F1"});
        DEFAULTS.put("debug_overlay",   new String[]{"F3"});
        DEFAULTS.put("cycle_camera",    new String[]{"C"});
        DEFAULTS.put("toggle_proc",     new String[]{"P"});
        DEFAULTS.put("menu_confirm",    new String[]{"ENTER",        "Z"});
        DEFAULTS.put("menu_back",       new String[]{"ESCAPE",       "X"});
    }

    public KeyBindings() {
        applyDefaults();
    }

    /**
     * Load keybindings from the "keybindings" object inside settings.json.
     * Any action missing from the file keeps its default value.
     * Unknown key name strings are logged and ignored (no crash).
     */
    @SuppressWarnings("unchecked")
    public void loadFromSettings(FileHandle settingsFile) {
        if (!settingsFile.exists()) return;
        try {
            Map<String, Object> root = new Gson().fromJson(
                settingsFile.readString("UTF-8"),
                new TypeToken<Map<String, Object>>(){}.getType()
            );
            Object kb = root.get("keybindings");
            if (!(kb instanceof Map)) return;
            Map<String, Object> kbMap = (Map<String, Object>) kb;
            for (Map.Entry<String, Object> e : kbMap.entrySet()) {
                String action = e.getKey();
                if (!(e.getValue() instanceof List)) continue;
                List<String> names = (List<String>) e.getValue();
                resolveAndStore(action, names.toArray(new String[0]));
            }
        } catch (Exception ex) {
            System.err.println("[KeyBindings] Failed to load: " + ex.getMessage()
                + " â€” using defaults");
        }
    }

    /** Returns true if any bound key for action is currently held. */
    public boolean isHeld(String action) {
        int[] codes = bindings.get(action);
        if (codes == null) return false;
        for (int code : codes)
            if (com.badlogic.gdx.Gdx.input.isKeyPressed(code)) return true;
        return false;
    }

    /** Returns true if any bound key for action was just pressed this frame. */
    public boolean isJustPressed(String action) {
        int[] codes = bindings.get(action);
        if (codes == null) return false;
        for (int code : codes)
            if (com.badlogic.gdx.Gdx.input.isKeyJustPressed(code)) return true;
        return false;
    }

    private void applyDefaults() {
        for (Map.Entry<String, String[]> e : DEFAULTS.entrySet())
            resolveAndStore(e.getKey(), e.getValue());
    }

    private void resolveAndStore(String action, String[] names) {
        List<Integer> codes = new ArrayList<>();
        for (String name : names) {
            int code = Input.Keys.valueOf(name);  // returns -1 if unknown
            if (code != -1) {
                codes.add(code);
            } else {
                System.err.println("[KeyBindings] Unknown key name '" + name
                    + "' for action '" + action + "' â€” skipped");
            }
        }
        if (!codes.isEmpty())
            bindings.put(action, codes.stream().mapToInt(Integer::intValue).toArray());
    }
}
```

### 16.3 Rewrite `InputPoller` to use `KeyBindings`

**File:** `java/client/src/main/java/com/indieniinja/client/InputPoller.java`

Replace the hardcoded `isKeyPressed` calls with `KeyBindings` queries:

```java
public final class InputPoller {

    private final KeyBindings keys;
    private long frameCounter = 0;

    public InputPoller(KeyBindings keys) {
        this.keys = keys;
    }

    public InputCommand poll() {
        InputCommand cmd = new InputCommand((int)(frameCounter++ & 0x7FFF_FFFFL));

        // Movement (held)
        cmd.left   = keys.isHeld("left");
        cmd.right  = keys.isHeld("right");
        cmd.up     = keys.isHeld("up");
        cmd.down   = keys.isHeld("down");
        cmd.jump   = keys.isHeld("jump");
        cmd.dash   = keys.isHeld("dash");
        cmd.crouch = keys.isHeld("crouch");
        cmd.slowWalk = keys.isHeld("slow_walk");

        // Combat (held â€” server uses edge-detection)
        cmd.attack        = keys.isHeld("attack")
                         || Gdx.input.isButtonPressed(Input.Buttons.LEFT);
        cmd.block         = keys.isHeld("block");
        cmd.throwShuriken = keys.isHeld("throw");
        cmd.teleport      = keys.isHeld("teleport");
        cmd.ninjutsu      = keys.isHeld("ninjutsu");

        // Weapon select (just-pressed)
        cmd.selectWeapon1 = keys.isJustPressed("select_weapon_1");
        cmd.selectWeapon2 = keys.isJustPressed("select_weapon_2");

        // Traversal / social (just-pressed)
        cmd.prone  = keys.isJustPressed("prone");
        cmd.emote  = keys.isJustPressed("emote");

        // Interaction (just-pressed)
        cmd.interact   = keys.isJustPressed("interact");
        cmd.consumable = keys.isJustPressed("consumable");
        cmd.inventory  = keys.isJustPressed("inventory");

        // UI (just-pressed)
        cmd.minimap         = keys.isJustPressed("minimap");
        cmd.fullmap         = keys.isJustPressed("fullmap");
        cmd.controlsOverlay = keys.isJustPressed("controls_overlay");
        cmd.debugOverlay    = keys.isJustPressed("debug_overlay");
        cmd.cycleCamera     = keys.isJustPressed("cycle_camera");
        cmd.toggleProc      = keys.isJustPressed("toggle_proc");

        // Menu (just-pressed)
        cmd.menuConfirm = keys.isJustPressed("menu_confirm");
        cmd.menuBack    = keys.isJustPressed("menu_back");

        return cmd;
    }
}
```

### 16.4 Wire `KeyBindings` in `GameScreen`

**File:** `java/client/src/main/java/com/indieniinja/client/GameScreen.java`

```java
// In GameScreen.create():
KeyBindings keyBindings = new KeyBindings();
FileHandle settingsFile = Gdx.files.local("user_data/settings/settings.json");
keyBindings.loadFromSettings(settingsFile);
inputPoller = new InputPoller(keyBindings);
```

`KeyBindings` is constructed once at startup. If the file is absent or malformed, defaults apply silently.

### 16.5 Update `settings.json`

**File:** `user_data/settings/settings.json`

- Remove the old top-level `key_left`, `key_right`, `key_jump`, `key_dash`, `key_crouch` fields
- Add the full `keybindings` block from Â§15.3
- Add `"gamepad_bindings": {}` as a reserved stub

### 16.6 Test â€” KeyBindings System Checklist

- [ ] Launch via `python launcher/launcher.py` â€” game starts, no crash, bindings load from file
- [ ] Delete `keybindings` block from `settings.json`, restart â€” defaults apply, game still playable
- [ ] Manually edit `settings.json` to swap attack to `"U"` â€” in-game attack now fires on `U`
- [ ] Enter an invalid key name (e.g. `"ZZZZ"`) in settings â€” logged warning, action falls back to default, no crash
- [ ] Confirm `key_left` / `key_right` (old fields) are gone from `settings.json` without breaking anything
- [ ] All five new `InputCommand` fields (`block`, `selectWeapon1`, `selectWeapon2`, `prone`, `emote`) transmit over the wire: add a temporary server-side log confirming receipt
- [ ] Hold `G` â†’ `cmd.block` is `true` in server log
- [ ] Press `1` â†’ `cmd.selectWeapon1` is `true` for exactly one tick
- [ ] Press `2` â†’ `cmd.selectWeapon2` is `true` for exactly one tick
- [ ] Press `V` â†’ `cmd.emote` is `true` for exactly one tick
- [ ] Press `Z` â†’ `cmd.prone` is `true` for exactly one tick (and `Z` does not fire `menuConfirm` during gameplay)

---

## PHASE 17 â€” Controls Overlay (In-Game HUD)

**Goal:** Render a readable in-game controls reference overlay, triggered by `F1`. It reads live from `KeyBindings` so it always reflects the player's current configuration.

### 17.1 Design

The overlay is a semi-transparent dark panel rendered over the game world, listing all gameplay bindings in two columns. It does not pause the game â€” the player can read controls while still moving.

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚            CONTROLS  (F1 to close)                   â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚  MOVEMENT            â”‚  COMBAT                       â”‚
â”‚  Move        A / D   â”‚  Attack        J              â”‚
â”‚  Jump        SPACE   â”‚  Block (hold)  G              â”‚
â”‚  Dash        SHIFT   â”‚  Throw         K              â”‚
â”‚  Crouch      CTRL    â”‚  Teleport      F / T          â”‚
â”‚  Slow Walk   ALT     â”‚  Ninjutsu      L              â”‚
â”‚                      â”‚                               â”‚
â”‚  TRAVERSAL           â”‚  WEAPON SELECT                â”‚
â”‚  Prone       Z       â”‚  Unarmed       1              â”‚
â”‚                      â”‚  Sword         2              â”‚
â”‚  INTERACTION         â”‚                               â”‚
â”‚  Use / Talk  E       â”‚  SOCIAL                       â”‚
â”‚  Item        Q       â”‚  Emote         V              â”‚
â”‚  Inventory   I / TAB â”‚                               â”‚
â”‚                      â”‚  UI                           â”‚
â”‚                      â”‚  Map           M              â”‚
â”‚                      â”‚  Full Map      N              â”‚
â”‚                      â”‚  Controls      F1             â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

### 17.2 State management

Add to `GameScreen`:
```java
private boolean showControlsOverlay = false;
```

In the render loop, toggle on `cmd.controlsOverlay`:
```java
if (cmd.controlsOverlay) showControlsOverlay = !showControlsOverlay;
```

Pass `showControlsOverlay` to `HudRenderer.render()` as a new parameter.

### 17.3 Rendering in `HudRenderer`

**File:** `java/client/src/main/java/com/indieniinja/client/rendering/HudRenderer.java`

Add `renderControlsOverlay(SpriteBatch batch, KeyBindings keys)` method. The renderer already has `BitmapFont font` and `SpriteBatch hudBatch` â€” no new rendering infrastructure needed.

```java
public void renderControlsOverlay(KeyBindings keys) {
    if (!visible) return;

    float sw = Gdx.graphics.getWidth();
    float sh = Gdx.graphics.getHeight();
    float panelW = sw * 0.55f;
    float panelH = sh * 0.65f;
    float panelX = (sw - panelW) * 0.5f;
    float panelY = (sh - panelH) * 0.5f;

    // Dark semi-transparent background
    shapeRenderer.begin(ShapeRenderer.ShapeType.Filled);
    shapeRenderer.setColor(0f, 0f, 0f, 0.78f);
    shapeRenderer.rect(panelX, panelY, panelW, panelH);
    shapeRenderer.end();

    // Title
    hudBatch.begin();
    font.setColor(1f, 0.85f, 0.2f, 1f);  // gold
    font.draw(hudBatch, "CONTROLS  (F1 to close)",
              panelX + 16f, panelY + panelH - 12f);
    font.setColor(Color.WHITE);

    // Two-column layout
    float colLeft  = panelX + 20f;
    float colRight = panelX + panelW * 0.5f + 10f;
    float rowStart = panelY + panelH - 40f;
    float rowStep  = 18f;

    drawSection(hudBatch, "MOVEMENT",  colLeft,  rowStart,          rowStep, keys, MOVEMENT_ENTRIES);
    drawSection(hudBatch, "TRAVERSAL", colLeft,  rowStart - 130f,   rowStep, keys, TRAVERSAL_ENTRIES);
    drawSection(hudBatch, "INTERACTION",colLeft, rowStart - 200f,   rowStep, keys, INTERACT_ENTRIES);
    drawSection(hudBatch, "COMBAT",    colRight, rowStart,          rowStep, keys, COMBAT_ENTRIES);
    drawSection(hudBatch, "WEAPON",    colRight, rowStart - 160f,   rowStep, keys, WEAPON_ENTRIES);
    drawSection(hudBatch, "SOCIAL",    colRight, rowStart - 230f,   rowStep, keys, SOCIAL_ENTRIES);
    drawSection(hudBatch, "UI",        colRight, rowStart - 290f,   rowStep, keys, UI_ENTRIES);

    font.setColor(Color.WHITE);
    hudBatch.end();
}
```

Entry lists (static constants in `HudRenderer`):
```java
// Each String[] is { displayLabel, keybinding_action_name }
private static final String[][] MOVEMENT_ENTRIES = {
    {"Move left/right", "left"},
    {"Jump",            "jump"},
    {"Dash",            "dash"},
    {"Crouch",          "crouch"},
    {"Slow walk",       "slow_walk"},
};
private static final String[][] TRAVERSAL_ENTRIES = {
    {"Prone",           "prone"},
};
private static final String[][] INTERACT_ENTRIES = {
    {"Use / Talk",      "interact"},
    {"Item / Consume",  "consumable"},
    {"Inventory",       "inventory"},
};
private static final String[][] COMBAT_ENTRIES = {
    {"Attack",          "attack"},
    {"Block (hold)",    "block"},
    {"Throw",           "throw"},
    {"Teleport (hold)", "teleport"},
    {"Ninjutsu (hold)", "ninjutsu"},
};
private static final String[][] WEAPON_ENTRIES = {
    {"Unarmed",         "select_weapon_1"},
    {"Sword",           "select_weapon_2"},
};
private static final String[][] SOCIAL_ENTRIES = {
    {"Emote",           "emote"},
};
private static final String[][] UI_ENTRIES = {
    {"Minimap",         "minimap"},
    {"Full map",        "fullmap"},
    {"Controls",        "controls_overlay"},
};
```

`drawSection()` renders a header label and then each entry as `label .............. KEY1 / KEY2`, where the key names are resolved by querying `KeyBindings` and converting int codes back to readable names via `Input.Keys.toString(code)`.

### 17.4 Key name formatting helper

```java
/** Convert KeyBindings action to a human-readable key string, e.g. "SHIFT_LEFT" â†’ "SHIFT" */
private String formatKeys(KeyBindings keys, String action) {
    // KeyBindings exposes a getNames(action) method (add this to KeyBindings):
    //   returns String[] of libGDX key names for the action
    String[] names = keys.getNames(action);
    if (names == null || names.length == 0) return "â€”";
    // Prettify common names
    return Arrays.stream(names)
        .map(HudRenderer::prettifyKeyName)
        .collect(Collectors.joining(" / "));
}

private static String prettifyKeyName(String raw) {
    return switch (raw) {
        case "SPACE"        -> "SPACE";
        case "SHIFT_LEFT",
             "SHIFT_RIGHT"  -> "SHIFT";
        case "CONTROL_LEFT",
             "CONTROL_RIGHT"-> "CTRL";
        case "ALT_LEFT"     -> "ALT";
        case "ESCAPE"       -> "ESC";
        case "BUTTON_LEFT"  -> "L.MOUSE";
        default             -> raw;
    };
}
```

Add `getNames(String action)` to `KeyBindings`:
```java
public String[] getNames(String action) {
    int[] codes = bindings.get(action);
    if (codes == null) return new String[0];
    String[] names = new String[codes.length];
    for (int i = 0; i < codes.length; i++)
        names[i] = Input.Keys.toString(codes[i]);
    return names;
}
```

### 17.5 Test â€” Controls Overlay Checklist

- [ ] Press `F1` in-game: overlay appears, game continues running behind it
- [ ] Press `F1` again: overlay dismisses
- [ ] Every action in the Phase 15 scheme appears in the overlay with correct key labels
- [ ] Manually rebind attack to `"U"` in `settings.json`, restart â€” overlay shows `U`, not `J`
- [ ] Overlay is readable at 1920Ã—1080 and at 1280Ã—720 (test both resolutions)
- [ ] Overlay does not block input â€” player can still move and jump while it is open
- [ ] `ESC` while overlay is open: overlay closes first (handle `menuBack` with overlay-close priority before pause)
- [ ] Launch via `python launcher/launcher.py` and confirm F1 functions from the launcher path

---

## Appendix B â€” Pistol Staging (Arcade Mode)

The pistol set (from ZIP 002) is extracted to `assets/sprites/player/pistol/` in Phase 1 but not registered. When Arcade Mode integration begins:

1. Add `loadPistolSheets(FileHandle pistolDir)` to `AnimationRegistry` â€” same pattern as sword
2. Add `WeaponState.PISTOL` to the enum
3. The pistol set contains 5 directional shooting sub-sheets (standing, run, jump, crouch, prone). Map these to:
   - `player_pistol_shoot_d0` through `player_pistol_shoot_d4`
4. The pistol has no melee combo â€” `punch1` still fires as a kick/butt-strike

---

## Appendix C â€” Decision Log

| Date | Decision | Reason |
|------|----------|--------|
| 2026-04-11 | No pixel conversion needed | ZIP sheets already 80Ã—80 px â€” confirmed by dimension check |
| 2026-04-11 | Weapon prefix injected at EntityRenderer, not state machine | State machine stays weapon-agnostic; cleaner separation |
| 2026-04-11 | `jumpfall_spritesheet.png` split at frame 5 | Same approach as existing `registerJumpFall()` method |
| 2026-04-11 | 8 attack combo sub-sheets registered as separate directional keys | Enables directional attack system without a new combo architecture |
| 2026-04-11 | Pistol staged but not wired | Not in Campaign GDD; reserve for Arcade Mode milestone |
| 2026-04-11 | Block triggered by `G` key (new `InputCommand.block` field) | `Q` is consumable; `K` is throw; `G` sits between movement and combat clusters with no prior binding |
| 2026-04-11 | Death variant chosen randomly at death event | Avoids death always looking identical; both variants have matching revive |
