package com.indieniinja.sim;

import com.indieniinja.core.EntityManager;
import com.indieniinja.core.EventBus;
import com.indieniinja.core.GameClock;
import com.indieniinja.network.EnemyState;
import com.indieniinja.network.InputCommand;
import com.indieniinja.network.PickupState;
import com.indieniinja.network.PlatformState;
import com.indieniinja.network.PlayerState;
import com.indieniinja.network.WorldSnapshot;
import com.indieniinja.physics.CollisionSystem;
import com.indieniinja.physics.PhysicsConstants;
import com.indieniinja.physics.PhysicsState;
import com.indieniinja.physics.PhysicsSystem;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Java authoritative game simulator — pure simulation, no rendering.
 *
 * Java equivalent of Python game/game_simulator.py GameSimulator.
 * The server's ZoneSimulationLoop holds one instance per zone and calls
 * step(inputs, dt) once per 60 Hz tick, then getSnapshot(frame) for broadcast.
 *
 * Step pipeline (matches Python order):
 *   1. Apply InputCommand to each SimPlayer (update physics state from client input)
 *   2. Clock.stepOne() → EventBus.emit(TickEvent) → PhysicsSystem + CollisionSystem fire
 *   3. Platform updates (FallingPlatform state machines)
 *   4. Enemy AI update
 *   5. Server-side combat (enemy → player damage)
 *   6. Pickup lifetime tick + authoritative collection
 *
 * Phase B scope:
 *   - Players: client-authoritative positions from INPUT messages
 *     (no server-side jump/dash mechanics yet — that is Phase C)
 *   - Enemies: server-authoritative patrol/chase/attack AI + physics
 *   - Pickups: server-authoritative collection
 *   - Platforms: server-authoritative falling platform state machine
 */
public final class GameSimulator {

    // ── Constants ─────────────────────────────────────────────────────────────
    private static final float DT           = PhysicsConstants.FIXED_DT;
    private static final float PIXELS_PER_S = 1f / DT;  // 60

    // ── Core systems ──────────────────────────────────────────────────────────
    private final EventBus      bus;
    private final GameClock     clock;
    private final EntityManager entityManager;
    private final PhysicsSystem physicsSystem;
    private final CollisionSystem collisionSystem;

    // ── Sim entities ─────────────────────────────────────────────────────────
    /** Slot → SimPlayer (ordered by slot for deterministic snapshot). */
    private final Map<Integer, SimPlayer> players = new LinkedHashMap<>();
    private final List<SimEnemy>    enemies  = new ArrayList<>();
    private final List<SimPickup>   pickups  = new ArrayList<>();
    private final List<FallingPlatform> fallingPlatforms = new ArrayList<>();

    // ── World ─────────────────────────────────────────────────────────────────
    public final long   seed;
    public final String hubId;
    private final float worldHeightPx;

    // ── Construction ─────────────────────────────────────────────────────────

    public GameSimulator(long seed, String hubId, LevelLayout layout) {
        this.seed          = seed;
        this.hubId         = hubId;
        this.worldHeightPx = layout.worldHeightPx;

        // Build core systems
        bus           = new EventBus();
        entityManager = new EntityManager(bus);
        clock         = new GameClock(bus);

        // Physics reads from entityManager.activeEntities()
        physicsSystem    = new PhysicsSystem(bus, entityManager.activeEntities());
        collisionSystem  = new CollisionSystem(bus, entityManager.activeEntities(), layout.spatialHash);

        // Spawn enemies and register with EntityManager so CollisionSystem handles them
        int enemyIdx = 0;
        for (LevelLayout.EnemySpawn spec : layout.enemySpawns) {
            SimEnemy en = buildEnemy(spec, enemyIdx++);
            enemies.add(en);
            if (!en.canFly) {
                // Ground enemies need physics + collision; flying enemies manage their own movement
                var entity = entityManager.create(com.indieniinja.core.EntityType.ENEMY, en.physics);
                entity.addTag("enemy");
            }
        }

        // Spawn pickups
        int pickupIdx = 0;
        for (LevelLayout.PickupSpawn spec : layout.pickupSpawns) {
            pickups.add(new SimPickup(
                hubId + "_pickup_" + pickupIdx++,
                spec.type(), spec.x(), spec.y()
            ));
        }

        // Register falling platforms
        fallingPlatforms.addAll(layout.fallingPlatforms);
    }

    // ── Public API ────────────────────────────────────────────────────────────

