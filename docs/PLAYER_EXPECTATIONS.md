# Shadow Ascent — Player Expectations Guide
## Living Document: What Works, What to Expect, How to Test

**Current version:** v0.11.12 | **Last updated:** 2026-04-12
**How to start:** Launch the game using the launcher application (launcher.exe / launcher shortcut)

---

## Quick Status: What's Playable Right Now

| Feature | Status | Notes |
|---------|--------|-------|
| Solo mode (no server) | **Working** | Select "Solo" on mode select screen |
| Campaign/Multiplayer | **Working** | Requires server running |
| Yin/Yang system | **Working** | Bars visible in HUD bottom-left |
| Lantern system | **Working** | Meter visible; vignette responds |
| Vignette overlay | **Working (v0.11.9)** | Transparent gradient at screen edges; GL blend bug fixed |
| Hub state machine | **Working** | Hub evolves as you play |
| NPC roster sync | **Working** | NPCs appear/vanish per hub state |
| Player animations (unarmed) | **Working** | 81 production sheets loaded |
| Player animations (sword) | **Working** | 90 sword sheets loaded |
| Crouch/crouch-walk | **Working** | Hold S or down-arrow |
| Swim states | **Working** | Enters water → swim/swim_idle |
| Enemy AI | **Working (v0.11.10)** | IDLE/PATROL/CHASE/ATTACK/FLEE/GUARD/STUNNED/DEAD — skeleton blocks, enemies flee at low HP |
| Boss encounters | **Working (v0.11.10)** | 4-phase FSM + Shadow Ascent patterns (Siren, Echo Warden, Time Leech Lord, Memory Eater) |
| Save state | **Working** | Currency, inventory, abilities, visited rooms |
| Replay recording | **Working** | `-Dninja.record` flag; .ndjson in user_data/replays/ |
| Enemy sprites | **Working (v0.11.12)** | Real animated sprites: swordsman, skeleton, slime, spearman, archer |
| Climb/ledge animations | **Partial** | States wired; sheets available but need FSM routing |
| Boss (Shadow Ascent) | **Working (v0.11.10)** | Siren, Echo Warden, Time Leech Lord, Memory Eater — BossPatternLibrary |
| Echo system | **Not started** | M6 |
| Act IV depression mechanics | **Not started** | M7 |
| Arcade mode | **Not started** | Separate roadmap |
| Sandbox mode | **Not started** | Separate roadmap |

---

## Full Test Checklist — v0.11.12

Run each of these in order. Start every session by opening the launcher application.

### 1. Launch & Mode Select

- [ ] Open the launcher — window appears with server address field, CONNECT and QUIT buttons
- [ ] Click CONNECT → Mode Select screen appears
- [ ] Four mode cards visible: ARCADE (green), CAMPAIGN (blue), SOLO (purple), SANDBOX (gold)
- [ ] Arrow keys navigate between cards; Enter or click selects
- [ ] Select SOLO → game starts without needing a server

### 2. HUD

- [ ] Bottom-left: Yin bar (blue), Yang bar (orange)
- [ ] Bottom-left: Lantern meter below Yin/Yang
- [ ] Bars animate as values change
- [ ] "FLOW" indicator appears when Yin ≈ Yang (within 0.15)

### 3. Movement

- [ ] Left/Right arrow keys move the player horizontally
- [ ] Space or Up to jump; variable height hold
- [ ] Double-jump (if unlocked)
- [ ] Dash: Shift key — quick horizontal burst
- [ ] Wall-slide: hold toward wall while airborne
- [ ] Crouch: Down arrow or S — player crouches with animation
- [ ] Crouch-walk: hold Down and move — crouch-walk animation plays
- [ ] Enter water tile → swim animation plays
- [ ] Stationary in water → swim_idle animation plays

### 4. Vignette (key v0.11.9 fix)

- [ ] When Lantern value is high (>0.7): minimal or no vignette; world fully visible
- [ ] When Lantern value is mid (0.3–0.7): soft transparent gradient at screen edges
- [ ] When Lantern value is low (<0.3): deep vignette darkens edges; red tint visible
- [ ] **Critical check**: game world (terrain, player, enemies) should ALWAYS be visible through vignette — it is a transparent overlay, not a solid mask
- [ ] Moving through dark areas causes Lantern decay; world darkens gradually
- [ ] Collecting a lantern fragment restores Lantern meter

