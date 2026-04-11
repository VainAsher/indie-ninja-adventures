# SHADOW ASCENT: THE HOLLOWED NINJA

## Full Game Design Document (GDD)

---

# 0. GAME MODES OVERVIEW

Indie Ninja Adventures ships three discrete modes. Each has its own loop, tone, and target player. They share the same engine, art, and ability set but differ in narrative, pacing, and world structure.

---

## 0.1 Solo / Campaign (Shadow Ascent)

**Tagline:** *The Hallowed Ninja reclaims their Yin and Yang.*

* **Genre:** Narrative Metroidvania platformer
* **Pacing:** Deliberate; story-driven
* **World:** Instanced hub + mission levels; procedurally generated interconnected rooms
* **Portal system:** Hub world connects to level zones via portals; players travel back and forth
* **Co-op:** Drop-in / drop-out (1–4 players); Yin/Yang balance tracked per player
* **Narrative:** Full 7-act emotional arc (Sections 1–7 of this document describe this mode)
* **Player identity:** The Hallowed Ninja
* **Persistence:** Full save file (abilities, story flags, hub state, visited rooms)

The canonical mode. All GDD sections that follow describe this mode unless stated otherwise.

---

## 0.2 Arcade Mode

**Tagline:** *Fast, brutal, endless.*

* **Genre:** Roguelike run-based platformer
* **Pacing:** High-speed; narrative stripped
* **World:** Procedurally generated rooms per run; smaller room size than Campaign; no hub
* **Run structure:** Continuous dungeon; death ends the run; score accumulates
* **Modifiers:** Pre-run loadout selection (weapon type, ability set, passive modifiers)
* **Builds:** Player builds around powerup/modifier synergies discovered mid-run
* **Co-op:** Lobby-based (fixed party before run); no drop-in mid-run
* **Narrative:** None. Cosmetic unlock rewards only.
* **Player identity:** Unnamed Ninja (customisable appearance)
* **Persistence:** Leaderboard scores, unlocked cosmetics, loadout presets
* **Key differences from Campaign:** No hub, no Yin/Yang story system, no Lantern mechanic; combat is primary loop not secondary

---

## 0.3 Sandbox Mode

**Tagline:** *Build your world. Live in it.*

* **Genre:** 2D ninja Minecraft/Terraria-style sandbox
* **Pacing:** Open-ended; player-set goals
* **World:** Endless procedurally generated interconnected world; no instancing; all players in same persistent world
* **World generation settings:** User-configurable (world seed, biome composition, enemy density, quest frequency, day/night cycle speed)
* **Building:** Place and remove blocks; construct shelters, training grounds, clan halls
* **Quests:** Procedurally generated optional objectives; no critical path
* **Co-op:** Always-on persistent multiplayer; server-hosted world
* **Narrative:** None enforced. Environment tells emergent stories.
* **Player identity:** Disciples / Acolytes (NOT the Hallowed Ninja); the player is not the protagonist
* **Persistence:** Persistent world file; per-player inventory and position in the shared world
* **Key differences from Campaign:** No instanced zones, no acts, no story flags; players are not the Hallowed Ninja; world is constructed and destructed by players; primary loop is exploration and survival

---

# 1. GAME OVERVIEW

## 1.1 High Concept

A 2D narrative-driven platformer where players embody a disgraced ninja who has lost their Yin and Yang, and must rebuild themselves through challenge, isolation, and community in order to become whole again.

## 1.2 Genre

* 2D Platformer
* Narrative Adventure
* Light Metroidvania

## 1.3 Core Pillars

* Emotional storytelling through gameplay (no direct exposition)
* Hub evolution as narrative delivery
* Mechanical representation of mental state (Yin/Yang & Lantern)
* Climbing and movement mastery as growth
* Loss, rebuilding, and self-reclamation

---

# 2. CORE GAME LOOP

1. Enter Hub
2. Accept mission / access level
3. Complete platforming challenge + boss encounter
4. Earn fragment (Yin, Yang, or Lantern)
5. Return to hub
6. Hub evolves (NPCs added/removed, areas unlocked)
7. Unlock new abilities / pathways
8. Repeat