    /**
     * Add a player to the simulation.
     * Called when a player connects or enters this zone.
     */
    public void addPlayer(SimPlayer player) {
        players.put(player.slot, player);
        // Register physics state so PhysicsSystem and CollisionSystem process it
        // In Phase B, player position is client-authoritative — we still register
        // so the physics list is coherent; pos is overwritten from INPUT each tick.
        var entity = entityManager.create(com.indieniinja.core.EntityType.PLAYER, player.physics);
        entity.addTag("player");
    }

    /**
     * Remove a player from the simulation (on disconnect / zone leave).
     */
    public void removePlayer(int slot) {
        players.remove(slot);
        // Entity removal: find by tag "player" matching slot
        // Simple: clear all player entities and re-add remaining (small N)
        rebuildPlayerEntities();
    }

    /**
     * Advance simulation by exactly one fixed tick.
     * Called by ZoneSimulationLoop at 60 Hz.
     *
     * @param inputs Map from slot → InputCommand (slots absent hold last known)
     */
    public void step(Map<Integer, InputCommand> inputs) {
        // Rebuild the active-entity list if dirty (e.g. addPlayer was just called).
        // PhysicsSystem and CollisionSystem hold a reference to this same list object;
        // without this call the list stays stale and physics never runs for new entities.
        entityManager.activeEntities();

        // 1. Store latest inputs and apply movement to player physics
        for (Map.Entry<Integer, InputCommand> e : inputs.entrySet()) {
            SimPlayer p = players.get(e.getKey());
            if (p == null) continue;
            p.latestInput = e.getValue();
            applyPlayerInput(p, e.getValue());
        }

        // Tick invincibility timers
        for (SimPlayer p : players.values()) p.tickInvincibility();

        // 2. Physics tick: gravity + integration + collision (via EventBus)
        clock.stepOne();  // emits TickEvent → PhysicsSystem(60) → CollisionSystem(45)

        // 3. Platform state machines
        stepPlatforms();

        // 4. Enemy AI + physics
        stepEnemies();

        // 5. Server-side player-enemy combat
        stepCombat();

        // 6. Pickups: lifetime + authoritative collection
        stepPickups();
    }

    /**
     * Build a WorldSnapshot from current sim state for broadcast.
     * Java equivalent of Python GameSimulator.get_snapshot(frame).
     */
    public WorldSnapshot getSnapshot(long frame) {
        WorldSnapshot snap = new WorldSnapshot();
        snap.frame = frame;
        snap.seed  = seed;
        snap.hubId = hubId;

        // Players — ordered by slot
        for (Map.Entry<Integer, SimPlayer> e : players.entrySet()) {
            SimPlayer p = e.getValue();
            PlayerState ps = new PlayerState();
            ps.playerId  = p.playerId;
            ps.slot      = p.slot;
            ps.posX      = p.physics.x;
            ps.posY      = p.physics.y;
            ps.velX      = p.physics.vx;
            ps.velY      = p.physics.vy;
            ps.health    = p.health;
            ps.facing           = p.facing == 0 ? 1 : p.facing;
            ps.isDead           = p.isDead;
            ps.animState        = p.animState;
            ps.wallSlideStamina = p.wallSlideStamina;
            ps.isWallSliding    = p.isWallSliding;
            snap.players.add(ps);
        }

        // Enemies
        for (SimEnemy en : enemies) {
            if (en.removed) continue;
            EnemyState es = new EnemyState();
            es.enemyId     = en.enemyId;
            es.x           = en.physics.x;
            es.y           = en.physics.y;
            es.vx          = en.physics.vx;
            es.vy          = en.physics.vy;
            es.hp          = en.hp;
            es.aiState     = en.aiState.wire;
            es.facingRight = en.facingRight;
            snap.enemies.add(es);
        }

        // Pickups
        for (SimPickup pu : pickups) {
            PickupState ps = new PickupState();
            ps.pickupId   = pu.pickupId;
            ps.x          = pu.x;
            ps.y          = pu.y;
            ps.pickupType = pu.pickupType;
            ps.alive      = pu.alive;
            snap.pickups.add(ps);
        }

        // Falling platforms
        for (FallingPlatform fp : fallingPlatforms) {
            PlatformState ps = new PlatformState();
            ps.platformId = fp.platformId;
            ps.state      = fp.wireState();
            ps.posY       = fp.posY;
            ps.timer      = fp.timer;
            ps.vy         = fp.vy;
            snap.platformStates.add(ps);
        }

        return snap;
    }

