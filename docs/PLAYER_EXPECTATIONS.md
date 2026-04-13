# Shadow Ascent - Launcher-Only Player Expectations and UX Test Guide
## Living Playtest Document for User-Experience, Design-Intent, and Balance Validation

**Current target build:** `v0.11.29`  
**Last updated:** `2026-04-13 22:47:26 +01:00`  
**Tester profile:** User with `launcher.exe` only (no IDE, no terminal, no debug tooling required)

---

## 1) Purpose
Use this document to evaluate whether the shipped player experience matches the intended design in `GDD.md` and active plans.

This guide is intentionally written from a player-only perspective:
- Start from `launcher.exe`
- Play normally
- Record what you felt, what confused you, and where difficulty felt unfair or flat

---

## 2) How to Run a Launcher-Only Test

1. Launch `launcher.exe`.
2. Enter game via **SOLO** (recommended for repeatable UX tests) or **CAMPAIGN** if you are validating online flow.
3. Run the session blocks in Section 6.
4. Capture feedback using the templates in Section 9.
5. Include screenshots or short clips for high-impact issues.

Optional artifact to attach if available: `user_data/logs/client.log`.

---

## 3) Intended Experience (from GDD) and What to Verify

| Design goal | Player should feel | Validate with feedback area IDs |
|---|---|---|
| Movement mastery is the core fantasy | Precise control, readable failure, fast retry confidence | `UX-MOVE`, `UX-COMBAT` |
| Combat is light but meaningful | Combat supports traversal/story pacing, not pure attrition | `UX-COMBAT`, `BAL-ENEMY` |
| Yin/Yang and Lantern represent internal state | World readability and power expression shift with emotional state | `UX-SYSTEMS`, `BAL-SYSTEMS` |
| Hub evolution carries narrative weight | Return-to-hub moments feel like progression/loss/recovery | `UX-NARRATIVE`, `UX-PROGRESSION` |
| Challenge should be teachable, not random | Losses feel earned and understandable | `BAL-DIFFICULTY`, `UX-READABILITY` |

---

## 4) Current Player-Visible Scope (v0.11.29)

| Feature | Status | What tester should expect |
|---|---|---|
| Launcher to mode-select flow | Working | Can enter game from launcher without terminal steps |
| Solo mode | Working | Full playable loop without dedicated server setup |
| Yin/Yang + Lantern HUD systems | Working | Values affect feel/readability; HUD updates during play |
| Vignette/darkness presentation | Working | World remains visible through vignette (no opaque mask) |
| Hub state evolution | Working | NPC roster and hub feel change with progression |
| Enemy AI states (patrol/chase/attack/flee/guard/stunned/dead) | Working | Distinct behavior per archetype |
| Boss psychological patterns (Siren, Echo Warden, Time Leech Lord, Memory Eater) | Working | Distinct fight identity and narrative behavior |
| Enemy tuning pass (slime/skeleton/archer) | Working in `v0.11.29` | Slime lunge alignment pass, skeleton directional guard + retreat, archer kiting + projectile pressure |
| Enemy/platform reliability pass | Working in `v0.11.29` | One-way platform stacking fix; enemies should no longer desync around tightly stacked platform+terrain tiles |
| Siren first-boss 3-phase rewrite baseline | Working in `v0.11.29` | Phase 1 ranged lane control; phase 2 teleport reposition; phase 3 volley pressure; red-slime add waves |
| Scripted-loss splash flow | Working in `v0.11.29` | On Siren defeat path, placeholder narrative splash appears with CONTINUE action |
| Save/load core persistence | Working | Progress/state should persist between sessions |
| Echo system foundations (`EchoRecorder`, `SimEcho`) | In progress | Foundation exists, full puzzle-driven player experience not yet fully exposed |
| Act IV depression mechanics + full late-act pacing | Not complete | Do not treat as regression if absent |
| Proof token/labyrinth loop | Not complete | Planned scope, not final player-facing behavior yet |

---

## 5) Do Not Misclassify These as Regressions Yet

Report as "not-yet-implemented" unless behavior contradicts release notes:
- Full Echo puzzle loop content
- Complete Act IV/Act V/Act VII emotional-arc tuning
- Final proof-token labyrinth gating
- Final arcade/sandbox feature-complete loops

---

## 6) Launcher-Only Test Sessions (Execution Order)

## Session A - First 15 Minutes (Onboarding and Friction)
- [ ] Launcher opens and user can enter a game mode without confusion
- [ ] Controls are discoverable enough to move/jump/attack without external docs
- [ ] HUD elements are understandable at a glance
- [ ] First enemy encounter communicates threat and response options

