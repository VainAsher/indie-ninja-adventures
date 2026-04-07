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
    private final List<SimEnemy>    enemies   = new ArrayList<>();
    private final List<SimPickup>   pickups   = new ArrayList<>();
    private final List<FallingPlatform> fallingPlatforms = new ArrayList<>();
    private final List<SimShuriken> shurikens = new ArrayList<>();
    private int shurikenSeq = 0;

    // ── World ─────────────────────────────────────────────────────────────────
    public final long   seed;
    public final String hubId;
    private final float worldHeightPx;
    private final com.indieniinja.physics.SpatialHash spatialHash;

    // ── Construction ─────────────────────────────────────────────────────────

    public GameSimulator(long seed, String hubId, LevelLayout layout) {
        this.seed          = seed;
        this.hubId         = hubId;
        this.worldHeightPx = layout.worldHeightPx;
        this.spatialHash   = layout.spatialHash;

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

        // 5. Server-side player-enemy combat (melee + contact)
        stepCombat();

        // 6. Spawn any shurikens flagged by applyPlayerInput
        spawnPendingShurikens();

        // 7. Advance shurikens (movement + tile/enemy collision)
        stepShurikens();

        // 8. Pickups: lifetime + authoritative collection
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
            ps.wallSlideStamina  = p.wallSlideStamina;
            ps.isWallSliding     = p.isWallSliding;
            ps.teleportPhaseMode = p.teleportPhaseMode;
            ps.teleportCursorX   = p.teleportCursorX;
            ps.teleportCursorY   = p.teleportCursorY;
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

        // Shurikens
        for (SimShuriken sh : shurikens) {
            if (!sh.alive) continue;
            com.indieniinja.network.ShurikenState ss = new com.indieniinja.network.ShurikenState();
            ss.shurikenId = sh.shurikenId;
            ss.ownerSlot  = sh.ownerSlot;
            ss.x          = sh.x;
            ss.y          = sh.y;
            ss.vx         = sh.vx;
            ss.stuck      = sh.stuck;
            ss.alive      = sh.alive;
            snap.shurikens.add(ss);
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
    private void applyPlayerInput(SimPlayer sp, InputCommand cmd) {
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

        // ── Attack / throw cooldowns ──────────────────────────────────────────
        if (sp.attackActiveTicks > 0) {
            sp.attackActiveTicks--;
            if (sp.attackActiveTicks == 0) sp.isAttacking = false;
        }
        if (sp.attackCooldown  > 0f) sp.attackCooldown  -= DT;
        if (sp.throwCooldown   > 0f) {
            sp.throwCooldown -= DT;
            if (sp.throwCooldown <= 0f) sp.isThrowing = false;
        }

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
        boolean jumpJustPressed   = cmd.jump          && !sp.prevJump;
        boolean dashJustPressed   = cmd.dash          && !sp.prevDash;
        boolean attackJustPressed = cmd.attack        && !sp.prevAttack;
        boolean throwJustPressed  = cmd.throwShuriken && !sp.prevThrow;

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
        if (sp.wallJumpLockTimer > 0f) sp.wallJumpLockTimer -= DT;

        if (sp.isDashing) {
            // Dash overrides normal velocity; direction locked to current facing
            p.vx = PhysicsConstants.DASH_SPEED * sp.facing;
        } else if (sp.wallJumpLockTimer > 0f) {
            // Wall-jump input lock — preserve the launch vx so momentum carries the
            // player away from the wall.  Mirrors Python entities/player.py line 260:
            //   if self.state.is_dashing or self.state.wall_jump_lock > 0: (skip horiz input)
            // Only update facing from input during the lock so the sprite flips immediately.
            if (cmd.right) sp.facing =  1;
            if (cmd.left)  sp.facing = -1;
        } else {
            // Default: walk at 0.6× speed (no ALT).  ALT (cmd.slowWalk) = run at full speed.
            // Mirrors Python entities/player.py: is_running = ALT key; else slow_walk 0.6×
            float speedMult = cmd.slowWalk ? 1.0f : 0.6f;
            float maxSpeed  = PhysicsConstants.MAX_RUN_SPEED * speedMult;
            float targetVx  = 0f;
            if (cmd.right) targetVx =  maxSpeed;
            if (cmd.left)  targetVx = -maxSpeed;
            if (cmd.crouch) targetVx *= PhysicsConstants.CROUCH_SPEED_MULT;
            p.vx = targetVx;
            if (cmd.right) sp.facing =  1;
            if (cmd.left)  sp.facing = -1;
        }

        // ── Crouch height ─────────────────────────────────────────────────────
        // Python CrouchMechanic: height collapses to PLAYER_CROUCH_HEIGHT (28) while
        // crouching on ground; the AABB bottom stays fixed (y shifts up by the difference).
        // Uncrouch: restore full height, shift y back down.
        boolean isCrouching = cmd.crouch && p.onGround;
        if (isCrouching && p.height == PhysicsConstants.PLAYER_HEIGHT) {
            int diff = PhysicsConstants.PLAYER_HEIGHT - PhysicsConstants.PLAYER_CROUCH_HEIGHT;
            p.y      += diff;   // keep feet in same position
            p.height  = PhysicsConstants.PLAYER_CROUCH_HEIGHT;
        } else if (!isCrouching && p.height == PhysicsConstants.PLAYER_CROUCH_HEIGHT) {
            int diff = PhysicsConstants.PLAYER_HEIGHT - PhysicsConstants.PLAYER_CROUCH_HEIGHT;
            p.y      -= diff;   // restore feet position
            p.height  = PhysicsConstants.PLAYER_HEIGHT;
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
        // Mirrors Python mechanics/jump.py _try_wall_jump():
        //   - No jump-count gate (wall jump always available on wall/coyote)
        //   - 1.6× vy boost whether sliding or not (strong upward pop)
        //   - Full WALL_JUMP_POWER_X horizontal (away from wall) + input lock so
        //     the player can't immediately cancel the momentum — enables two-wall climbing
        //   - Reset jumpCount so double-jump is refreshed after wall jump
        boolean canWallJump = p.onWall || sp.wallCoyoteTimer > 0f;
        if (jumpJustPressed && canWallJump && !p.onGround) {
            int wallDir = (p.wallDir != 0) ? p.wallDir
                        : (sp.lastWallDir != 0) ? sp.lastWallDir
                        : (sp.facing >= 0 ? -1 : 1);
            p.vy         = -PhysicsConstants.WALL_JUMP_POWER_Y * 1.6f;
            p.vx         = -wallDir * PhysicsConstants.WALL_JUMP_POWER_X;  // full power away from wall
            sp.facing    = -wallDir;
            sp.jumpCount = 0;
            sp.jumpBuffer= 0f;
            sp.isWallSliding          = false;
            sp.wallCoyoteTimer        = 0f;
            sp.wallJumpLockTimer      = SimPlayer.WALL_JUMP_INPUT_LOCK;
            sp.awaitGroundAfterExhaust = false;
            p.onWall     = false;
            p.wallDir    = 0;
        }

        // Track last wall direction for wall coyote and fallback wall-jump dir
        if (p.onWall && p.wallDir != 0) sp.lastWallDir = p.wallDir;

        // Wall coyote timer: brief window after leaving wall where wall-jump still works
        if (p.onWall && !p.onGround) sp.wallCoyoteTimer = PhysicsConstants.COYOTE_TIME;
        else if (sp.wallCoyoteTimer > 0f) sp.wallCoyoteTimer -= DT;

        // ── Gravity modifier flags ────────────────────────────────────────────
        // Jump-cut: release jump while still rising → extra gravity via PhysicsSystem
        p.jumpCutActive  = !cmd.jump && p.vy < 0f;
        // Fast-fall: hold down while airborne
        p.fastFallActive = cmd.down && !p.onGround;

        // ── Persist state for next tick ───────────────────────────────────────
        sp.wasOnGround = p.onGround;
        sp.prevJump    = cmd.jump;
        sp.prevDash    = cmd.dash;
        sp.prevAttack  = cmd.attack;
        sp.prevThrow   = cmd.throwShuriken;

        // ── Teleport ──────────────────────────────────────────────────────────
        // Mirrors Python TeleportMechanic exactly:
        //   Press F/T  → enter 0.6s phase; ghost cursor starts at player position
        //   Hold phase → directional keys steer cursor at 420 px/s, capped to 256 px
        //   After 0.6s → auto-warp to cursor (skip warp if blocked); 3s cooldown
        if (sp.teleportCooldown > 0f) sp.teleportCooldown -= DT;
        if (sp.isTeleporting) {
            sp.teleportInvulnTimer -= DT;
            if (sp.teleportInvulnTimer <= 0f) sp.isTeleporting = false;
        }
        boolean teleportHeld        = cmd.teleport;
        boolean teleportJustPressed = teleportHeld && !sp.prevTeleport;
        sp.prevTeleport = teleportHeld;

        // Enter phase on key press edge
        if (teleportJustPressed && sp.teleportCooldown <= 0f
                && !sp.isTeleporting && !sp.teleportPhaseMode) {
            sp.teleportPhaseMode  = true;
            sp.teleportPhaseTimer = SimPlayer.TELEPORT_PHASE_TIME;
            sp.teleportOriginX    = p.x;
            sp.teleportOriginY    = p.y;
            sp.teleportCursorX    = p.x;
            sp.teleportCursorY    = p.y;
            p.vx = 0f;
            p.vy = 0f;
        }

        // During phase: freeze player, steer cursor, auto-warp when timer expires
        if (sp.teleportPhaseMode) {
            p.vx = 0f;
            p.vy = 0f;

            // 8-directional cursor steering (Python: update_phase_direction(dx, dy))
            int dirX = (cmd.right ? 1 : 0) - (cmd.left  ? 1 : 0);
            int dirY = (cmd.down  ? 1 : 0) - ((cmd.up || cmd.jump) ? 1 : 0); // Y-DOWN: up=-Y
            if (dirX != 0 || dirY != 0) {
                float step = SimPlayer.TELEPORT_CURSOR_SPEED * DT;
                sp.teleportCursorX += dirX * step;
                sp.teleportCursorY += dirY * step;
                float cdx  = sp.teleportCursorX - sp.teleportOriginX;
                float cdy  = sp.teleportCursorY - sp.teleportOriginY;
                float dist = (float) Math.sqrt(cdx * cdx + cdy * cdy);
                if (dist > SimPlayer.TELEPORT_RANGE) {
                    sp.teleportCursorX = sp.teleportOriginX + cdx / dist * SimPlayer.TELEPORT_RANGE;
                    sp.teleportCursorY = sp.teleportOriginY + cdy / dist * SimPlayer.TELEPORT_RANGE;
                }
            }

            // Decrement phase timer; warp when it hits zero (Python: teleport_cast_time → 0)
            sp.teleportPhaseTimer -= DT;
            if (sp.teleportPhaseTimer <= 0f) {
                float cx = sp.teleportCursorX;
                float cy = sp.teleportCursorY;
                boolean blocked = false;
                var tiles = spatialHash.candidates(cx, cy, p.width, p.height);
                for (var tile : tiles) {
                    if (!tile.isPlatform() && tile.overlaps(cx, cy, p.width, p.height)) {
                        blocked = true; break;
                    }
                }
                if (!blocked) {
                    p.x  = cx;
                    p.y  = cy;
                    p.vx = 0f;
                    p.vy = 0f;
                }
                sp.teleportPhaseMode   = false;
                sp.isTeleporting       = true;
                sp.teleportInvulnTimer = SimPlayer.TELEPORT_INVULN;
                sp.teleportCooldown    = SimPlayer.TELEPORT_COOLDOWN;
                sp.isDashing           = false;
            }
        }

        // ── Melee attack ──────────────────────────────────────────────────────
        if (attackJustPressed && sp.attackCooldown <= 0f && !sp.isAttacking) {
            sp.isAttacking      = true;
            sp.attackActiveTicks = SimPlayer.MELEE_ACTIVE_TICKS;
            sp.attackCooldown   = SimPlayer.MELEE_COOLDOWN;
        }

        // ── Shuriken throw ────────────────────────────────────────────────────
        if (throwJustPressed && sp.throwCooldown <= 0f && sp.shurikenAmmo > 0) {
            sp.shurikenAmmo--;
            sp.isThrowing    = true;
            sp.throwCooldown = SimPlayer.SHURIKEN_COOLDOWN;
            // Actual SimShuriken is spawned by the outer GameSimulator (needs list access)
            sp.pendingShuriken = true;
        }

        // ── Wall slide ────────────────────────────────────────────────────────
        applyWallSlide(sp, p);

        // ── Animation state ───────────────────────────────────────────────────
        if (sp.teleportPhaseMode) {
            sp.animState = "idle";   // player frozen in place while cursor moves
        } else if (sp.isTeleporting) {
            sp.animState = "teleport";
        } else if (sp.isDashing) {
            sp.animState = "dash";
        } else if (sp.isAttacking) {
            sp.animState = "attack";
        } else if (sp.isThrowing) {
            sp.animState = "throw";
        } else if (sp.isWallSliding) {
            sp.animState = "wall_slide";
        } else if (!p.onGround) {
            sp.animState = p.vy < 0f ? "jump" : "fall";
        } else if (cmd.crouch) {
            sp.animState = "crouch";
        } else if (Math.abs(p.vx) > 0.1f) {
            // ALT key (cmd.slowWalk) = run; default movement = slow_walk
            sp.animState = cmd.slowWalk ? "run" : "slow_walk";
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
        // ── Enemy → player contact damage ────────────────────────────────────
        for (SimEnemy en : enemies) {
            if (!en.isAlive()) continue;
            if (en.aiState != EnemyAIState.ATTACK) continue;
            if (en.attackActiveTimer <= 0) continue;
            for (SimPlayer p : players.values()) {
                if (!p.isAlive()) continue;
                if (aabbOverlap(en.physics.x, en.physics.y, en.physics.width, en.physics.height,
                                p.physics.x, p.physics.y, p.physics.width, p.physics.height)) {
                    p.takeDamage(en.baseDamage);
                }
            }
        }

        // ── Player melee → enemy damage ───────────────────────────────────────
        for (SimPlayer sp : players.values()) {
            if (!sp.isAlive() || !sp.isAttacking) continue;
            // Melee hitbox: extends forward from player center in facing direction
            float cx      = sp.physics.x + sp.physics.width * 0.5f;
            float cy      = sp.physics.y + sp.physics.height * 0.5f;
            float reach   = SimPlayer.MELEE_REACH;
            float halfH   = SimPlayer.MELEE_HEIGHT * 0.5f;
            float hbX     = sp.facing >= 0 ? cx : cx - reach;
            float hbY     = cy - halfH;
            for (SimEnemy en : enemies) {
                if (!en.isAlive()) continue;
                if (aabbOverlap(hbX, hbY, reach, SimPlayer.MELEE_HEIGHT,
                                en.physics.x, en.physics.y, en.physics.width, en.physics.height)) {
                    en.takeDamage(SimPlayer.MELEE_DAMAGE);
                }
            }
        }
    }

    private void spawnPendingShurikens() {
        for (SimPlayer sp : players.values()) {
            if (!sp.pendingShuriken) continue;
            sp.pendingShuriken = false;
            float cx = sp.physics.x + sp.physics.width  * 0.5f;
            float cy = sp.physics.y + sp.physics.height * 0.5f;
            float vx = sp.facing * SimPlayer.SHURIKEN_SPEED;
            shurikens.add(new SimShuriken(
                hubId + "_shuriken_" + shurikenSeq++,
                sp.slot, cx - SimShuriken.W * 0.5f, cy - SimShuriken.H * 0.5f, vx, 0f));
        }
    }

    private void stepShurikens() {
        shurikens.removeIf(s -> !s.alive);
        for (SimShuriken s : shurikens) {
            if (s.stuck) {
                s.stuckTimer -= DT;
                if (s.stuckTimer <= 0) s.alive = false;
                continue;
            }
            s.x   += s.vx;
            s.y   += s.vy;
            s.ttl -= DT;
            if (s.ttl <= 0) { s.alive = false; continue; }

            // Tile collision via SpatialHash
            var tiles = spatialHash.candidates(s.x, s.y, SimShuriken.W, SimShuriken.H);
            for (var tile : tiles) {
                if (tile.overlaps(s.x, s.y, SimShuriken.W, SimShuriken.H)) {
                    s.stuck      = true;
                    s.stuckTimer = 2.0f;
                    break;
                }
            }
            if (s.stuck) continue;

            // Enemy collision
            for (SimEnemy en : enemies) {
                if (!en.isAlive()) continue;
                if (aabbOverlap(s.x, s.y, SimShuriken.W, SimShuriken.H,
                                en.physics.x, en.physics.y, en.physics.width, en.physics.height)) {
                    en.takeDamage(SimPlayer.SHURIKEN_DAMAGE);
                    s.stuck      = true;
                    s.stuckTimer = 0.1f;
                    break;
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
