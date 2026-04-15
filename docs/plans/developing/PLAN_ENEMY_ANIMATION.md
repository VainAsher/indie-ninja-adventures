---
doc_type: plan
status: developing
owner: core-team
last_updated: 2026-04-15
version_anchor: v0.11.45
---
# PLAN â€” Enemy Animation & AI Overhaul
## Replace Placeholder Shapes with Animated Stateful Enemy Sprites
**Created:** 2026-04-12 | **Last updated:** 2026-04-12 | **Codebase version:** v0.11.12 | **Target release:** v0.12.x

---

## 0. Situation Summary

### What shipped in v0.11.10

Phases 2 and 3 are fully implemented:

- **`AnimationRegistry.loadEnemySheets(FileHandle baseDir)`** â€” reads `assets/sprites/enemies/<type>/`,
  registers `enemy_<type>_<state>` keys for all 8 AI states. Silently skips missing files.
  "goblin" alias registered pointing to swordsman art for backward compat.
- **`EnemyAIState`** â€” expanded with `FLEE` (`"flee"`) and `GUARD` (`"guard"`)
- **`SimEnemy`** â€” `fleeTimer`, `guardTimer`, `FLEE_DURATION = 3.0f`, `GUARD_DURATION = 2.0f`,
  `FLEE_HP_THRESHOLD = 0.25f`. `takeDamage()` sets `fleeTimer` when HP drops below threshold.
- **`GameSimulator.stepEnemyAI()`** â€” rewritten: FLEE moves enemy away from player at 1.2Ã— speed;
  GUARD (skeleton only) holds the shield frame and sets `blockCooldown`; STUNNED transitions to
  FLEE if `fleeTimer > 0`; `blockCooldown` ticked each frame.
- **`stepCombat()`** â€” `if (en.aiState == EnemyAIState.GUARD) continue;` blocks melee on guarding skeleton
- **`EntityRenderer.enemyFps()`** â€” all type+state entries including FLEE/GUARD FPS
- **`EntityRenderer.enemySize()`** â€” swordsman/goblinâ†’48Ã—64, grunt/spearmanâ†’32Ã—56
- **`GameScreen`** â€” wires `anims.loadEnemySheets(enemySheetDir)` on startup

### What exists (as of v0.11.10)

The codebase has a complete server-side enemy simulation (`SimEnemy`, `EnemyAIState`,
`GameSimulator.stepEnemyAI()`) and a client rendering path (`EntityRenderer.renderEnemy()`)
that resolves animation keys in the form `"enemy_<type>_<aiState>"`.

`AnimationRegistry.loadEnemySheets()` is implemented and wired in `GameScreen`. Spritesheets
will load automatically once the stitch script (Phase 1) has been run against the source ZIP.

**Current enemy rendering:** falls back to a 1Ã—1 magenta placeholder until Phase 1 stitch
script populates `assets/sprites/enemies/<type>/`.

**Current enemy AI states:** `IDLE`, `PATROL`, `CHASE`, `ATTACK`, `FLEE`, `GUARD`, `STUNNED`, `DEAD`

**Existing enemy types (server):** swordsman, bat, slime, skeleton, spearman, archer

### What we have in the ZIP

`"enemy placeholder animations. single frame per png.zip"` contains **5 enemy folders** with
individual-frame PNGs already extracted from PSD layers. No spritesheet stitching has been
done yet â€” the frames are named `idle-1.png`, `walk-2.png`, `attack-A3.png`, etc.

| Folder | Enemy type | Actual frame counts (confirmed 2026-04-12) |
|--------|------------|-------------------------------------------|
| `1 Enemy` | swordsman | idle(4), walk(6), attack-A(8)+attack-B(11), dead(4), hit(3), jump(6) â€” 42 total |
| `2 Enemy` | skeleton | idle(4), walk(6), attack-A(12)+attack-B(7), dead(4), hit(3), jump(5), shield-block(2) â€” 43 total |
| `3 Enemy` | slime | idle(4), walk(4), attack-A(10)+attack-B(11)+attack-C(8), dead(5), hit(3) â€” 45 total, no jump |
| `4 Enemy` | spearman | idle(2), walk(6), attack-A(6)+attack-B(10), dead(4), hit(3), jump(5) â€” 36 total |
| `5 Enemy` | archer | idle(2), run(12), attack-A(6)+attack-B(6), dead(4), hit(4), jump(6) â€” 40 total |

### Enemy-to-art mapping

| Game type  | Art folder | Weapon         |
|------------|------------|----------------|
| swordsman  | `1 Enemy`  | **greatsword** |
| skeleton   | `2 Enemy`  | melee + shield |
| slime      | `3 Enemy`  | melee          |
| spearman   | `4 Enemy`  | **spear**      |
| archer     | `5 Enemy`  | **bow**        |
| bat        | *(none)*   | contact        |

- **swordsman** â€” Greatsword skeleton; attack-A is the raise/windup (6 frames), attack-B is the overhead smash down (10 frames); slow but very high damage; replaces `swordsman` type name
- **skeleton** â€” Shield skeleton; shield-block frames are unique; blocks attacks and counter-attacks
- **slime** â€” Three attack variants (A/B/C) suit slow multi-hit style; no jump (ground-only)
- **spearman** â€” Longer reach melee; attack-A/B are thrust variants; jump confirms airborne spear
- **archer** â€” 12-frame run for kiting; attack frames are draw+release; fires `SimArrow` projectiles
- **bat** â€” Flying art not in ZIP; keep magenta placeholder; dedicated flying art is backlog