### 5. Yin/Yang Effects

- [ ] Collect a yin_fragment pickup → Yin bar increases
- [ ] At Yin > 0.7: hidden platforms become visible (revealed with alpha proportional to Yin)
- [ ] Collect a yang_fragment pickup → Yang bar increases
- [ ] At Yang > 0.7: attack damage increases (combat feedback)
- [ ] With both bars balanced: FLOW mode indicator shows; companion orbs orbit more quickly

### 6. Hub System

- [ ] Hub starts in FULL state: multiple NPCs visible (vendors, mentors, training dummies)
- [ ] After first boss defeat: hub transitions to CORRUPTED — some NPCs vanish, dialogue changes
- [ ] Siren encounter (planned M5): hub transitions to EMPTY; only Siren remains
- [ ] Hub 2 (Chasm): begins FRACTURED; NPCs return as fragments collected

### 7. Enemies

- [ ] Enemies spawn in level rooms
- [ ] PATROL: enemy walks between waypoints
- [ ] CHASE: player enters detection range → enemy pursues
- [ ] ATTACK: enemy enters attack range → attack animation + player takes damage
- [ ] **FLEE (v0.11.10)**: damage enemy below 25% HP → enemy turns and retreats; animation plays (not T-pose)
- [ ] **GUARD (v0.11.10, skeleton only)**: skeleton may raise shield instead of attacking; hit during GUARD deals ~1/3 damage
- [ ] STUNNED: hit enemy → stun animation, then returns to PATROL
- [ ] Enemy dies at 0 HP → loot drops (coins, fragments)
- [ ] **Enemy sprites (v0.11.12)**: real animated sprites visible for swordsman, skeleton, slime, spearman, and archer — no more colored rectangles
- [ ] **Death animation (v0.11.12)**: enemy plays death anim to last frame before disappearing; does not vanish instantly
- [ ] **Spearman (v0.11.12)**: skeleton with spear spawns at mid-depth rooms; longer attack reach than swordsman
- [ ] **Archer (v0.11.12)**: skeleton archer spawns at high-depth rooms; kites at range rather than chasing

### 8. Bosses

- [ ] Boss room spawns one boss (type determined by room seed)
- [ ] Boss has 4 phases: combat intensifies at 75%, 50%, 25% HP
- [ ] PHASE_TRANSITION: brief pause, then resumes at higher speed
- [ ] VULNERABLE window: 3 seconds of increased damage window
- [ ] Boss death → loot spawn → room clears
- [ ] **Siren (v0.11.10)**: scripted loss — Siren drains Yin/Yang to 0 over ~6 s; player collapses; hub transitions to EMPTY
- [ ] **Echo Warden (v0.11.10)**: mirrors player X with 0.5 s delay ring buffer; boss attacks when it catches up
- [ ] **Time Leech Lord (v0.11.10)**: Lantern drains constantly; spawns Time Leech minions every 8 s; speed burst at 30% HP
- [ ] **Memory Eater (v0.11.10)**: resets platform positions on each phase change; unlocked doors can relock

### 9. Combat

- [ ] Z key: basic attack (combo chain: slash1 → slash2 → slash3)
- [ ] X key: throw shuriken
- [ ] Sword state: if weapon equipped — sword-specific animations play
- [ ] Unarmed state: punch/kick animations

### 10. Persistence (Solo)

- [ ] Die → respawn at last checkpoint; currency/inventory preserved
- [ ] Exit solo and re-enter → progress saved (visited rooms, abilities)

---

## What You Should NOT See (Known Issues Would Look Like This)

- **Black screen / all-white screen**: If the vignette covers the world entirely → GL blend regression. Check ChunkRenderer.renderVignette().
- **Magenta rectangles for player**: Animation sheets not found under `assets/sprites/player/unarmed/`. Check that extraction ran.
- **Colored rectangles for enemies**: Should no longer appear in v0.11.12+ — if seen, the launcher may be running an old JAR. Relaunch.
- **Missing HUD bars**: YinYangComponent or LanternComponent not wired on the entity. Check GameSimulator.

---

## Version History (Player-Visible Changes)

