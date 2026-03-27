# Render Gap Investigation & Test Suite Fix
Branch: `perf/render-gap-phase6`
Parent: `feature/animation-pipeline`
Target: ≥60 FPS on perf_run2.json (currently avg=44.6), all tests green

---

## Context

`perf_run2.json` replay profiling (11,419 frames):

| Section | avg | p95 |
| --- | --- | --- |
| frame_total | 24.74ms | 36.51ms |
| render | 22.33ms | 35.57ms |
| render_tiles | 3.30ms | 3.68ms |
| render_enemies | 0.06ms | 0.07ms |
| render_hud | 1.29ms | 3.27ms |
| **untracked gap** | **17.68ms** | — |

Untracked gap = render(22.33) − tiles(3.30) − enemies(0.06) − hud(1.29) = **17.68ms**

Candidates in render loop between line 2866 and 3140:
- NPCs (`draw_npc_char`)
- Player sprite (`pygame.transform.scale` every frame — **prime suspect**)
- Companion orbs (update + render)
- Shuriken projectiles (`rotozoom` per projectile per frame)
- Exit marker + objective compass (math + sorting per frame)

---

## PHASE A — ADD SUB-SECTION PROFILING ✅

**Goal:** Quantify each untracked segment precisely.

**Sections to add:**

| Key | Lines covered |
| --- | --- |
| `render_npcs` | 2868–2876 |
| `render_player` | 2878–2948 |
| `render_companions` | 2950–2967 |
| `render_projectiles` | 2969–2993 |

**Output:** New profiler run on perf_run2.json

---

## PHASE B — BOTTLENECK FIXES

_(Populated after Phase A run)_

---

## PHASE C — TEST SUITE FIXES

**Stale assertions (update expected values):**

| Test | File | Issue |
| --- | --- | --- |
| `test_mission_count` | test_mission_registry.py | Expects 25, got 30 |
| `test_missions_by_region` | test_mission_registry.py | Region counts stale |
| `test_region_distribution` | test_mission_registry.py | Region counts stale |
| `test_region_list` | test_mission_registry.py | Region list stale |
| `test_statistics` | test_phase7_campaign.py | Expects 2 unlocked regions, got 3 |
| `test_save_version_migration` | test_phase7_campaign.py | Expects migration to 0.6.0, got 0.7.0 |
| `test_enemy_ai_without_seed_still_works` | test_ai_determinism.py | Expects cooldown=1.0, got 0.8 |
| `test_input_command_snapshot` | test_input_command_snapshot.py | New fields added to InputCommand |

**Logic failures (investigate + fix):**

| Test | File | Symptom |
| --- | --- | --- |
| `test_attack_deals_damage` | test_enemy_ai_comprehensive.py | attack returns None |
| `test_attack_cooldown` | test_enemy_ai_comprehensive.py | attack returns None |
| `test_chase_target_update_interval` | test_enemy_ai_comprehensive.py | target not cached |
| `test_enemy_detects_obstacle_ahead` | test_enemy_obstacle_avoidance.py | obstacle_ahead=False |
| `test_raycast` | test_collision_system.py | raycast misses wall |
| `test_data_integrity::test_mission_reward_items_exist` | test_data_integrity.py | lantern_emblem item missing |
| `test_threshold_balance` (ERROR) | edge_cases/test_threshold_balance.py | exception thrown |

---

## PHASE D — VALIDATION

- Run full test suite: all green (or document any accepted skip)
- Re-run perf_run2.json replay: avg FPS ≥ 60
- Commit + push

---

## Decision Log

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-03-27 | Branch from feature/animation-pipeline | Includes all perf O1-O9 and animation pipeline changes |