> **Design note:** The ZIP does not contain flying-enemy frames. `bat` retains the placeholder
> until dedicated art arrives. `spearman` and `archer` are introduced as new types â€” both
> require one-line additions to `buildEnemy()` in `GameSimulator`.
>
> **Archer AI is fundamentally different from all other enemies** â€” it kites, not chases.
> It fires `SimArrow` projectiles (built on the existing `SimShuriken` infrastructure).
> The run animation is used for lateral repositioning, not pursuit.

---

## 1. Architecture overview

```
ZIP (individual PNGs)
        â”‚
        â–¼
tools/stitch_enemy_frames.py          â† Phase 1
        â”‚  produces
        â–¼
assets/sprites/enemies/
  swordsman/   idle.png  walk.png  attack_a.png  attack_b.png  hit.png  dead.png  jump.png
  skeleton/ idle.png  walk.png  attack_a.png  attack_b.png  hit.png  dead.png  jump.png  shield_block.png
  slime/    idle.png  walk.png  attack_a.png  attack_b.png  attack_c.png  hit.png  dead.png
  grunt/    idle.png  walk.png  attack_a.png  attack_b.png  hit.png  dead.png  jump.png
  wolf/     idle.png  run.png   attack_a.png  attack_b.png  hit.png  dead.png  jump.png
        â”‚
        â–¼
AnimationRegistry.loadEnemySheets()   â† Phase 2
        â”‚  registers keys
        â–¼
  enemy_swordsman_idle, enemy_swordsman_patrol, enemy_swordsman_chase,
  enemy_swordsman_attack, enemy_swordsman_attack_b, enemy_swordsman_stunned, enemy_swordsman_dead
  (same pattern for skeleton, slime, grunt, wolf)
  enemy_skeleton_guard  (shield-block â€” unique to skeleton)
        â”‚
        â–¼
EntityRenderer.renderEnemy()          â† Phase 5 (routing only)
  already uses "enemy_<type>_<aiState>" â€” just needs FLEE/GUARD routing added

GameSimulator.stepEnemyAI()           â† Phase 3
  adds: FLEE state, GUARD state (skeleton), ledge detection
```

---

## 2. What to keep unchanged

| System | Why it stays |
|--------|-------------|
| `EnemyState` wire format | Add only optional fields; existing `aiState` string covers all new states |
| `renderEnemy()` dispatch | Already resolves `"enemy_<type>_<aiState>"` â€” just needs fallback routes for new states |
| `AnimationRegistry.sliceAndRegister()` | Exact same mechanism as player sheets |
| `SimEnemy` physics fields | Patrol bounds, timers, `facingRight` â€” all reused |
| `enemyFps()` in `EntityRenderer` | Extend, not replace; add new type+state combinations |
| `enemySize()` in `EntityRenderer` | Update display dims per artwork; keep physics dims separate |

---

## Phase 1 â€” Asset Pipeline: Stitch Individual Frames into Spritesheets

**Goal:** Turn the individual PNGs in the ZIP into horizontal spritesheets that
`AnimationRegistry.sliceAndRegister()` can consume.

### 1.1 Extract the ZIP

```
Destination: assets/sprites/enemies/_source/
Structure after extraction:
  assets/sprites/enemies/_source/1 Enemy/PNG/*.png
  assets/sprites/enemies/_source/2 Enemy/PNG/*.png
  ... etc
```

### 1.2 Write `tools/stitch_enemy_frames.py`

Mirrors the role of `tools/extract_animations.py` but for enemies.

```python
# tools/stitch_enemy_frames.py
"""
Stitch per-enemy-type individual PNG frames into horizontal spritesheets.

Input:  assets/sprites/enemies/_source/<N> Enemy/PNG/
Output: assets/sprites/enemies/<type>/idle.png, walk.png, run.png, etc.

Usage:
    python tools/stitch_enemy_frames.py
"""
```

**Animation group rules (same for every enemy type unless noted):**

| Output filename        | Source frames              | Notes |
|------------------------|----------------------------|-------|
| `idle.png`             | `idle-1.png` â€¦ `idle-N.png` | All idle frames in order |
| `walk.png`             | `walk-1.png` â€¦ `walk-N.png` | Patrol/slow movement |
| `run.png`              | `run-1.png` â€¦ `run-N.png`   | Wolf only; others copy walk |
| `attack_a.png`         | `attack-A1.png` â€¦ `attack-AN.png` | Primary attack |
| `attack_b.png`         | `attack-B1.png` â€¦ `attack-BN.png` | Combo / alt attack |
| `attack_c.png`         | `attack-C1.png` â€¦ `attack-CN.png` | Slime only |
| `hit.png`              | `hit-1.png` â€¦ `hit-N.png`   | Stun reaction |
| `dead.png`             | `dead-1.png` â€¦ `dead-N.png` | Death animation (play once) |
| `jump.png`             | `jump-1.png` â€¦ `jump-N.png` | Airborne; skip for slime/bat |
| `shield_block.png`     | `shield-block-1.png` â€¦      | Skeleton only |

**Frame ordering:** frames are sorted alphanumerically by the number suffix
(A1 < A2 < â€¦ < A12 using zero-padded sort key to avoid A10 < A2).