Record:
- `time_to_first_control_confidence`
- `first_point_of_confusion`
- `did_user_feel_stuck_without_docs (yes/no)`

## Session B - Core Movement and Combat Feel (20-30 min)
- [ ] Movement feels responsive enough for precision platforming
- [ ] Crouch, jump, dash, wall interactions behave consistently
- [ ] Taking damage feels fair and readable
- [ ] Combat cadence does not overshadow traversal identity

Record:
- `movement_responsiveness_score (1-5)`
- `combat_readability_score (1-5)`
- `deaths_total`
- `deaths_that_felt_unfair`

## Session C - Systems Clarity (Yin/Yang/Lantern) (20 min)
- [ ] Yin/Yang changes are visible and understandable
- [ ] Lantern state changes world readability in a legible way
- [ ] Flow-state moments are noticeable and satisfying

Record:
- `systems_clarity_score (1-5)`
- `could_player_explain_yin_yang_effects (yes/no)`
- `could_player_explain_lantern_effects (yes/no)`

## Session D - Enemy Balance Focus (v0.11.29) (20-30 min)

### Slime
- [ ] Attack now reaches about one slime body length in front
- [ ] Telegraph is readable enough to react
- [ ] Hits feel consistent with visible body/contact zone
- [ ] Slimes do not float or ignore gravity in normal terrain traversal
- [ ] Slimes do not clip through stacked platform+terrain geometry

### Skeleton shield bearer
- [ ] Effective threat range feels increased versus prior baseline
- [ ] Added range creates pressure without feeling "invisible"
- [ ] Guard behavior remains readable and counterplay still exists
- [ ] Front-facing guard blocks/reduces damage; rear-side attacks still reward flanks
- [ ] Enemy briefly retreats into guard after attack attempt (not constant face-tank)

### Archer
- [ ] Archer emits projectile attacks (not only melee presence)
- [ ] Projectile readability is sufficient for dodge/positioning
- [ ] Projectile damage pressure feels fair for encounter context
- [ ] Archer repositions to restore firing lane before shooting (kiting behavior)
- [ ] Archer has no hidden melee pressure when in close range

Record:
- `slime_fairness_score (1-5)`
- `skeleton_range_fairness_score (1-5)`
- `archer_projectile_readability_score (1-5)`
- `enemy_with_most_unfair_hits`
- `platform_clipping_incidents`
- `stacked_platform_failures`

## Session F - First Boss and Scripted Defeat Flow (20-30 min)

### Siren phase behavior
- [ ] Phase 1 reads as ranged spacing and projectile pressure
- [ ] Phase 2 clearly introduces teleport repositioning
- [ ] Phase 3 clearly upgrades to multi-shot volleys
- [ ] Boss remains inside the room bounds (no arena escape)

### Add-wave vulnerability loop
- [ ] Red slimes spawn each phase in room-local zones
- [ ] Clearing red slimes is readable as prerequisite to meaningful boss damage
- [ ] Add-wave count per phase feels intentional (not random clutter)

### Scripted loss splash
- [ ] Defeat path triggers narrative splash reliably
- [ ] CONTINUE input reliably dismisses splash and returns control
- [ ] Post-splash progression aligns with Act II scripted-loss expectations

Record:
- `boss_phase_readability_score (1-5)`
- `boss_damage_window_clarity (1-5)`
- `scripted_loss_overlay_success (yes/no)`
- `boss_room_escape_seen (yes/no)`

## Session E - Progression and Persistence (10-15 min)
- [ ] Exiting and relaunching from launcher preserves expected progress
- [ ] Returning player context is understandable
- [ ] Hub/progression state feels coherent after reload

Record:
- `save_load_confidence (1-5)`
- `missing_or_confusing_state_after_reload`

---

## 7) Detailed Feedback Gathering Areas

Use these IDs in notes, bug reports, and balancing reviews.