---

# 3. CORE MECHANICS

## 3.1 Movement

* Run, jump, wall-jump
* Dash (unlockable)
* Grapple / rope (late game)
* Climb surfaces

Movement evolves over time to reflect mastery and emotional stability.

## 3.2 Combat (Light)

* Basic sword strikes
* Charged attacks (Yang-based)
* Defensive/parry abilities
* Limited enemy focus (platforming-first design)

## 3.3 Yin & Yang System

### Yin (Emotion)

* Reveals hidden platforms
* Slows time perception
* Enhances environmental awareness

### Yang (Discipline)

* Increases attack strength
* Improves movement precision
* Reduces stamina drain

### Balance State

* Unlocks “Flow Mode”
* Smooth animation blending
* Enhanced traversal + combat

## 3.4 Lantern System (Mental State)

* Acts as global modifier

Low Lantern:

* Darkened world
* Missing platforms
* Reduced control

High Lantern:

* Clear pathways
* Extended jumps
* Environmental assistance

---

# 4. HUB SYSTEM DESIGN

## 4.1 Hub Philosophy

The hub is the emotional center of the game. It evolves to reflect the player’s internal state.

---

## 4.2 HUB 1 — Bamboo Courtyard

### State 1: Full

* Multiple NPCs (vendors, mentors, allies)
* Bright, stable environment

### State 2: Corruption

* NPCs disappear
* Dialogue shifts
* Prices increase
* Areas close

### State 3: Empty

* Only player + Siren NPC remain

---

## 4.3 HUB 1 BOSS EVENT

### Boss: Siren of the Veiled Vale

* Scripted loss encounter
* Player is stripped of Yin & Yang
* Hub collapses

---

## 4.4 HUB 2 — Chasm of Still Shadows

### Initial State

* Empty
* Broken terrain
* Limited movement

### Progression

* NPCs return one-by-one
* Each return unlocks mechanics or upgrades

---

## 4.5 HUB EVOLUTION SYSTEM

Each boss defeated:

* Adds NPC
* Unlocks new hub area
* Changes visual tone

---

# 5. WORLD STRUCTURE

## ACT I — The Rise (Tutorial)

* Training levels
* Introduces movement and basic mechanics

## ACT II — The Fall

* Hub corruption
* Siren influence increases

## ACT III — The Labyrinth Court

* Maze-based levels
* Unfair systems
* Proof token mechanic

## ACT IV — The Break

* Minimal UI
* Slowed gameplay
* Depression mechanics

## ACT V — The Hearth Mountain

* Recovery mechanics introduced
* Community-based traversal

## ACT VI — The Ascent

* Climbing-focused levels
* Yin/Yang reintegration

## ACT VII — The Upper Peaks

* Final hub
* Full ability access
* Narrative resolution

---

# 6. PUZZLE & CO-OP SYSTEM DESIGN

## 6.1 Design Philosophy

Puzzles reinforce the core themes of trust, communication, growth, and interdependence. Even in single-player, mechanics simulate cooperation through echoes, NPC spirits, or split-control mechanics.

Core principles:

* No long idle time
* Fail-forward design (mistakes teach, not punish)
* Communication over execution (even in solo via delayed feedback systems)
* Scalable complexity (based on player count or progression)

---

## 6.2 Puzzle Archetypes (Integrated Systems)

### 🧩 Asymmetric Ability Locks

Players (or player + echoes) have different abilities.

Examples:

* Phase through walls
* Carry heavy objects
* Activate distant switches

Design Use:

* Introduce “Echo Forms” in solo play that mimic co-op roles
* In co-op mode, players take distinct roles

Twists:

* Rotate abilities mid-level
* Force role swaps at checkpoints

---

### 🔁 Chain-Reaction Mechanisms

Actions ripple through the level.

Examples:

* Lever → water flow → platform rise → hidden switch

Design Use:

* Multi-step environmental puzzles tied to Lantern state

Twists:

* Delayed triggers requiring anticipation
* Incorrect order causes partial reset (not full failure)

---

### ⏳ Simultaneous Timing Challenges

Examples:

* Multiple pressure plates
* Synchronized platform traversal