    // ── Step helpers ──────────────────────────────────────────────────────────

    /**
     * Full mechanics pipeline: dash, double-jump, wall-jump, coyote time, jump buffer.
     * Called once per 60 Hz tick before the physics/collision pass.
     *
     * Convention: p.physics.onGround reflects the result from the PREVIOUS tick's
     * collision pass — correct for coyote time and ground-jump detection.
     */
    private static void applyPlayerInput(SimPlayer sp, InputCommand cmd) {
        PhysicsState p = sp.physics;

        // ── Ground-state change detection ─────────────────────────────────────
        boolean justLanded    = !sp.wasOnGround && p.onGround;
        boolean justLeftGround = sp.wasOnGround  && !p.onGround;

        // ── Landing: reset jump state ─────────────────────────────────────────
        if (justLanded) {
            sp.jumpCount   = 0;
            sp.coyoteTimer = 0f;
            sp.jumpBuffer  = 0f;
        }

        // ── Coyote time: walking off an edge without jumping ──────────────────
        // Only grant coyote window when the player left the ground naturally (not by jumping).
        if (justLeftGround && sp.jumpCount == 0) {
            sp.coyoteTimer = PhysicsConstants.COYOTE_TIME;
        }
        if (sp.coyoteTimer > 0f) sp.coyoteTimer -= DT;

        // ── Dash timers ───────────────────────────────────────────────────────
        if (sp.isDashing) {
            sp.dashTimer -= DT;
            if (sp.dashTimer <= 0f) {
                sp.isDashing    = false;
                sp.dashTimer    = 0f;
                sp.dashCooldown = PhysicsConstants.DASH_COOLDOWN;
            }
        }
        if (sp.dashCooldown > 0f) sp.dashCooldown -= DT;

        // ── Rising-edge input detection ───────────────────────────────────────
        boolean jumpJustPressed = cmd.jump && !sp.prevJump;
        boolean dashJustPressed = cmd.dash && !sp.prevDash;

        // ── Jump buffer: store a jump press for landing ───────────────────────
        if (jumpJustPressed) sp.jumpBuffer = PhysicsConstants.JUMP_BUFFER_TIME;
        if (sp.jumpBuffer > 0f) sp.jumpBuffer -= DT;

        // ── Dash initiation ───────────────────────────────────────────────────
        if (dashJustPressed && sp.dashCooldown <= 0f && !sp.isDashing) {
            sp.isDashing = true;
            sp.dashTimer = PhysicsConstants.DASH_DURATION;
            p.vy = 0f;  // cancel vertical momentum for horizontal dash
        }

        // ── Horizontal movement ───────────────────────────────────────────────
        if (sp.isDashing) {
            // Dash overrides normal velocity; direction locked to current facing
            p.vx = PhysicsConstants.DASH_SPEED * sp.facing;
        } else {
            float targetVx = 0f;
            if (cmd.right) targetVx =  PhysicsConstants.MAX_RUN_SPEED;
            if (cmd.left)  targetVx = -PhysicsConstants.MAX_RUN_SPEED;
            if (cmd.crouch) targetVx *= PhysicsConstants.CROUCH_SPEED_MULT;
            p.vx = targetVx;
            if (cmd.right) sp.facing =  1;
            if (cmd.left)  sp.facing = -1;
        }

        // ── Jump logic ────────────────────────────────────────────────────────
        boolean canGroundJump = p.onGround || sp.coyoteTimer > 0f;
        boolean jumpTriggered = jumpJustPressed || (sp.jumpBuffer > 0f && canGroundJump);

        if (canGroundJump && jumpTriggered && sp.jumpCount == 0) {
            // First jump — ground or coyote
            p.vy           = -PhysicsConstants.JUMP_POWER;
            p.onGround     = false;
            sp.jumpCount   = 1;
            sp.coyoteTimer = 0f;
            sp.jumpBuffer  = 0f;
        } else if (!canGroundJump && jumpJustPressed && sp.jumpCount == 1 && !sp.isDashing) {
            // Double jump — airborne, first jump already used
            p.vy          = -PhysicsConstants.DOUBLE_JUMP_POWER;
            sp.jumpCount  = 2;
            sp.jumpBuffer = 0f;
        }

        // ── Wall jump ─────────────────────────────────────────────────────────
        if (jumpJustPressed && p.onWall && !p.onGround && sp.jumpCount < 2) {
            p.vx        = -p.wallDir * PhysicsConstants.WALL_JUMP_POWER_X;
            p.vy        = -PhysicsConstants.WALL_JUMP_POWER_Y;
            sp.facing   = -p.wallDir;
            // Wall jump counts as the first (or second) jump
            sp.jumpCount = Math.max(sp.jumpCount + 1, 1);
            sp.jumpBuffer = 0f;
        }

        // ── Gravity modifier flags ────────────────────────────────────────────
        // Jump-cut: release jump while still rising → extra gravity via PhysicsSystem
        p.jumpCutActive  = !cmd.jump && p.vy < 0f;
        // Fast-fall: hold down while airborne
        p.fastFallActive = cmd.down && !p.onGround;

        // ── Persist state for next tick ───────────────────────────────────────
        sp.wasOnGround = p.onGround;
        sp.prevJump    = cmd.jump;
        sp.prevDash    = cmd.dash;

        // ── Wall slide ────────────────────────────────────────────────────────
        applyWallSlide(sp, p);

        // ── Animation state ───────────────────────────────────────────────────
        if (sp.isDashing) {
            sp.animState = "dash";
        } else if (sp.isWallSliding) {
            sp.animState = "wall_slide";
        } else if (!p.onGround) {
            sp.animState = p.vy < 0f ? "jump" : "fall";
        } else if (cmd.crouch) {
            sp.animState = "crouch";
        } else if (Math.abs(p.vx) > 0.1f) {
            sp.animState = "run";
        } else {
            sp.animState = "idle";
        }
    }