**Output format:** all frames stitched left-to-right into a single horizontal PNG;
frame dimensions preserved from source (script reads actual image width/height).

**Output dirs:**

```
assets/sprites/enemies/swordsman/
assets/sprites/enemies/skeleton/
assets/sprites/enemies/slime/
assets/sprites/enemies/grunt/
assets/sprites/enemies/wolf/
```

### 1.3 Frame dimension audit

The ZIP frames appear to be ~64-80 px per side (same visual scale as the player
template sheets). The stitcher script should print actual dimensions so we can
confirm before registering frame counts in the registry.

**Deliverables:**
- `tools/stitch_enemy_frames.py` committed and runnable with `python tools/stitch_enemy_frames.py`
- All 5 enemy type directories populated under `assets/sprites/enemies/`
- `README` note in `assets/sprites/enemies/` documenting source mapping

---

## Phase 2 â€” AnimationRegistry: `loadEnemySheets()`

**Goal:** Register all enemy animation keys so `EntityRenderer.renderEnemy()` resolves
real frames instead of the magenta fallback.

**File:** `java/client/src/main/java/com/indieniinja/client/rendering/AnimationRegistry.java`

### 2.1 Add `loadEnemySheets(FileHandle baseDir)`

```java
/**
 * Load all enemy animations from per-type subdirectories under baseDir.
 * Expected structure: baseDir/<type>/idle.png, walk.png, attack_a.png, etc.
 * Keys registered: "enemy_<type>_<state>" â€” consumed by EntityRenderer.renderEnemy().
 *
 * Missing files are silently skipped; the magenta fallback remains for that key.
 */
public void loadEnemySheets(FileHandle baseDir) {
    loadEnemyType(baseDir, "swordsman",   GOBLIN_FRAME_COUNTS);
    loadEnemyType(baseDir, "skeleton", SKELETON_FRAME_COUNTS);
    loadEnemyType(baseDir, "slime",    SLIME_FRAME_COUNTS);
    loadEnemyType(baseDir, "grunt",    GRUNT_FRAME_COUNTS);
    loadEnemyType(baseDir, "wolf",     WOLF_FRAME_COUNTS);
}
```

**Frame count tables** (fill exact values after running stitch script in Phase 1):

```java
// Goblin (Enemy 1)
private static final Map<String,Integer> GOBLIN_FRAME_COUNTS = Map.of(
    "idle",     2,
    "walk",     6,
    "attack_a", 6,
    "attack_b", 10,
    "hit",      3,
    "dead",     4,
    "jump",     5
);

// Skeleton (Enemy 2) â€” includes shield_block
private static final Map<String,Integer> SKELETON_FRAME_COUNTS = Map.of(
    "idle",         4,
    "walk",         6,
    "attack_a",     12,
    "attack_b",     7,
    "hit",          3,
    "dead",         4,
    "jump",         5,
    "shield_block", 2
);

// Slime (Enemy 3) â€” no jump
private static final Map<String,Integer> SLIME_FRAME_COUNTS = Map.of(
    "idle",     4,
    "walk",     4,
    "attack_a", 10,
    "attack_b", 11,
    "attack_c", 8,
    "hit",      3,
    "dead",     5
);

// Grunt (Enemy 4) â€” same structure as swordsman
private static final Map<String,Integer> GRUNT_FRAME_COUNTS = Map.of(
    "idle",     4,
    "walk",     6,
    "attack_a", 6,
    "attack_b", 10,
    "hit",      3,
    "dead",     4,
    "jump",     5
);

// Wolf (Enemy 5) â€” run not walk
private static final Map<String,Integer> WOLF_FRAME_COUNTS = Map.of(
    "idle",     2,
    "run",      12,
    "attack_a", 8,
    "attack_b", 11,
    "hit",      4,
    "dead",     4,
    "jump",     6
);
```

### 2.2 AI-state â†’ sheet-name mapping

`loadEnemyType()` registers keys for each AI state using the right sheet:

```java
private void loadEnemyType(FileHandle baseDir, String type, Map<String,Integer> counts) {
    FileHandle dir = baseDir.child(type);

    // idle â†’ "enemy_<type>_idle"
    loadIfPresent(dir, "enemy_"+type+"_idle",      "idle.png",     counts.get("idle"));

    // patrol (slow walk) â†’ walk sheet
    loadIfPresent(dir, "enemy_"+type+"_patrol",    "walk.png",     counts.get("walk"));

    // chase (fast) â†’ run sheet if present, else walk
    String chaseSheet = dir.child("run.png").exists() ? "run.png" : "walk.png";
    int    chaseFrames = counts.containsKey("run") ? counts.get("run") : counts.get("walk");
    loadIfPresent(dir, "enemy_"+type+"_chase",     chaseSheet,     chaseFrames);

    // flee (moving away) â€” same sheet as chase; direction handled by facingRight flip
    loadIfPresent(dir, "enemy_"+type+"_flee",      chaseSheet,     chaseFrames);

    // attack â†’ primary attack sheet
    loadIfPresent(dir, "enemy_"+type+"_attack",    "attack_a.png", counts.get("attack_a"));
    loadIfPresent(dir, "enemy_"+type+"_attack_b",  "attack_b.png", counts.getOrDefault("attack_b", 0));
    loadIfPresent(dir, "enemy_"+type+"_attack_c",  "attack_c.png", counts.getOrDefault("attack_c", 0));

    // guard (skeleton shield block)
    loadIfPresent(dir, "enemy_"+type+"_guard",     "shield_block.png", counts.getOrDefault("shield_block", 0));

    // stunned â†’ hit reaction sheet
    loadIfPresent(dir, "enemy_"+type+"_stunned",   "hit.png",      counts.get("hit"));

    // dead â†’ death sheet (play-once; renderer holds last frame after completion)
    loadIfPresent(dir, "enemy_"+type+"_dead",      "dead.png",     counts.get("dead"));

    // jump (airborne) â€” used when enemy is mid-air
    if (counts.containsKey("jump"))
        loadIfPresent(dir, "enemy_"+type+"_jump",  "jump.png",     counts.get("jump"));
}
```

