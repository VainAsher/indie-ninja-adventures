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

### 1.4 Design Realignment Addendum (`2026-04-13 22:41:01 +01:00`)

This addendum realigns Shadow Ascent toward a stance-driven mastery loop without
rewriting narrative structure.

#### Updated Pillar Structure

* Movement mastery
* Yin/Yang stance gameplay
* Balance-driven Flow state
* Echo time-clone integration
* Stance-expressive phase teleport
* Lantern as mastery amplifier
* Gear-driven playstyle expression

This shifts gameplay from static stat bonuses toward intentional style switching.

---

# 2. CORE GAME LOOP

### 2.1 Meta loop (hub progression)

1. Enter Hub
2. Accept mission / access level
3. Complete platforming challenge + boss encounter
4. Earn fragment (Yin, Yang, or Lantern)
5. Return to hub
6. Hub evolves (NPCs added/removed, areas unlocked)
7. Unlock new abilities / pathways
8. Repeat

### 2.2 Moment-to-moment loop (stance and Flow)

1. Enter room
2. Choose a Yin or Yang approach
3. Execute stance-specific movement/combat actions
4. Drift toward imbalance
5. Rebalance via opposite stance actions
6. Trigger temporary Flow window
7. Exploit Flow for traversal/combat burst
8. Return toward neutral and repeat

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

## 3.3 Yin & Yang System (Stance Model)

Yin and Yang are not passive meters; they are active stances with distinct feel.

### Yin Stance (Control / Stealth)

* Quiet movement profile
* Safer setup and positioning tools
* Puzzle-first and avoidance-first options
* Precision-focused movement handling

### Yang Stance (Aggression / Action)

* Higher offensive pressure and commit speed
* Faster burst movement options
* Break-through and direct-engagement behavior
* Louder, riskier play profile

### Balance and Flow State

Flow is triggered by balanced recent action usage, not static stat stacking.

* Movement gains: smoother acceleration, cleaner chaining, reduced friction
* Combat gains: faster recovery, reduced action tax, stronger aerial control
* Traversal gains: stronger dash/teleport consistency and forgiveness

Flow is short, skill-earned, and must be maintained through continued rebalance.

## 3.4 Lantern System (Mastery Amplifier)

Lantern remains the emotional clarity axis but now scales systemic mastery effects.

Low Lantern:

* Short Flow windows
* Weaker Flow bonuses
* Less stable Echo/teleport execution

Mid Lantern:

* Baseline Flow duration and reliability
* Stable Echo utility

High Lantern:

* Extended Flow windows
* Stronger Flow amplification
* Highest teleport precision and Echo stability

Lantern does not replace stance play; it amplifies successful stance balancing.

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

### 10.3 Controls Setup Specification
#### 10.3.1 Controls Philosophy

Shadow Ascent uses a layered control model designed to preserve platforming clarity while supporting stance-driven expression, stealth, traversal mastery, and light combat.

The controls are built around four principles:

Movement profile and stance are separate systems.
Live inputs are reserved for real-time play.
Upgrades expand existing action families rather than adding new permanent buttons.
Context and stance modify outcomes, not button locations.

This ensures that the player always understands what their inputs mean, even as the game gains complexity through progression.

#### 10.3.2 Design Goals

The control setup must satisfy the following goals:

A. Preserve movement readability

The player must always feel precise control over:

walking
running
crouching
jumping
climbing
dashing

No advanced system may compromise core platforming readability.

B. Separate physical movement from expressive stance

Movement profile states determine:

speed
sound
detection
body posture

Yin/Yang stance determines:

tactical identity
combat feel
traversal expression
tool behavior

These layers must remain independent.

C. Protect input space for mastery systems

Real-time buttons are reserved for:

movement
combat
stance switching
traversal arts
Echo arts
interaction

Systems such as inventory, crafting, loadout editing, and codex/journal access are handled through menu layers or safe-state interfaces.

D. Allow advanced systems to scale cleanly

Traversal and Echo are designed as expandable action families. New upgrades should deepen these families through context, chaining, and variation rather than introducing new permanent buttons.

#### 10.3.3 Input Layers

Player control is interpreted through multiple simultaneous layers.

Layer 1: Locomotion Profile

Controls physical movement state, posture, and detection behavior.

States include:

Stand Idle
Walk
Run
Crouch Idle
Crouch Walk
Jump
Rise
Fall
Air Control
Wall Slide
Wall Jump
Climb
Swim Surface
Swim Submerged
Water Jump / Surface Exit
Layer 2: Stance

Controls tactical identity and move expression.

States:

Yin
Yang
Flow-enhanced Yin
Flow-enhanced Yang
Layer 3: Action Overlay