    /**
     * Wall slide stamina state machine.
     * Mirrors Python mechanics/wall_slide.py WallSlideMechanic.on_tick() exactly.
     * Called after horizontal/jump logic so p.onWall / p.onGround are already updated.
     */
    private static void applyWallSlide(SimPlayer sp, PhysicsState p) {
        boolean touchingWall = p.onWall && !p.onGround;

        // ── Exhaust detach: nudge off wall for a few ticks after stamina runs out ─
        if (sp.exhaustDetachFrames > 0) {
            if (p.wallDir != 0) p.x += -p.wallDir;  // 1px away from wall
            p.onWall  = false;
            p.wallDir = 0;
            p.vy = Math.max(p.vy, 2.0f);
            sp.exhaustDetachFrames--;
            touchingWall = false;
        }

        // ── Currently sliding: check exit conditions first ────────────────────
        if (sp.isWallSliding) {
            touchingWall = p.onWall && !p.onGround;
            if (!touchingWall || sp.wallSlideStamina <= SimPlayer.WALL_SLIDE_EXHAUST_THRESH) {
                // Exhaust
                sp.wallSlideStamina = Math.max(0f,
                    sp.wallSlideStamina - SimPlayer.WALL_SLIDE_EXHAUST_PENALTY);
                sp.isWallSliding           = false;
                sp.awaitGroundAfterExhaust = true;
                sp.exhaustDetachFrames     = 6;
                p.onWall  = false;
                p.wallDir = 0;
                p.vy = Math.max(p.vy, 2.0f);
            } else {
                // Continue sliding: drain stamina, cap fall speed
                sp.wallSlideStamina = Math.max(0f,
                    sp.wallSlideStamina - DT * SimPlayer.WALL_SLIDE_DRAIN_MULT);
                p.vy = Math.min(p.vy + 0.3f, SimPlayer.WALL_SLIDE_SPEED);
            }
            return;
        }

        // ── Consider starting a new slide ─────────────────────────────────────
        boolean canSlide = touchingWall
            && sp.wallSlideStamina >= SimPlayer.WALL_SLIDE_MIN_STAMINA
            && !sp.awaitGroundAfterExhaust;

        if (canSlide) {
            sp.isWallSliding = true;
            p.vy = Math.min(p.vy + 0.3f, SimPlayer.WALL_SLIDE_SPEED);
            return;
        }

        // ── Not sliding: regen and friction ──────────────────────────────────
        // Regen gating: require ground contact before regen restarts after exhaust
        if (p.onGround) {
            sp.awaitGroundAfterExhaust = false;
            sp.exhaustDetachFrames     = 0;
        }

        boolean blockRegen = touchingWall || sp.awaitGroundAfterExhaust;
        if (!blockRegen && sp.wallSlideStamina < SimPlayer.WALL_SLIDE_MAX_STAMINA) {
            sp.wallSlideStamina = Math.min(
                SimPlayer.WALL_SLIDE_MAX_STAMINA,
                sp.wallSlideStamina + SimPlayer.WALL_SLIDE_REGEN_RATE * DT);
        }

        // Wall friction: touching wall but not sliding slows descent slightly
        if (touchingWall && !sp.awaitGroundAfterExhaust) {
            p.vy = Math.min(p.vy + 0.3f, SimPlayer.WALL_FRICTION_SPEED);
        }
    }