### 2.3 Wire up in `GameScreen`

After the existing `anims.loadUnarmedSheets()` / `anims.loadSwordSheets()` calls:

```java
// GameScreen.java â€” inside createAnimationRegistry() or equivalent init block
FileHandle enemyBase = Gdx.files.internal("sprites/enemies");
anims.loadEnemySheets(enemyBase);
```

### 2.4 Update `enemyFps()` in `EntityRenderer`

Add new type+state entries matching actual frame rates for each artwork:

```java
// EntityRenderer.java â€” enemyFps()
case "swordsman.idle"              -> 6f;
case "swordsman.patrol"            -> 7f;
case "swordsman.chase"             -> 8f;   // slow heavy walk
case "swordsman.attack"            -> 6f;   // attack_a = slow raise (windup), attack_b = smash
case "swordsman.stunned"           -> 8f;
case "swordsman.dead"              -> 8f;

case "skeleton.idle"            -> 6f;
case "skeleton.patrol"          -> 8f;
case "skeleton.chase"           -> 10f;
case "skeleton.attack"          -> 10f;
case "skeleton.guard"           -> 6f;
case "skeleton.stunned"         -> 10f;
case "skeleton.dead"            -> 10f;

case "slime.idle"               -> 6f;
case "slime.patrol"             -> 6f;
case "slime.chase"              -> 8f;
case "slime.attack"             -> 8f;
case "slime.stunned"            -> 8f;
case "slime.dead"               -> 6f;

case "grunt.idle"               -> 6f;
case "grunt.patrol"             -> 8f;
case "grunt.chase", "grunt.flee"-> 10f;
case "grunt.attack"             -> 12f;
case "grunt.stunned"            -> 10f;
case "grunt.dead"               -> 10f;

case "wolf.idle"                -> 6f;
case "wolf.patrol"              -> 12f;
case "wolf.chase", "wolf.flee"  -> 16f;
case "wolf.attack"              -> 14f;
case "wolf.stunned"             -> 10f;
case "wolf.dead"                -> 10f;
```

**Files to modify:**
- `java/client/src/main/java/com/indieniinja/client/rendering/AnimationRegistry.java` â€” add `loadEnemySheets()`
- `java/client/src/main/java/com/indieniinja/client/GameScreen.java` â€” wire up call
- `java/client/src/main/java/com/indieniinja/client/rendering/EntityRenderer.java` â€” extend `enemyFps()`, update `enemySize()`

---

## Phase 3 â€” AI State Expansion: FLEE, GUARD, Ledge Detection

**Goal:** Give each enemy behaviorally distinct movement and reaction logic.
Ship working FSMs first; tune timing in follow-up commits (same lesson as boss tuning).

### 3.1 Add new states to `EnemyAIState`

**File:** `java/core/src/main/java/com/indieniinja/sim/EnemyAIState.java`

```java
public enum EnemyAIState {
    IDLE     ("idle"),
    PATROL   ("patrol"),
    CHASE    ("chase"),
    ATTACK   ("attack"),
    GUARD    ("guard"),    // NEW â€” skeleton only: raise shield, absorb hit
    FLEE     ("flee"),     // NEW â€” cowardly enemies below HP threshold
    STUNNED  ("stunned"),
    DEAD     ("dead");

    public final String wire;
    EnemyAIState(String wire) { this.wire = wire; }
}
```

### 3.2 Add behavioral fields to `SimEnemy`

**File:** `java/core/src/main/java/com/indieniinja/sim/SimEnemy.java`

```java
// â”€â”€ Behavioral config (set by buildEnemy) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
public float  fleeHpThreshold    = 0f;    // 0 = never flees; 0.25 = flee at 25% HP
public boolean canBlock           = false; // true for skeleton: may enter GUARD
public boolean canJump            = true;  // false for slime: no jump AI
public float   blockCooldown      = 0f;   // seconds remaining until next block allowed
public float   attackWindupDuration = ATTACK_WINDUP_TIME; // per-type override; swordsman = 1.2f

// â”€â”€ GUARD sub-state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
public float  guardTimer = 0f;         // how long guard is held
public static final float GUARD_DURATION   = 0.8f;
public static final float GUARD_COOLDOWN   = 3.0f;
public static final float GUARD_CHANCE     = 0.35f;  // probability per attack windup
```

### 3.3 Extend `buildEnemy()` in `GameSimulator`