Controls currently executed actions.

Actions:

Melee Attack
Thrown Tool
Dash
Guard / Parry
Traversal Art
Echo Art
Interact
Layer 4: Context Resolution

Determines which action variant is executed based on:

grounded / airborne / wall / swimming state
nearby traversal anchors
phase-compatible geometry
active Echo targets
interactable objects or NPCs
current stance
current Flow state
#### 10.3.4 Locomotion Specification

Locomotion is divided into four major categories:

grounded locomotion
aerial locomotion
wall locomotion
swimming locomotion

These are independent of Yin/Yang stance.
Stance modifies expression, but does not replace the movement rules of the body.

##### 10.3.4.A Grounded Locomotion

Grounded locomotion determines physical presence, sound, and detection while on solid terrain.

Walk

Default grounded movement state.

Properties:

medium speed
medium sound
medium detection
full control availability
Run

Fast grounded movement state.

Properties:

highest grounded speed
loudest movement profile
highest detection risk
strongest momentum carry
Crouch Idle

Low-profile stationary state.

Properties:

minimal sound
minimal visual profile
reduced detection
restricted movement posture
Crouch Walk

Slow stealth movement state.

Properties:

lowest speed
lowest sound
lowest detection profile
strongest stealth utility
Design Rationale

Grounded locomotion expresses the player’s physical presence in the world. It directly supports stealth, pacing, and readable movement risk.

##### 10.3.4.B Aerial Locomotion

Aerial locomotion governs player control after leaving the ground.

Jump

Primary vertical movement action.

Properties:

initiated from grounded or valid wall/swim exit states
consistent core input across the full game
may gain follow-up interactions through upgrades
Rise / Fall

Airborne movement phases following jump or launch.

Properties:

air steering allowed within defined tuning limits
jump timing remains stable across stance states
dash, attack, thrown tool, traversal art, and Echo may layer over these states where valid
Air Control

The player retains directional influence while airborne.

Properties:

stronger or weaker based on stance tuning, Flow, upgrades, or environmental conditions
should remain readable and deterministic
Design Rationale

Air locomotion must feel reliable. Jump is one of the most trusted actions in a platformer and must remain stable even as stance and progression deepen the movement system.

##### 10.3.4.C Wall Locomotion

Wall locomotion includes wall contact, wall slide, and wall jump.

Wall Slide

Triggered when the player is airborne, adjacent to a valid wall surface, and providing directional input toward that surface.

Properties:

slows downward descent
creates a controlled transition state
may reduce landing risk and create timing windows for wall jump or traversal art
Wall Jump

Triggered by jump input while in valid wall contact state.

Properties:

launches player away from wall
direction is derived from wall contact and movement input
may chain into dash, traversal art, or air actions depending on progression
Wall Climb

If climbable surfaces are supported, wall movement may extend into climb state.

Properties:

slower vertical traversal
may consume stamina, focus, or stance-dependent movement cost if desired by design
compatible with stealth-heavy or traversal-heavy level design
Yin Wall Behavior

Typically favors:

more precise control
safer repositioning
stronger correction and stability
Yang Wall Behavior

Typically favors:

more aggressive push-off
faster re-entry to momentum
stronger burst chaining
Design Rationale

Wall interaction is a core part of platforming mastery and should be treated as a first-class locomotion system rather than a minor extension of jumping.

##### 10.3.4.D Swimming Locomotion

Swimming locomotion governs movement while the player is partially or fully submerged.

Swimming should be treated as a full movement state family, not as a temporary environmental gimmick.

Swim Surface

The player is at or near the water surface.

Properties:

horizontal movement emphasized
vertical control limited by buoyancy and surface rules
jump input may trigger water breach or surface exit
Swim Submerged

The player is fully underwater.

Properties:

full directional movement available within water tuning rules
movement speed, drag, and action timing differ from grounded and aerial states
audio/detection behavior changes appropriately for underwater stealth or disturbance
Water Jump / Surface Exit

Triggered when jump input is pressed at a valid surface threshold or from specific edge conditions.

Properties:

launches the player from water into air state
may chain into dash, attack, traversal art, or ledge recovery depending on progression
Swimming Design Rules
swimming must use the same core movement input language as land movement
jump remains the upward or exit-oriented action
dash and traversal art may gain water-specific behavior if supported
stance may modify swim feel, but should not fundamentally remap control logic
Yin Swimming Behavior

Typically favors:

smoother control
quieter movement
better precision in submerged navigation
safer repositioning
Yang Swimming Behavior

Typically favors:

stronger propulsion
more forceful entry/exit movement
louder disturbance profile
riskier but faster underwater traversal
Design Rationale