| Version | What Changed for the Player |
|---------|----------------------------|
| v0.11.12 | **Enemy art + type corrections**: real animated sprites for all 5 types (swordsman, skeleton, slime, spearman, archer); death animation plays to completion; spearman and archer spawn in world |
| v0.11.11 | **Enemy spritesheets shipped**: 37 sheets stitched from art ZIP; frame counts calibrated to actual 128×96 art |
| v0.11.10 | **M5 — Enemy AI + Boss Patterns**: FLEE/GUARD enemy states; skeleton shields; Siren, Echo Warden, Time Leech Lord, Memory Eater bosses |
| v0.11.9 | **Vignette fix**: transparent overlay restored — game world now always visible through darkness effect |
| v0.11.8 | Smoother vignette gradient (20 layers, quadratic curve); corner overlap fixed; base dim layer added |
| v0.11.7 | Vignette works in solo mode; crouch-walk and swim animations wired; companion orbs scale with Yin/Yang; HUD redesign |
| v0.11.6 | Yin/Yang bars and Lantern meter appear in HUD; vignette darkens screen edges; 171 player sprite sheets; sword animation routing |
| v0.11.5 | Solo replay recording; `.ndjson` replay files written to `user_data/replays/`; launcher replay viewer |
| v0.11.4 | Log files now write to disk; server starts correctly from launcher |
| v0.11.3 | Portal NPE fix in solo; full save state (currency, inventory, abilities) |
| v0.11.2 | Solo multi-room world works; hub NPCs authority fix |
| v0.11.1 | Hub evolution: NPCs appear/vanish per act; Acts I–VI wired |
| v0.11.0 | Solo mode added: play without a server; physics regression tests closed |

---

## Upcoming: What's Being Built

### v0.11.13 — Milestone 6: Echo System & Puzzles

- **Echo recording**: player leaves an echo trail through rooms; echoes replay past movements
- **Echo-trigger zones**: step into a zone → echo activates; used for pressure-plate puzzles
- **Puzzle archetypes**: echo-door (echo must stand on plate), echo-bridge (echo carries light across gap)
- **Fragment drop → boss rewards**: defeating a Shadow Ascent boss drops a story fragment / ability unlock

### v0.11.12 — SHIPPED

#### Enemy type corrections

All 5 enemy types now correctly named and playable with real animated sprites:

- **swordsman** — greatsword skeleton; slow heavy overhead smash
- **skeleton** — sword + shield skeleton; GUARD state blocks melee hits
- **slime** — ground-only; three attack variants; no jump
- **spearman** — skeleton with spear; longer attack reach; spawns at mid-depth (3+)
- **archer** — skeleton archer; kites at range; spawns at high-depth (6+) and boss/treasure rooms

#### Death animation hold

Enemies now play their death animation to the last frame before disappearing, instead of vanishing instantly on death.

### v0.11.10–11 — SHIPPED

#### Enemy AI expanded

- FLEE state: enemies retreat when HP drops below 25%
- GUARD state (skeleton only): skeleton raises shield; blocked hits deal ~1/3 damage

#### Shadow Ascent boss patterns

- **Siren of the Veiled Vale** — scripted loss; strips Yin/Yang to 0 over 6 s; hub collapses to EMPTY
- **Echo Warden** — mirrors player X with 0.5 s delay; attacks when it catches the player
- **Time Leech Lord** — drains Lantern constantly; spawns minions every 8 s; speed burst at 30% HP
- **Memory Eater** — resets platform positions on each phase transition

---

## Design Reference

| GDD System | Code status | First playable |
|------------|-------------|----------------|
| Yin/Yang (§3.3) | Done (v0.11.6) | v0.11.6 |
| Lantern (§3.4) | Done (v0.11.6) | v0.11.6 |
| Hub evolution (§4) | Done (v0.11.1) | v0.11.1 |
| Narrative Act FSM (§5) | Done (v0.11.1) | v0.11.1 |
| Boss AI — psychological (§7) | Done (v0.11.10) | v0.11.10 |
| Echo system (§6) | Not started (M6) | v0.11.13+ |
| Act IV depression (§5) | Not started (M7) | v0.11.14+ |
| Proof token / labyrinth (§5) | Not started (M6) | v0.11.13+ |
| Arcade mode (§0.2) | Not started | TBD |
| Sandbox mode (§0.3) | Not started | TBD |

---

*This document is updated with every release. "What You Should NOT See" section tracks known regressions to watch for during playtesting.*