    private void stepPlatforms() {
        for (FallingPlatform fp : fallingPlatforms) {
            boolean supported = false;
            for (SimPlayer p : players.values()) {
                if (p.isAlive() && fp.entityOnPlatform(
                        p.physics.x, p.physics.y,
                        p.physics.width, p.physics.height,
                        p.physics.onGround)) {
                    supported = true;
                    break;
                }
            }
            fp.step(DT, supported);
        }
    }

    private void stepEnemies() {
        // Collect alive player positions (for targeting and multi-player aware AI)
        List<float[]> playerTuples = new ArrayList<>(players.size());
        for (SimPlayer p : players.values()) {
            if (p.isAlive()) {
                playerTuples.add(new float[]{
                    p.physics.x, p.physics.y, p.physics.width, p.physics.height
                });
            }
        }
        if (playerTuples.isEmpty()) return;

        float[] nearest = playerTuples.get(0);

        for (SimEnemy en : enemies) {
            if (!en.isAlive()) continue;
            stepEnemyAI(en, nearest, playerTuples);
            // Flying enemies manage their own vertical movement (no CollisionSystem for them)
            if (en.canFly) applyFlyingEnemyMovement(en);
            // Ground enemies: gravity + collision handled by PhysicsSystem/CollisionSystem via EntityManager
        }
    }

    /**
     * Enemy AI state machine — mirrors Python entities/enemy.py EnemyManager.update().
     * Simplified to the four states used in the server sim.
     */
    private void stepEnemyAI(SimEnemy en, float[] nearest, List<float[]> players) {
        float dist = en.distanceTo(nearest[0], nearest[1]);

        switch (en.aiState) {
            case IDLE, PATROL -> {
                // Move horizontally between patrol waypoints
                float speed = en.moveSpeed * en.patrolSpeedMult * DT;
                en.physics.x += en.facingRight ? speed : -speed;

                // Bounce at waypoint limits
                if (en.physics.x <= en.patrolMinX) {
                    en.physics.x  = en.patrolMinX;
                    en.facingRight = true;
                } else if (en.physics.x + en.physics.width >= en.patrolMaxX) {
                    en.physics.x  = en.patrolMaxX - en.physics.width;
                    en.facingRight = false;
                }

                // Detect player
                if (dist < en.detectionRadius) en.aiState = EnemyAIState.CHASE;
            }
            case CHASE -> {
                // Move toward nearest player
                float tx = nearest[0];
                float cx = en.physics.x + en.physics.width * 0.5f;
                float speed = en.moveSpeed * DT;
                if (tx > cx) { en.physics.x += speed; en.facingRight = true; }
                else         { en.physics.x -= speed; en.facingRight = false; }

                if (dist < en.attackRange)     { en.aiState = EnemyAIState.ATTACK; en.attackWindupTimer = SimEnemy.ATTACK_WINDUP_TIME; }
                else if (dist > en.detectionRadius * 1.5f) en.aiState = EnemyAIState.PATROL;
            }
            case ATTACK -> {
                // Telegraphed attack phases
                if (en.attackWindupTimer > 0) {
                    en.attackWindupTimer -= DT;
                } else if (en.attackActiveTimer < SimEnemy.ATTACK_ACTIVE_TIME) {
                    en.attackActiveTimer += DT;
                } else {
                    en.attackActiveTimer  = 0f;
                    en.attackRecoveryTimer = SimEnemy.ATTACK_RECOVERY_TIME;
                    en.aiState = EnemyAIState.CHASE;
                }
            }
            case STUNNED -> {
                en.stunTimer -= DT;
                if (en.stunTimer <= 0) {
                    en.stunTimer = 0;
                    en.aiState  = EnemyAIState.PATROL;
                }
            }
            case DEAD -> { /* nothing */ }
        }
    }