Swimming should feel like an extension of mastery, not a control interruption. The player should immediately understand how to move in water using the same movement language learned on land.

#### 10.3.4 Movement Profile States

Movement profile states are independent of Yin/Yang stance.

Walk

Default grounded movement state.

Properties:

medium speed
medium sound
medium detection
full control availability
Run

Fast grounded movement state.

Properties:

highest grounded speed
loudest movement profile
highest detection risk
strongest momentum carry
Crouch Idle

Low-profile stationary state.

Properties:

minimal sound
minimal visual profile
reduced detection
restricted movement posture
Crouch Walk

Slow stealth movement state.

Properties:

lowest speed
lowest sound
lowest detection profile
strongest stealth utility
Design Rationale

Movement profile expresses the player’s physical presence in the world. It determines how visible, audible, and committed the player is, and is therefore central to stealth, traversal tension, and encounter pacing.

#### 10.3.5 Stance System

Yin and Yang are active stance states, not passive buffs.

Yin Stance

Represents control, precision, subtlety, and setup.

Typical effects:

tighter movement handling
safer positioning tools
quieter combat and traversal expression
defensive or evasive utility
Yang Stance

Represents aggression, force, momentum, and direct action.

Typical effects:

stronger offensive pressure
faster burst movement behavior
louder action profile
more committed traversal and combat actions
Design Rationale

Stance switching changes the feel and tactical purpose of actions while preserving a stable control map. This allows deep expressive play without requiring the player to relearn button placement.

#### 10.3.5 Jump, Wall Jump, and Swim Input Rules

Jump remains the universal mobility action across all movement contexts.

Jump Input Behavior

The jump input resolves by context:

if grounded, perform ground jump
if in valid wall contact, perform wall jump
if at swimmable surface boundary, perform water jump / surface exit
otherwise no jump occurs unless an unlocked special movement rule applies
Design Rule

The player should never need separate buttons for:

normal jump
wall jump
swim breach
surface exit jump

All of these are contextual expressions of the same movement input.

Rationale

This preserves muscle memory and makes locomotion scalable without input bloat.

10.3.6 Core Live Actions

The following actions are always considered part of the real-time gameplay layer:

Move
Run
Crouch
Jump
Melee Attack
Thrown Tool
Dash
Guard / Parry
Stance Switch
Traversal Art
Echo Art
Interact
Quick Map
Pause

These actions define the playable moment-to-moment language of the game.

#### 10.3.7 Combat and Utility Actions
Melee Attack

Primary close-range combat action.

Behavior:

stance-dependent feel
directional variants supported
may support charge extensions through hold behavior if required by progression
Thrown Tool

Dedicated off-hand action family.

Behavior:

Yin: Smoke Bomb
Yang: Shuriken

Shared properties:

same input
same cooldown/resource lane
stance determines effect

Purpose:

Yin tool supports disengage, stealth reset, and escape
Yang tool supports ranged pressure, interruption, and environmental triggering
Guard / Parry

Dedicated defensive action.

Behavior:

tap for parry timing window
optional hold behavior for advanced defensive upgrades
Design Rationale

Combat remains intentionally light. The control scheme supports tactical depth through stance variation and directional nuance rather than through a large number of separate combat buttons.

#### 10.3.8 Traversal Art Family

Traversal Art is a dedicated advanced movement input family built around hold-to-aim behavior.

Core behaviors may include:

blink
phase movement
grapple pull
anchor warp
redirect movement
traversal chaining during Flow

Traversal Art uses:

one dedicated input
directional aiming
context-based resolution
stance-dependent tuning
Yin Traversal Behavior

Typically favors:

precision
safer positioning
cleaner short-range execution
controlled movement correction
Yang Traversal Behavior

Typically favors:

burst movement
stronger launch behavior
break-through positioning
more aggressive entry and exit states
Design Rationale

Traversal Art is intended to be one of the game’s core mastery systems. It must therefore have a dedicated live input and enough design space to grow through upgrades without expanding button count.

#### 10.3.9 Echo Art Family

Echo Art is a dedicated utility/mastery system supporting solo-cooperative puzzle design and advanced play.

Core behaviors may include:

place Echo
replay movement or timing
hold environmental triggers
lure enemy attention
mirror specific interactions
support asymmetric puzzle solving

Echo Art uses:

one dedicated input
tap/hold variants
context-based resolution
upgrade-driven expansion
Design Rationale

Echo is a signature system and should not be hidden inside menus or reduced to a passive effect. It must be directly usable in live play while remaining contained within a single expandable input family.

#### 10.3.10 Flow and Lantern Control Policy
Flow

Flow is not a manually activated ability.

It is triggered through successful stance balancing and maintained through continued skillful play.