```java
// GameSimulator.java â€” buildEnemy()
case "swordsman" -> {
    // Heavy armoured skeleton: slow, high-damage overhead greatsword smash
    // Stats: low speed (55 px/s), high damage (4), long attack range (80px for greatsword reach)
    // Long windup (1.2s) telegraphs the smash â€” player can dodge or stagger first
    SimEnemy e = new SimEnemy(hubId+"_swordsman_"+idx, "swordsman",
                    spec.x(), spec.y(), 40, 64,
                    5+hpBonus, 4, 55f*speedMult, 200f, 80f,
                    spec.patrolMinX(), spec.patrolMaxX(), false);
    e.attackWindupDuration = 1.2f;  // slow raise visible for 1.2s before smash lands
    yield e;
}
case "skeleton" -> {
    SimEnemy e = new SimEnemy(...);
    e.canBlock = true;
    yield e;
}
case "slime" -> {
    SimEnemy e = new SimEnemy(...);
    e.canJump  = false;
    yield e;
}
case "wolf" -> {
    SimEnemy e = new SimEnemy(...);
    e.fleeHpThreshold = 0.10f;  // wolves briefly flee before repositioning
    yield e;
}
case "grunt" -> new SimEnemy(...);   // no flee, no block
```

### 3.4 Rewrite `stepEnemyAI()` in `GameSimulator`

**File:** `java/core/src/main/java/com/indieniinja/sim/GameSimulator.java`

Full updated state machine replacing the current `switch` at line ~1111:

```java
private void stepEnemyAI(SimEnemy en, float[] nearest, List<float[]> players) {
    // Flying enemies have their own movement path â€” skip ground AI
    if (en.canFly) { applyFlyingEnemyMovement(en); return; }

    float dist = en.distanceTo(nearest[0], nearest[1]);

    // â”€â”€ Global: flee check (overrides other states when HP is critical) â”€â”€â”€â”€â”€â”€
    if (en.fleeHpThreshold > 0f
            && en.hp > 0
            && (float) en.hp / en.maxHp < en.fleeHpThreshold
            && en.aiState != EnemyAIState.STUNNED
            && en.aiState != EnemyAIState.DEAD) {
        en.aiState = EnemyAIState.FLEE;
    }

    switch (en.aiState) {

        case IDLE -> {
            // Idle: look for player, transition to patrol
            if (dist < en.detectionRadius) en.aiState = EnemyAIState.CHASE;
            else en.aiState = EnemyAIState.PATROL;
        }

        case PATROL -> {
            float speed = en.moveSpeed * en.patrolSpeedMult * DT;
            float nextX = en.physics.x + (en.facingRight ? speed : -speed);

            // Ledge detection: raycast one tile downward at leading edge
            boolean ledgeAhead = !groundExistsAt(nextX + (en.facingRight ? en.physics.width : 0),
                                                  en.physics.y - 2f);
            if (ledgeAhead) en.facingRight = !en.facingRight;
            else            en.physics.x    = nextX;

            // Waypoint bounce
            if (en.physics.x <= en.patrolMinX) {
                en.physics.x   = en.patrolMinX;
                en.facingRight = true;
            } else if (en.physics.x + en.physics.width >= en.patrolMaxX) {
                en.physics.x   = en.patrolMaxX - en.physics.width;
                en.facingRight = false;
            }

            if (dist < en.detectionRadius) en.aiState = EnemyAIState.CHASE;
        }

        case CHASE -> {
            float tx = nearest[0];
            float cx = en.physics.x + en.physics.width * 0.5f;
            float speed = en.moveSpeed * DT;
            if (tx > cx) { en.physics.x += speed; en.facingRight = true; }
            else         { en.physics.x -= speed; en.facingRight = false; }

            if (dist < en.attackRange) {
                // Skeleton: random chance to guard instead of attacking
                if (en.canBlock && en.blockCooldown <= 0f
                        && random.nextFloat() < SimEnemy.GUARD_CHANCE) {
                    en.aiState   = EnemyAIState.GUARD;
                    en.guardTimer = SimEnemy.GUARD_DURATION;
                } else {
                    en.aiState           = EnemyAIState.ATTACK;
                    en.attackWindupTimer = SimEnemy.ATTACK_WINDUP_TIME;
                }
            } else if (dist > en.detectionRadius * 1.5f) {
                en.aiState = EnemyAIState.PATROL;
            }
        }

        case ATTACK -> {
            if (en.attackWindupTimer > 0) {
                en.attackWindupTimer -= DT;
            } else if (en.attackActiveTimer < SimEnemy.ATTACK_ACTIVE_TIME) {
                en.attackActiveTimer += DT;
            } else {
                en.attackActiveTimer   = 0f;
                en.attackRecoveryTimer = SimEnemy.ATTACK_RECOVERY_TIME;
                en.aiState = EnemyAIState.CHASE;
            }
        }

        case GUARD -> {
            // Absorb damage at reduced rate (handled in stepCombat); count down
            en.guardTimer    -= DT;
            en.blockCooldown  = SimEnemy.GUARD_COOLDOWN;
            if (en.guardTimer <= 0) en.aiState = EnemyAIState.CHASE;
        }

        case FLEE -> {
            // Move directly away from the nearest player
            float tx = nearest[0];
            float cx = en.physics.x + en.physics.width * 0.5f;
            float speed = en.moveSpeed * DT;
            if (tx > cx) { en.physics.x -= speed; en.facingRight = false; }
            else         { en.physics.x += speed; en.facingRight = true; }

            // Stop fleeing if far enough away
            if (dist > en.detectionRadius * 2f) en.aiState = EnemyAIState.PATROL;
        }

        case STUNNED -> {
            en.stunTimer -= DT;
            if (en.stunTimer <= 0) {
                en.stunTimer = 0;
                en.aiState   = EnemyAIState.PATROL;
            }
        }

        case DEAD -> { /* nothing */ }
    }

    // Tick block cooldown
    if (en.blockCooldown > 0f) en.blockCooldown -= DT;
}
```