    /** Flying enemies do their own simple vertical sinusoidal hover — no gravity/collision. */
    private static void applyFlyingEnemyMovement(SimEnemy en) {
        // Bats hover in place vertically with a gentle sine wave
        en.physics.y += (float)(Math.sin(System.nanoTime() * 1e-9 * 2.0) * 0.5);
        // Clamp to reasonable world bounds
        if (en.physics.y < 0) en.physics.y = 0;
    }

    private void stepCombat() {
        for (SimEnemy en : enemies) {
            if (!en.isAlive()) continue;
            if (en.aiState != EnemyAIState.ATTACK) continue;
            // Only during the ACTIVE window
            if (en.attackActiveTimer <= 0) continue;

            for (SimPlayer p : players.values()) {
                if (!p.isAlive()) continue;
                // Simple AABB check
                if (aabbOverlap(en.physics.x, en.physics.y, en.physics.width, en.physics.height,
                                p.physics.x, p.physics.y, p.physics.width, p.physics.height)) {
                    p.takeDamage(en.baseDamage);
                }
            }
        }
    }

    private void stepPickups() {
        for (SimPickup pu : pickups) {
            if (!pu.alive) continue;
            pu.tick();
            // Authoritative collection
            for (SimPlayer p : players.values()) {
                if (p.isAlive() && pu.overlaps(p.physics.x, p.physics.y, p.physics.width, p.physics.height)) {
                    pu.alive = false;
                    // Apply pickup effect (health restore)
                    if ("health_potion".equals(pu.pickupType)) {
                        p.health = Math.min(p.maxHealth, p.health + 2);
                    }
                    break;
                }
            }
        }
    }

    // ── Utility ───────────────────────────────────────────────────────────────

    private static boolean aabbOverlap(float ax, float ay, float aw, float ah,
                                        float bx, float by, float bw, float bh) {
        return ax < bx + bw && ax + aw > bx
            && ay < by + bh && ay + ah > by;
    }

    private void rebuildPlayerEntities() {
        // Remove all player-tagged entities then re-add from current players map
        for (com.indieniinja.core.Entity e : entityManager.byTag("player")) {
            entityManager.destroy(e.entityId);
        }
        for (SimPlayer p : players.values()) {
            var entity = entityManager.create(com.indieniinja.core.EntityType.PLAYER, p.physics);
            entity.addTag("player");
        }
    }

    private SimEnemy buildEnemy(LevelLayout.EnemySpawn spec, int idx) {
        // Stats from Python ENEMY_DEFINITIONS (entities/enemy.py)
        return switch (spec.type()) {
            case "goblin"   -> new SimEnemy(hubId+"_goblin_"+idx,   "goblin",   spec.x(), spec.y(), 32, 48, 3, 1, 72f,  200f, 32f, spec.patrolMinX(), spec.patrolMaxX(), false);
            case "bat"      -> new SimEnemy(hubId+"_bat_"+idx,      "bat",      spec.x(), spec.y(), 28, 28, 2, 1, 90f,  180f, 28f, spec.patrolMinX(), spec.patrolMaxX(), true);
            case "slime"    -> new SimEnemy(hubId+"_slime_"+idx,    "slime",    spec.x(), spec.y(), 32, 28, 4, 2, 60f,  160f, 28f, spec.patrolMinX(), spec.patrolMaxX(), false);
            case "skeleton" -> new SimEnemy(hubId+"_skeleton_"+idx, "skeleton", spec.x(), spec.y(), 32, 48, 3, 1, 60f,  200f, 64f, spec.patrolMinX(), spec.patrolMaxX(), false);
            case "wolf"     -> new SimEnemy(hubId+"_wolf_"+idx,     "wolf",     spec.x(), spec.y(), 40, 32, 3, 2, 90f,  220f, 40f, spec.patrolMinX(), spec.patrolMaxX(), false);
            default         -> new SimEnemy(hubId+"_enemy_"+idx,    spec.type(),spec.x(), spec.y(), 32, 48, 3, 1, 72f,  200f, 32f, spec.patrolMinX(), spec.patrolMaxX(), false);
        };
    }

    // ── Accessors (for testing) ───────────────────────────────────────────────

    public Map<Integer, SimPlayer> getPlayers()  { return java.util.Collections.unmodifiableMap(players); }
    public List<SimEnemy>          getEnemies()  { return java.util.Collections.unmodifiableList(enemies); }
    public List<SimPickup>         getPickups()  { return java.util.Collections.unmodifiableList(pickups); }
}