| ID | Area | What to capture | Why it matters |
|---|---|---|---|
| `UX-LAUNCH` | Launcher and entry flow | Confusion points, failed starts, mode-select clarity | First-minute abandonment risk |
| `UX-CONTROLS` | Input and control discoverability | Any action that felt hidden or unintuitive | Lowers onboarding friction |
| `UX-MOVE` | Traversal responsiveness | Delay, missed inputs, inconsistent jump/dash outcomes | Core game identity is movement mastery |
| `UX-READABILITY` | Visual and combat readability | Could player parse threat, space, and affordances quickly? | Reduces "cheap" deaths |
| `UX-COMBAT` | Combat feel and pacing | Is combat supportive or dominant vs traversal? | Aligns with "light combat" design pillar |
| `UX-SYSTEMS` | Yin/Yang/Lantern understanding | Can player explain what changed and why? | Systems must be felt, not hidden |
| `UX-NARRATIVE` | Emotional arc delivery through play | Hub return feeling, loss/recovery tone, act transitions | Validates narrative-through-mechanics goal |
| `UX-PROGRESSION` | Mission and progression confidence | Clarity of next objective and unlock logic | Prevents churn from uncertainty |
| `BAL-ENEMY` | Enemy archetype tuning | Fairness and pressure for slime/skeleton/archer/bosses | Main balancing loop input |
| `BAL-DIFFICULTY` | Difficulty curve quality | Spike locations, retry load, fatigue points | Keeps challenge intentional |
| `BAL-RESOURCES` | Economy and sustain pressure | Potion/fragment scarcity or overload | Impacts long-session pacing |
| `TECH-STABILITY` | Runtime reliability | Crashes, hard-locks, visual corruption, desync-like behavior | Release-blocking health |

---

## 8) Balance-Specific Questions (Answer Explicitly)

### Slime range update
- Did slime hits now match visible forward body extension?
- Did you ever feel hit from behind/side when visual did not support it?
- If unfair, estimate distance error in "tiles" or "character widths".

### Skeleton +15% range
- Did added range feel like healthy threat or surprise/unreadable poke?
- Could you learn spacing reliably after 2-3 encounters?
- Did guard + longer reach create unavoidable damage chains?

### Archer projectile behavior
- Could you reliably identify incoming projectiles before impact?
- Did projectile speed feel dodgeable with current movement kit?
- Were encounters with multiple archers still readable?

### Global tuning
- Which enemy type currently causes the most "unearned" damage?
- Which enemy is now too weak to be interesting?
- If one tuning change should be next, what is it and why?

---

## 9) Feedback Templates

## A) Session Summary Template

```md
### Session Summary
Build: v0.11.29
Mode: SOLO / CAMPAIGN
Session length: XX min

Top 3 positives:
1.
2.
3.

Top 3 pain points:
1.
2.
3.

Most likely churn moment:

Overall alignment to intended experience (1-5):

IDs used: UX-___, BAL-___, TECH-___
```

## B) Encounter and Balance Template

```md
### Encounter Note
Area/room:
Enemy type(s):

What happened:
Expected behavior:
Observed behavior:

Fairness score (1-5):
Readability score (1-5):
Suggested adjustment:

ID: BAL-ENEMY / BAL-DIFFICULTY / UX-READABILITY
```

## C) Bug Template (Launcher-Only)

```md
### Bug Report
Build: v0.11.29
Mode: SOLO / CAMPAIGN
Severity: blocker / high / medium / low

Steps to reproduce:
1.
2.
3.

Expected:
Observed:
Repro rate:

Attachments:
- screenshot/video
- optional log snippet from user_data/logs/client.log

ID: TECH-STABILITY / UX-___ / BAL-___
```

---

## 10) Version Notes (Player-Visible, Recent)

| Version | Player-visible impact |
|---|---|
| `v0.11.29` | Enemy/platform reliability pass, archer kiting behavior, skeleton directional guard+retreat, Siren 3-phase baseline, scripted-loss continue splash |
| `v0.11.28` | Release metadata sync for launcher/release pipeline (`version.json` + Gradle version) and launcher UX guide alignment |
| `v0.11.27` | Launcher-only UX test handbook refresh: updated expected scope, structured feedback IDs, and balancing capture templates |
| `v0.11.26` | Enemy tuning pass: slime forward lunge reach update, skeleton range +15%, archers fire damaging projectiles |
| `v0.11.25` | Echo system foundation (`SimEcho`) integrated server-side for future puzzle loops |
| `v0.11.24` | Enemy hitbox and attack-zone alignment fixes |
| `v0.11.23` | Enemy targeting and hitbox tuning refinements |
| `v0.11.10` | Boss psychological patterns live (Siren, Echo Warden, Time Leech Lord, Memory Eater) |
| `v0.11.6-0.11.9` | Yin/Yang and Lantern HUD systems plus vignette clarity fixes |

---

## 11) Exit Criteria for This Guide

This guide is considered successful when a launcher-only tester can:
1. Enter and play without setup confusion.
2. Provide actionable feedback tied to `UX-*`, `BAL-*`, and `TECH-*` IDs.
3. Identify whether current experience matches intended GDD pillars.
4. Produce at least one concrete balancing recommendation from actual play.

---

*Keep this file aligned with release tags and plan updates every loop.*