### 3.5 Add `groundExistsAt()` to `GameSimulator`

```java
/**
 * Returns true if there is solid ground directly below the given point.
 * Uses the existing SpatialHash / tile grid query one tile below.
 */
private boolean groundExistsAt(float x, float y) {
    // Query the tile map one tile (16 px) below the foot position.
    // Use the same tile-index lookup as PhysicsSystem.
    int tileX = (int)(x / TILE_SIZE);
    int tileY = (int)((y - TILE_SIZE) / TILE_SIZE);
    TileType t = currentRoom != null ? currentRoom.getTile(tileX, tileY) : TileType.AIR;
    return t == TileType.SOLID || t == TileType.PLATFORM;
}
```

### 3.6 Reduced damage during GUARD

**File:** `java/core/src/main/java/com/indieniinja/sim/GameSimulator.java` â€” `stepCombat()`

```java
// In player-melee â†’ enemy damage section:
int finalDmg = dmg;
if (en.aiState == EnemyAIState.GUARD) finalDmg = Math.max(1, dmg / 3);  // block absorbs 66%
en.takeDamage(finalDmg);
```

**Files to modify (Phase 3):**
- `java/core/src/main/java/com/indieniinja/sim/EnemyAIState.java` â€” add FLEE, GUARD
- `java/core/src/main/java/com/indieniinja/sim/SimEnemy.java` â€” add behavioral fields
- `java/core/src/main/java/com/indieniinja/sim/GameSimulator.java` â€” rewrite `stepEnemyAI()`, add `groundExistsAt()`, update `buildEnemy()`, update combat

---

## Phase 4 â€” EnemyState Wire: `grunt` type & new state propagation

**Goal:** Ensure new types and states round-trip correctly over the network wire.

### 4.1 Add `grunt` to `EntityPlanner`

**File:** `java/core/src/main/java/com/indieniinja/world/postprocess/EntityPlanner.java`

```java
// Replace one "bat" spawn slot in dungeon rooms with "grunt"
// Grunts spawn in COMBAT rooms as mid-tier ground enemies
```

### 4.2 EnemyState serialization â€” no changes needed