Effects may include:

smoother chaining
stronger traversal reliability
improved recovery
cleaner aerial control
reduced action friction
Lantern

Lantern acts as a mastery amplifier, not a separate stance or major control burden.

Lantern affects:

Flow duration
Flow strength
Echo stability
traversal precision
teleport consistency
Design Rationale

Neither Flow nor Lantern should consume core live input space. Their purpose is to reinforce mastery, not complicate control readability.

#### 10.3.11 Menu and Meta-System Policy

The following systems are primarily handled outside the live action layer:

inventory
crafting
equipment/loadout management
codex/journal
ability management
detailed map review
settings
Quick Map

Quick map access remains available in live play.

Recommended behavior:

tap = quick local map overlay
hold = full map screen
Crafting and Inventory

These systems are accessed through:

pause menu
hub interfaces
shrines/checkpoints
safe-state screens
Design Rationale

Menu-driven meta-systems preserve live input space for movement, stance, traversal, and Echo mastery.

#### 10.3.12 Default Controller Layout
Input	Action
Left Stick	Move / Aim / Walk / Run / Crouch / Swim Direction
A / Cross	Jump / Wall Jump / Water Exit Jump
X / Square	Melee Attack
B / Circle	Dash
Y / Triangle	Thrown Tool / Context Interact
LB / L1	Switch Yin/Yang
RB / R1	Guard / Parry
LT / L2	Traversal Art
RT / R2	Echo Art
Back / Select (tap)	Quick Map
Back / Select (hold)	Full Map
Start	Pause / Menu
Controller Notes
partial stick tilt = walk
full stick tilt = run
down input = crouch
down + movement = crouch walk
in water, stick controls swim vector
jump input is context-sensitive across ground, wall, and water
10.3.13 Default Keyboard Layout
Precision Keyboard Preset
Input	Action
Arrow Keys	Move / Aim / Crouch / Swim Direction
Left Shift	Run Modifier
Z	Jump / Wall Jump / Water Exit Jump
X	Melee Attack
C	Dash
A	Switch Yin/Yang
S	Guard / Parry
D	Traversal Art
F	Thrown Tool
R	Echo Art
E	Interact
Tab (tap)	Quick Map
Tab (hold)	Full Map
Esc	Pause / Menu
Keyboard Notes
movement defaults to walk
Shift + movement = run
Down = crouch
Down + Left/Right = crouch walk
in water, arrow keys determine swim direction
jump input resolves contextually for ground, wall, and water movement
#### 10.3.14 Upgrade and Expansion Rules

To preserve clarity, upgrades must follow these rules:

Rule A: No new permanent action buttons

Upgrades may deepen:

Traversal Art
Echo Art
melee variants
tool behavior
Flow interaction

They may not add unrelated new live buttons.

Rule B: Existing action families must expand through context

A new upgrade should:

add a new target type
add a new follow-up option
improve an existing branch
modify stance interaction
expand Flow synergy
Rule C: Variant selection should be handled outside active play when necessary

If Traversal or Echo develops too many branches, selection should occur through:

loadout menus
shrines
hub stations
upgrade configuration screens

not through rapid in-combat cycling.

#### 10.3.15 Context Priority Rules

To prevent ambiguity, actions with multiple possible outcomes must obey clear priority logic.

Traversal Art Priority
explicit traversal target
valid anchor
valid phase surface
airborne redirect option
fallback traversal behavior
Echo Art Priority
active puzzle/Echo context
re-trigger existing Echo
place new Echo
recall/cancel behavior
Tool / Interact Priority
explicit interact prompt in safe context
otherwise execute thrown tool
Design Rationale

Clear priority rules ensure the player always understands why an action occurred, even when systems overlap.

#### 10.3.16 Accessibility Requirements

The control system must support:

full rebinding
hold/toggle run option
hold/toggle crouch option
configurable aim-hold behavior
input buffering
jump forgiveness / coyote time
readable stance feedback
readable movement profile feedback
readable Flow and Echo state feedback

Accessibility is required to preserve the intended control feel across a wide range of player preferences.

#### 10.3.17 Summary

Shadow Ascent uses a layered control architecture that separates locomotion profile, stance identity, and action families. Locomotion includes grounded, aerial, wall, and swimming movement. Movement profile states control sound, speed, posture, buoyancy handling, and detection. Yin and Yang control tactical expression rather than redefining the control map. Traversal Art and Echo Art serve as the game’s expandable mastery systems. Flow and Lantern amplify play without consuming additional core inputs. Meta-systems such as inventory, crafting, and loadout management are handled through menu layers so that real-time input space remains dedicated to movement, combat, stance switching, traversal, and Echo execution.
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