Design Use:

* Echo clones replicate past actions (single-player solution)

Twists:

* Players separated visually
* Timing windows shrink with difficulty

---

### 👁️ Information Asymmetry

Examples:

* Invisible symbols only visible in Yin state
* Audio cues tied to Yang rhythm

Design Use:

* Yin reveals hidden truth
* Yang interacts with physical systems

Twists:

* Partial or misleading information
* Rotating perspective roles

---

### 🌊 Environmental State Manipulation

Examples:

* Flooding rooms
* Freezing lava

Design Use:

* Directly tied to Lantern and Yin/Yang balance

Twists:

* One path opens while another closes
* Persistent world changes affect future levels

---

### 🧠 Memory & Pattern Recognition

Examples:

* Symbol sequences
* Split pattern recall

Design Use:

* Yin enhances memory clarity

Twists:

* Each player sees partial data
* Patterns evolve dynamically

---

### 🧲 Physics-Based Interaction

Examples:

* Player boosting
* Momentum puzzles

Design Use:

* Advanced traversal challenges in later acts

Twists:

* Wind, gravity shifts, slippery terrain

---

### 🔐 Human Key Mechanics

Examples:

* Player holds position to unlock door

Design Use:

* Echo projections can “stand in” temporarily

Twists:

* Moral tension: leave echo behind or reclaim it?

---

### 🧬 Ability Evolution Puzzles

Examples:

* Unlock ability → revisit area → new solution

Design Use:

* Core Metroidvania progression

Twists:

* Different builds unlock different routes

---

### 🧭 Split-Path Coordination

Examples:

* Upper vs lower path interaction

Design Use:

* Multi-layer level design

Twists:

* Risk vs speed trade-offs

---

## 6.3 Signature System — “The Living Dungeon”

Hybrid puzzle encounters combining:

* Environmental shifts
* Asymmetric roles
* Timed mechanics
* Memory sequences
* Split-path coordination

Used for:

* Major story levels
* Endgame challenges

---

# 7. ENEMIES & BOSSES

## Enemy Types

* Hollow Echoes (mimic movement)
* Time Leeches (drain stamina)
* Masked Constructs (illusion-based enemies)

## Boss Design Philosophy

Each boss represents a psychological or systemic obstacle.

### Example Bosses

* Echo Warden (self-doubt)
* Time Leech Lord (burnout)
* Labyrinth Sentinel (systemic resistance)
* Memory Eater (loss of identity)

---

# 7. PROGRESSION SYSTEM

## Unlock Types

* Movement abilities
* Yin fragments
* Yang fragments
* Lantern upgrades

## Gating

* Ability-based progression
* Hub state progression

---

# 8. NARRATIVE DESIGN

## Delivery Method

* Environmental storytelling
* NPC dialogue (minimal, symbolic)
* Visual transitions

## Key Themes

* Isolation
* Control vs freedom
* Identity rebuilding
* Community healing

---

# 9. ART & AUDIO DIRECTION

## Visual Style

* Soft shadows
* High contrast lighting
* Silhouetted environments

## Inspirations

* Ori-style lighting
* Hollow Knight tone

## Audio

* Ambient-driven
* Minimal dialogue
* Dynamic music based on Lantern state

---

# 10. UI/UX DESIGN

## UI Elements

* Minimal HUD
* Lantern meter
* Yin/Yang indicators

## Feedback Systems

* Visual glow intensity
* Controller vibration (optional)

---

# 11. TECHNICAL CONSIDERATIONS

## Engine Options

* Unity (recommended)
* Godot (alternative)

decided on Java implemnetation, with python launcher

## Systems Needed

* State-driven hub system
* NPC state tracking
* Ability gating system
* Dynamic environment changes

---

# 12. ENDGAME & RESOLUTION

## Final State

* Balanced Yin/Yang
* Fully restored hub
* Open traversal

## Final Message

The player does not reclaim what was lost directly.
They become whole, stable, and ready for whatever comes.

---

# 13. FUTURE EXPANSION IDEAS

* New challenge dungeons
* Alternate endings based on balance
* New game + with altered hub progression

---

# END OF DOCUMENT