`EnemyState.aiState` is already a plain String. `"flee"` and `"guard"` serialize
automatically through the existing `EnemyAIState.wire` field. No `SCHEMA_VERSION` bump
required (EnemyState is not part of `PlayerState` or `WorldSnapshot`'s versioned fields).

### 4.3 Add `grunt` to `buildEnemy()` switch and XP table

```java
// GameSimulator.buildEnemy()
case "grunt" -> new SimEnemy(hubId+"_grunt_"+idx, "grunt",
                   spec.x(), spec.y(), 36, 52,
                   4+hpBonus, 2, 65f*speedMult, 190f, 36f,
                   spec.patrolMinX(), spec.patrolMaxX(), false);

// GameSimulator.enemyXp()
case "grunt" -> 11;
```

**Files to modify (Phase 4):**
- `java/core/src/main/java/com/indieniinja/sim/GameSimulator.java` â€” `buildEnemy()`, `enemyXp()`
- `java/core/src/main/java/com/indieniinja/world/postprocess/EntityPlanner.java` â€” grunt spawn slots

---

## Phase 5 â€” EntityRenderer: Routing, Death Hold, Size Tuning

**Goal:** Correct rendering for all 8 AI states across all enemy types.

### 5.1 Update `renderEnemy()` â€” state routing

**File:** `java/client/src/main/java/com/indieniinja/client/rendering/EntityRenderer.java`

```java
private void renderEnemy(SpriteBatch batch, EnemyState e, float dt) {
    // Skip dead only after death animation completes (see 5.2)
    if ("dead".equals(e.aiState) && isDeathComplete(e.enemyId, e.enemyType)) return;

    String typePrefix = (e.enemyType != null && !e.enemyType.isEmpty())
        ? e.enemyType : derivePrefixFromId(e.enemyId);

    // Map wire state â†’ animation key
    String animState = switch (e.aiState != null ? e.aiState : "idle") {
        case "flee"   -> "flee";     // registered = walk/run sheet
        case "guard"  -> "guard";    // registered = shield_block sheet (skeleton only)
        case "dead"   -> "dead";     // play-once; held at last frame
        default       -> e.aiState;
    };
    String animKey = "enemy_" + typePrefix + "_" + animState;

    float stateTime = tickStateTime(e.enemyId, animKey, dt);
    TextureRegion frame = anims.getFrame(animKey, stateTime,
                            enemyFps(typePrefix, e.aiState != null ? e.aiState : "idle"));

    boolean wantFlipX = !e.facingRight;
    if (wantFlipX != frame.isFlipX()) frame.flip(true, false);

    int[] sz = enemySize(typePrefix);
    batch.draw(frame, e.x, e.y, sz[0], sz[1]);

    if (wantFlipX != frame.isFlipX()) frame.flip(true, false);

    // Hit spark on damage
    if (particles != null) {
        int prev = prevHealth.getOrDefault(e.enemyId, e.hp);
        if (e.hp < prev) particles.emitHitSpark(e.x + sz[0]*0.5f, e.y + sz[1]*0.5f);
        prevHealth.put(e.enemyId, e.hp);
    }
}
```

### 5.2 Death animation: play to completion

Track a per-enemy death state time in the renderer. Entity only disappears from the
snapshot once the server marks it removed, but the renderer should hold the last
frame visible until the death animation finishes, then skip drawing.

```java
// EntityRenderer â€” new field
private final java.util.HashMap<String, Float> deathTimers = new java.util.HashMap<>();

private boolean isDeathComplete(String enemyId, String type) {
    // We know dead anim FPS and frame count â€” check if total duration has elapsed
    float fps    = enemyFps(type, "dead");
    int   frames = enemyDeadFrameCount(type);   // lookup from a small static map
    float dur    = frames / fps;
    float elapsed = deathTimers.getOrDefault(enemyId, 0f);
    return elapsed >= dur;
}
```

The `tickStateTime()` call on the death key already accumulates time in `stateTimes`;
`deathTimers` just mirrors it for the `isDeathComplete` check.

### 5.3 Update `enemySize()` for display dimensions

After running the stitch script (Phase 1) and confirming actual artwork pixel sizes,
update the display dimensions. Physics dimensions stay unchanged (hitbox is separate
from sprite visual bounds).

```java
// EntityRenderer.enemySize() â€” update display dims to match actual art
// (values TBD from Phase 1 frame audit; these are initial guesses)
case "swordsman"   -> new int[]{48, 64};   // art taller than physics box
case "skeleton" -> new int[]{48, 72};
case "slime"    -> new int[]{48, 40};   // art wider/shorter
case "grunt"    -> new int[]{52, 68};
case "wolf"     -> new int[]{64, 48};
case "bat"      -> new int[]{28, 28};   // unchanged (placeholder)
```

**Files to modify (Phase 5):**
- `java/client/src/main/java/com/indieniinja/client/rendering/EntityRenderer.java`

---

## Phase 6 â€” Integration Verification

**Goal:** Every enemy type is visually correct in every AI state before calling this done.

### 6.1 Verification checklist (run from `python launcher/launcher.py`)

For each enemy type (swordsman, skeleton, slime, grunt, wolf):

- [ ] **PATROL** â€” walks along patrol range; reverses at ledge and waypoint
- [ ] **CHASE** â€” switches to fast animation when pursuing player; correct facing
- [ ] **ATTACK** â€” telegraphed windup visible in animation; hit spark on player
- [ ] **FLEE** â€” triggers at HP threshold; moves away; animation plays (not T-pose)
- [ ] **STUNNED** â€” hit reaction animation plays; returns to PATROL after duration
- [ ] **DEAD** â€” death animation plays to completion; entity disappears on final frame
- [ ] **GUARD** (skeleton only) â€” shield-block frame holds during guard window; reduced damage
- [ ] **Flip** â€” enemy correctly faces the direction it moves in all states
- [ ] **Size** â€” sprite aligns with physics hitbox (use debug overlay)

### 6.2 Per-type behavioral tests

| Type | Key test |
|------|---------|
| swordsman | Never flees; slow heavy walk; long attack windup (overhead raise visible before smash); high damage |
| skeleton | Blocks ~35% of the time on approach; blocked hit does 1/3 damage |
| slime | Never jumps (stays on ground level); three attack variants rotate |
| grunt | No flee, no block; high damage trading; straightforward aggression |
| wolf | Chase animation runs at 16 FPS (12 run frames Ã— speed); retreat/reposition loop |
| bat | Retains sinusoidal hover; magenta placeholder acceptable until dedicated art |

### 6.3 Regression checks

- Existing player animation still loads and plays (no AnimationRegistry breakage)
- Multiplayer: EnemyState round-trips with new states (`flee`, `guard`) â€” verify via server log
- Solo mode: `GameSimulator` enemy AI ticks at correct 60 Hz in-process

---

## 5. File Manifest

### New files to create
```
tools/stitch_enemy_frames.py
assets/sprites/enemies/swordsman/idle.png, walk.png, attack_a.png, attack_b.png, hit.png, dead.png, jump.png
assets/sprites/enemies/skeleton/idle.png, walk.png, attack_a.png, attack_b.png, hit.png, dead.png, jump.png, shield_block.png
assets/sprites/enemies/slime/idle.png, walk.png, attack_a.png, attack_b.png, attack_c.png, hit.png, dead.png
assets/sprites/enemies/grunt/idle.png, walk.png, attack_a.png, attack_b.png, hit.png, dead.png, jump.png
assets/sprites/enemies/wolf/idle.png, run.png, attack_a.png, attack_b.png, hit.png, dead.png, jump.png
```

### Files to modify
```
java/core/src/main/java/com/indieniinja/sim/EnemyAIState.java
    â†’ add FLEE, GUARD

java/core/src/main/java/com/indieniinja/sim/SimEnemy.java
    â†’ add fleeHpThreshold, canBlock, canJump, blockCooldown, guardTimer

java/core/src/main/java/com/indieniinja/sim/GameSimulator.java
    â†’ rewrite stepEnemyAI(), add groundExistsAt(), update buildEnemy(), update combat

java/client/src/main/java/com/indieniinja/client/rendering/AnimationRegistry.java
    â†’ add loadEnemySheets(), loadEnemyType(), loadIfPresent()

java/client/src/main/java/com/indieniinja/client/GameScreen.java
    â†’ wire anims.loadEnemySheets(...)

java/client/src/main/java/com/indieniinja/client/rendering/EntityRenderer.java
    â†’ extend enemyFps(), update enemySize(), update renderEnemy(), add death hold

java/core/src/main/java/com/indieniinja/world/postprocess/EntityPlanner.java
    â†’ add grunt spawn slots
```

---

## 6. Milestone Checkboxes

### Phase 1 â€” Asset Pipeline
- [x] Write `tools/stitch_enemy_frames.py` (v0.11.10) â€” ZIP path: Desktop/New folder (4)/enemy placeholder animations...zip
- [x] Run script â†’ all 5 enemy type directories populated (v0.11.11) â€” 37 spritesheets, 128Ã—96 px/frame
- [x] Frame dimensions confirmed: 128Ã—96 px per frame (4:3 landscape); `enemySize()` updated to 64Ã—48 world px
- [x] Commit: `feat(enemy-art): stitch enemy placeholder frames into spritesheets` (v0.11.11)

### Phase 2 â€” AnimationRegistry
- [x] Add `loadEnemySheets()` + `loadEnemySheetType()` to `AnimationRegistry` (v0.11.10)
- [x] Update `enemyFps()` with all type+state entries incl. FLEE/GUARD (v0.11.10)
- [x] Frame counts corrected from stitch script audit (v0.11.11) â€” swordsman/grunt/wolf counts adjusted
- [x] Update `enemySize()` to 64Ã—48 world px matching 128Ã—96 art 4:3 ratio (v0.11.11)
- [x] Wire in `GameScreen` â€” loads from `assets/sprites/enemies/` if directory exists (v0.11.10)
- [ ] Verify in-game: colored placeholders replaced by real sprites (first launcher run post-v0.11.11)

### Phase 3 â€” AI Expansion
- [x] Add FLEE + GUARD to `EnemyAIState` (v0.11.10)
- [x] Add `fleeTimer`, `guardTimer`, `FLEE_DURATION`, `GUARD_DURATION`, `FLEE_HP_THRESHOLD` to `SimEnemy` (v0.11.10)
- [x] Rewrite `stepEnemyAI()` with FLEE, GUARD, skeleton counter-attack (v0.11.10)
- [x] Update `stepCombat()` â€” skeleton GUARD blocks melee damage (v0.11.10)
- [ ] Ledge detection in patrol (detect floor drop-offs) â€” deferred to Phase 3 follow-up

### Phase 4 â€” Wire & Planner
- [x] Corrected type names: `grunt`â†’`spearman`, `wolf`â†’`archer` across stitch script, registry, renderer, simulator (v0.11.12)
- [x] Add `spearman` type to `buildEnemy()` (36Ã—52 hitbox, 80px reach) and `enemyXp()` (13 XP) (v0.11.12)
- [x] Add `archer` type to `buildEnemy()` (32Ã—48 hitbox, 320px detection, 200px range) and `enemyXp()` (15 XP) (v0.11.12)
- [x] Update `EntityPlanner.enemyPool()` â€” spearman at depth â‰¥3, archer at depth â‰¥6 and heavy rooms (v0.11.12)

### Phase 5 â€” Renderer Polish
- [x] FLEE/GUARD routing in `renderEnemy()` â€” automatic via `e.aiState` key lookup (v0.11.10)
- [x] Death animation hold-until-complete â€” `deathTimers` map + `getFrameClamped()` (v0.11.12)
- [x] `enemySize()` updated to 64Ã—48 world px matching 4:3 art; slime 48Ã—36 (v0.11.11)
- [ ] Tune per-type display dimensions in Phase 6 QA playtest

### Phase 6 â€” Integration QA
- [ ] Run through full per-type checklist in solo mode
- [ ] Regression: player animation still works; solo mode stable
- [ ] Commit: `fix(enemy-art): QA pass â€” timing/size fixes from first playtest (m-ea5)`

---

## 7. Design Decisions

| Question | Decision |
|----------|----------|
| Bat art | Not in ZIP; retain magenta placeholder; dedicated flying spritesheet is a separate backlog item |
| Enemy type names | Confirmed v0.11.12: `4 Enemy`â†’`spearman`, `5 Enemy`â†’`archer`; old `grunt`/`wolf` labels were incorrect |
| Attack variants (B/C) | Register as separate keys (`attack_b`, `attack_c`); server picks variant by random sub-state â€” not wired in Phase 3, backlog |
| FLEE direction | Handled purely by `facingRight` flip in renderer â€” no new wire field needed |
| GUARD wire field | Uses existing `aiState` string `"guard"` â€” no protocol change |
| Death anim hold | Client-only; server already removes entity; renderer tracks elapsed time |
| Ledge detection | Simple downward tile query â€” not a raycast; avoids physics budget cost |
| Commit prefix | `feat(enemy-art):` and `feat(enemy-ai):` with milestone suffixes `(m-ea1)` â€¦ `(m-ea5)` |

---

*Living document. Start with Phase 1 (asset pipeline) â€” no code changes until spritesheets exist.
Update checkboxes as work progresses.*

