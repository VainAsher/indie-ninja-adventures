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

import com.indieniinja.network.BossState;
import com.indieniinja.network.PortalState;

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
    private final List<SimNPC>      npcs      = new ArrayList<>();
    private final List<SimBoss>     bosses    = new ArrayList<>();
    private final List<SimPortal>   portals   = new ArrayList<>();
    /** NPC ID → shop (only for "shop" type NPCs). */
    private final Map<String, SimShop> shops = new LinkedHashMap<>();
    private int shurikenSeq = 0;
    private int lootSeq     = 0;

    // ── Game mode state ───────────────────────────────────────────────────────
    private GameMode gameMode    = GameMode.ARCADE;
    private int      arcadeScore = 0;
    private int      arcadeDepth = 0;
    private int      arcadeRooms = 10;

    // ── World ─────────────────────────────────────────────────────────────────
    public final long   seed;
    public final String hubId;
    private final float worldHeightPx;
    private com.indieniinja.physics.SpatialHash spatialHash;

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

        // Spawn boss (boss rooms only)
        if (layout.bossSpawn != null) {
            LevelLayout.BossSpawn bs = layout.bossSpawn;
            BossType bt = BossType.fromWire(bs.bossTypeWire());
            bosses.add(new SimBoss(hubId + "_boss_0", bt, bs.x(), bs.y()));
        }

        // Spawn portals
        int portalIdx = 0;
        for (LevelLayout.PortalSpawn spec : layout.portalSpawns) {
            portals.add(new SimPortal(
                hubId + "_portal_" + portalIdx++,
                spec.portalType(), spec.destinationId(),
                spec.x(), spec.y(), spec.requiredAbility()
            ));
        }

        // Spawn NPCs (no physics entity — NPCs use simple patrol, no collision sim)
        int npcIdx = 0;
        for (LevelLayout.NPCSpawn spec : layout.npcSpawns) {
            String npcId = hubId + "_npc_" + npcIdx++;
            npcs.add(new SimNPC(
                npcId, spec.type(), spec.x(), spec.y(),
                32, 48,   // Python default: width=32, height=48
                spec.patrolMinX(), spec.patrolMaxX()
            ));
            // Create a shop for "shop" type NPCs
            if ("shop".equals(spec.type())) {
                int shopTier = 1 + (int)(Math.abs(seed ^ npcId.hashCode()) % 3); // tier 1-3
                shops.put(npcId, new SimShop(npcId, shopTier, seed ^ npcId.hashCode()));
            }
        }
    }

    // ── Public API ────────────────────────────────────────────────────────────

    /**
     * Add a player to the simulation.
     * Called when a player connects or enters this zone.
     */
    public void addPlayer(SimPlayer player) {
        players.put(player.slot, player);
        // Sandbox mode: start with generous currency + all abilities unlocked
        if (gameMode == GameMode.SANDBOX) {
            player.inventory.addCurrency(500);
            player.unlockedAbilities.addAll(java.util.List.of(
                "double_jump", "dash", "wall_jump", "shuriken", "teleport", "ninjutsu"
            ));
        }
        // Register physics state so PhysicsSystem and CollisionSystem process it
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
     * Set game mode and arcade depth/rooms.  Called by ZoneSimulationLoop
     * after the simulator is built but before any players join.
     */
    public void setMode(GameMode mode, int depth, int rooms) {
        this.gameMode    = mode;
        this.arcadeDepth = depth;
        this.arcadeRooms = rooms;
    }

    /** Accessor used by ZoneSimulationLoop to read arcade progression state. */
    public int getArcadeScore() { return arcadeScore; }
    public int getArcadeDepth() { return arcadeDepth; }
    public int getArcadeRooms() { return arcadeRooms; }

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

        // 9. NPC patrol + player-facing
        stepNpcs();

        // 10. Boss AI + combat
        stepBosses();

        // 11. Portal animation timers
        for (SimPortal portal : portals) portal.step(DT);
    }

    /**
     * Build a WorldSnapshot from current sim state for broadcast.
     * Java equivalent of Python GameSimulator.get_snapshot(frame).
     */
    public WorldSnapshot getSnapshot(long frame) {
        WorldSnapshot snap = new WorldSnapshot();
        snap.frame        = frame;
        snap.seed         = seed;
        snap.hubId        = hubId;
        snap.gameMode     = gameMode.wire;
        snap.arcadeScore  = arcadeScore;
        snap.arcadeDepth  = arcadeDepth;
        snap.arcadeRooms  = arcadeRooms;

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
            ps.stamina           = p.stamina;
            ps.mana              = p.mana;
            ps.ninjutsuCasting   = p.ninjutsuCasting;
            // Inventory — build wire type from SimInventory
            ps.inventory = buildInventoryState(p.inventory);
            // Progression
            ps.experience = p.experience;
            ps.level      = p.level;
            ps.abilities  = new java.util.ArrayList<>(p.unlockedAbilities);
            snap.players.add(ps);
        }

        // Enemies
        for (SimEnemy en : enemies) {
            if (en.removed) continue;
            EnemyState es = new EnemyState();
            es.enemyId     = en.enemyId;
            es.enemyType   = en.enemyType;
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

        // NPCs
        for (SimNPC npc : npcs) {
            com.indieniinja.network.NPCState ns = new com.indieniinja.network.NPCState();
            ns.npcId          = npc.id;
            ns.npcType        = npc.type;
            ns.x              = npc.x;
            ns.y              = npc.y;
            ns.facing         = npc.facing;
            ns.animState      = npc.animState;
            ns.isInteractable = npc.isInteractable;
            snap.npcs.add(ns);
        }

        // Bosses
        for (SimBoss boss : bosses) {
            BossState bs = new BossState();
            bs.bossId     = boss.bossId;
            bs.bossType   = boss.type.wire;
            bs.x          = boss.physics.x;
            bs.y          = boss.physics.y;
            bs.hp         = boss.hp;
            bs.maxHp      = boss.maxHp;
            bs.aiState    = boss.aiState.wire;
            bs.phase      = boss.phaseNumber;
            bs.facingRight = boss.facingRight;
            bs.alive       = boss.isAlive();
            snap.bosses.add(bs);
        }

        // Portals — always included on full snapshots (WorldSnapshot.toMap() skips on deltas)
        for (SimPortal portal : portals) {
            snap.portals.add(portal.toState());
        }

        // Shop states — always included so client can show shop UI
        for (SimShop shop : shops.values()) {
            com.indieniinja.network.ShopState ss = new com.indieniinja.network.ShopState();
            ss.npcId = shop.npcId;
            ss.tier  = shop.tier;
            for (SimShop.Entry e : shop.getItems()) {
                ss.items.add(new com.indieniinja.network.ShopState.ShopItemState(
                    e.itemId(), e.stock(), e.buyPrice(), e.sellPrice()));
            }
            snap.shopStates.add(ss);
        }

        return snap;
    }

    // ── Trade handler ─────────────────────────────────────────────────────────

    /**
     * Handle a buy or sell request from a player.
     * Called from ZoneSimulationLoop when a TRADE_REQUEST message arrives.
     * Returns true if the transaction succeeded.
     */
    public boolean handleTradeRequest(int playerSlot, String npcId,
                                      String itemId, int qty, boolean isBuy) {
        SimPlayer p = players.get(playerSlot);
        if (p == null) return false;
        SimShop shop = shops.get(npcId);
        if (shop == null) return false;
        return isBuy ? shop.buy(itemId, qty, p.inventory)
                     : shop.sell(itemId, qty, p.inventory);
    }

    /**
     * Craft an item using the named recipe, consuming ingredients from inventory.
     * Returns true if the craft succeeded; false if recipe unknown or ingredients missing.
     */
    public boolean handleCraftRequest(int playerSlot, String recipeId) {
        SimPlayer p = players.get(playerSlot);
        if (p == null) return false;
        CraftingRecipe recipe = RecipeBook.get(recipeId);
        if (recipe == null) return false;
        return recipe.craft(p.inventory);
    }

    /**
     * Use a consumable item from the player's inventory.
     * Health potions restore HP; max_hp_upgrade increases maxHealth.
     * Returns true if the item was used successfully.
     */
    public boolean handleUseItem(int playerSlot, String itemId) {
        SimPlayer p = players.get(playerSlot);
        if (p == null) return false;
        ItemDatabase.ItemDef def = ItemDatabase.get(itemId);
        if (def == null || !def.consumable()) return false;
        if (!p.inventory.hasItem(itemId, 1)) return false;
        // Apply effect
        if (def.healthRestore() > 0) {
            if (p.health >= p.maxHealth) return false;  // already full HP
            p.health = Math.min(p.maxHealth, p.health + def.healthRestore());
        }
        if (def.healthBonus() > 0) {
            p.maxHealth += def.healthBonus();
            p.health = Math.min(p.maxHealth, p.health + def.healthBonus());
        }
        p.inventory.removeItem(itemId, 1);
        return true;
    }

    /**
     * Equip or unequip an item (weapon / armor).
     * Toggling the already-equipped item unequips it.
     * Returns true if the inventory changed.
     */
    public boolean handleEquipItem(int playerSlot, String itemId) {
        SimPlayer p = players.get(playerSlot);
        if (p == null) return false;
        ItemDatabase.ItemDef def = ItemDatabase.get(itemId);
        if (def == null) return false;
        if (!p.inventory.hasItem(itemId, 1)) return false;
        switch (def.type()) {
            case "weapon" -> {
                if (itemId.equals(p.inventory.equippedWeapon)) p.inventory.unequipItem(itemId);
                else p.inventory.equipItem(itemId);
            }
            case "armor"  -> {
                if (itemId.equals(p.inventory.equippedArmor)) p.inventory.unequipItem(itemId);
                else p.inventory.equipItem(itemId);
            }
            default -> { return false; }
        }
        return true;
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

        // ── Stamina + Mana resources ──────────────────────────────────────────
        // Mirrors Python player._update_resources()
        boolean isRunning = sp.animState.equals("run") || (cmd.slowWalk && false); // run=ALT held
        // Actually: run = not slowWalk (ALT = slowWalk, no ALT = run in Python)
        isRunning = !cmd.slowWalk && (cmd.left || cmd.right) && p.onGround;
        if (isRunning) {
            sp.stamina = Math.max(0f, sp.stamina - SimPlayer.STAMINA_RUN_DRAIN * DT);
        } else {
            float regenRate = p.onGround ? SimPlayer.STAMINA_REGEN_RATE : SimPlayer.STAMINA_REGEN_RATE * 0.5f;
            sp.stamina = Math.min(SimPlayer.STAMINA_MAX, sp.stamina + regenRate * DT);
        }
        sp.mana = Math.min(SimPlayer.MANA_MAX, sp.mana + SimPlayer.MANA_REGEN_RATE * DT);

        // ── Ninjutsu (L key) — hold to enter stance, release to cast Purify ───
        // Mirrors Python: request_stance() on hold, request_cast("purify") on release
        if (sp.ninjutsuCooldown > 0f) sp.ninjutsuCooldown -= DT;
        if (sp.ninjutsuCasting) {
            sp.ninjutsuCastTimer -= DT;
            if (sp.ninjutsuCastTimer <= 0f) sp.ninjutsuCasting = false;
        }
        boolean ninjutsuHeld    = cmd.ninjutsu;
        boolean ninjutsuRelease = sp.ninjutsuHeld && !ninjutsuHeld;
        sp.ninjutsuHeld = ninjutsuHeld;
        if (ninjutsuRelease && sp.ninjutsuCooldown <= 0f && sp.mana >= SimPlayer.NINJUTSU_MANA_COST) {
            sp.mana             = Math.max(0f, sp.mana - SimPlayer.NINJUTSU_MANA_COST);
            sp.ninjutsuCasting  = true;
            sp.ninjutsuCastTimer = SimPlayer.NINJUTSU_CAST_TIME;
            sp.ninjutsuCooldown = SimPlayer.NINJUTSU_COOLDOWN;
            // (Purify hazard clearing will hook here once hazards are implemented)
        }

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
                // Shrink check height by 1px so touching (not penetrating) the floor is not
                // treated as blocked — matches Python's strict pygame.Rect.colliderect().
                float checkH = p.height - 1f;
                boolean blocked = false;
                var tiles = spatialHash.candidates(cx, cy, p.width, checkH);
                for (var tile : tiles) {
                    if (!tile.isPlatform() && tile.overlaps(cx, cy, p.width, checkH)) {
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
        if (sp.ninjutsuCasting) {
            sp.animState = sp.ninjutsuHeld ? "ninjutsu_hand" : "ninjutsu_summon";
        } else if (sp.teleportPhaseMode) {
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
                    if (en.takeDamage(SimPlayer.MELEE_DAMAGE)) spawnLoot(en);
                }
            }
        }
    }

    /**
     * Spawn 1–2 loot pickups at the dead enemy's position and grant XP to the nearest player.
     * 70% coin, 20% health_potion, 10% nothing — matches Python enemy loot tables.
     */
    private void spawnLoot(SimEnemy en) {
        // Arcade score: +1 per kill
        if (gameMode == GameMode.ARCADE) arcadeScore++;

        // XP reward
        int xp = enemyXp(en.enemyType);
        grantXpToNearest(en.physics.x + en.physics.width * 0.5f,
                         en.physics.y + en.physics.height * 0.5f, xp);

        float cx = en.physics.x + en.physics.width  * 0.5f - 10f;
        float cy = en.physics.y;
        int roll = (int) Math.abs((en.physics.x * 7 + en.physics.y * 13 + lootSeq * 31) % 10);
        lootSeq++;
        String type = roll < 7 ? "coin" : roll < 9 ? "health_potion" : null;
        if (type != null) pickups.add(new SimPickup(hubId + "_loot_" + lootSeq, type, cx, cy));
        if (roll < 2)     pickups.add(new SimPickup(hubId + "_loot_" + (lootSeq + 100), "coin", cx + 12f, cy));
    }

    /** Spawn loot and XP from a dead boss. Drops 3–5 items plus guaranteed currency. */
    private void spawnBossLoot(SimBoss boss) {
        if (gameMode == GameMode.ARCADE) arcadeScore += 10;

        grantXpToNearest(boss.physics.x + boss.physics.width  * 0.5f,
                         boss.physics.y + boss.physics.height * 0.5f,
                         boss.type.xpReward());

        float cx = boss.physics.x + boss.physics.width * 0.5f;
        float cy = boss.physics.y;
        // Guaranteed: 3 coins + 1 health potion
        for (int i = 0; i < 3; i++)
            pickups.add(new SimPickup(hubId + "_bloot_" + lootSeq++, "coin", cx - 20f + i * 20f, cy));
        pickups.add(new SimPickup(hubId + "_bloot_" + lootSeq++, "health_potion", cx, cy - 32f));
    }

    private static int enemyXp(String type) {
        return switch (type) {
            case "goblin"   -> 10;
            case "slime"    ->  8;
            case "skeleton" -> 12;
            case "wolf"     -> 15;
            case "bat"      ->  6;
            default         -> 10;
        };
    }

    /** Grant XP to the player closest to the kill position. */
    private void grantXpToNearest(float kx, float ky, int xp) {
        SimPlayer nearest = null;
        float bestDist = Float.MAX_VALUE;
        for (SimPlayer p : players.values()) {
            if (!p.isAlive()) continue;
            float dx = p.physics.x - kx, dy = p.physics.y - ky;
            float d = dx*dx + dy*dy;
            if (d < bestDist) { bestDist = d; nearest = p; }
        }
        if (nearest != null) nearest.addXp(xp);
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
                    if (en.takeDamage(SimPlayer.SHURIKEN_DAMAGE)) spawnLoot(en);
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
                    applyPickup(p, pu.pickupType);
                    break;
                }
            }
        }
    }

    /** Apply a collected pickup to a player — health, currency, or item to inventory. */
    private static void applyPickup(SimPlayer p, String type) {
        switch (type != null ? type : "") {
            case "coin"         -> p.inventory.addCurrency(1);
            case "health_potion"-> {
                // Try to use immediately if health not full; else add to inventory
                if (p.health < p.maxHealth) {
                    p.health = Math.min(p.maxHealth, p.health + 2);
                } else {
                    p.inventory.addItem("health_potion", 1);
                }
            }
            default -> {
                // Generic item — try to add to inventory
                if (ItemDatabase.get(type) != null) p.inventory.addItem(type, 1);
            }
        }
    }

    /**
     * Step all boss AI, boss→player damage, and player→boss combat.
     * Mirrors Python entities/boss.py Boss.update().
     */
    private void stepBosses() {
        if (bosses.isEmpty()) return;

        // Nearest alive player
        float nearestX = 0, nearestY = 0, nearestDist = Float.MAX_VALUE;
        SimPlayer nearestPlayer = null;
        for (SimPlayer p : players.values()) {
            if (!p.isAlive()) continue;
            float cx = p.physics.x + p.physics.width  * 0.5f;
            float cy = p.physics.y + p.physics.height * 0.5f;
            // Boss starts in intro at room centre — use first alive player as anchor
            if (nearestPlayer == null) { nearestX = cx; nearestY = cy; nearestPlayer = p; nearestDist = 0; }
            for (SimBoss boss : bosses) {
                float bx = boss.physics.x + boss.physics.width  * 0.5f;
                float by = boss.physics.y + boss.physics.height * 0.5f;
                float dx = cx - bx, dy = cy - by;
                float d  = (float) Math.sqrt(dx*dx + dy*dy);
                if (d < nearestDist) { nearestDist = d; nearestX = cx; nearestY = cy; nearestPlayer = p; }
            }
        }

        for (SimBoss boss : bosses) {
            if (!boss.isAlive()) continue;

            float bx = boss.physics.x + boss.physics.width  * 0.5f;
            float by = boss.physics.y + boss.physics.height * 0.5f;
            float dx = nearestPlayer != null ? (nearestX - bx) : 0;
            float dy = nearestPlayer != null ? (nearestY - by) : 0;
            float dist = (float) Math.sqrt(dx*dx + dy*dy);

            boss.step(DT, nearestX, nearestY, dist);

            // Gravity (bosses fall like enemies — no flying)
            boss.physics.vy = Math.min(boss.physics.vy + 0.4f, 12f);
            boss.physics.y += boss.physics.vy;
            boss.physics.x += boss.physics.vx;

            // Simple floor clamp — full collision would be expensive for a solo boss;
            // the spatial hash check ensures they don't fall through solid floors.
            var tiles = spatialHash.candidates(boss.physics.x, boss.physics.y,
                                               boss.physics.width, boss.physics.height);
            for (var tile : tiles) {
                if (!tile.isPlatform() && tile.overlaps(boss.physics.x, boss.physics.y,
                                                        boss.physics.width, boss.physics.height)) {
                    // Push up until not overlapping
                    boss.physics.y = tile.y() - boss.physics.height;
                    boss.physics.vy = 0;
                    break;
                }
            }

            // ── Boss → player damage (melee active window) ────────────────────
            if (boss.isMeleeActive() && nearestPlayer != null) {
                float px = nearestPlayer.physics.x, py = nearestPlayer.physics.y;
                float pw = nearestPlayer.physics.width, ph = nearestPlayer.physics.height;
                if (aabbOverlap(boss.physics.x, boss.physics.y, boss.physics.width, boss.physics.height,
                                px, py, pw, ph)) {
                    nearestPlayer.takeDamage(boss.type.baseDamage);
                }
            }

            // ── Player melee → boss ───────────────────────────────────────────
            for (SimPlayer sp : players.values()) {
                if (!sp.isAlive() || !sp.isAttacking) continue;
                float cx2   = sp.physics.x + sp.physics.width  * 0.5f;
                float cy2   = sp.physics.y + sp.physics.height * 0.5f;
                float reach = SimPlayer.MELEE_REACH;
                float halfH = SimPlayer.MELEE_HEIGHT * 0.5f;
                float hbX   = sp.facing >= 0 ? cx2 : cx2 - reach;
                float hbY   = cy2 - halfH;
                if (aabbOverlap(hbX, hbY, reach, SimPlayer.MELEE_HEIGHT,
                                boss.physics.x, boss.physics.y, boss.physics.width, boss.physics.height)) {
                    if (boss.takeDamage(SimPlayer.MELEE_DAMAGE)) spawnBossLoot(boss);
                }
            }

            // ── Shuriken → boss ───────────────────────────────────────────────
            for (SimShuriken s : shurikens) {
                if (!s.alive || s.stuck) continue;
                if (aabbOverlap(s.x, s.y, SimShuriken.W, SimShuriken.H,
                                boss.physics.x, boss.physics.y, boss.physics.width, boss.physics.height)) {
                    if (boss.takeDamage(SimPlayer.SHURIKEN_DAMAGE)) spawnBossLoot(boss);
                    s.stuck      = true;
                    s.stuckTimer = 0.1f;
                }
            }
        }
    }

    /**
     * Step all NPC patrol + face-player logic (Python: NPC.update).
     * Finds the nearest alive player's centre-X and passes it to each NPC.
     */
    private void stepNpcs() {
        if (npcs.isEmpty()) return;

        // Find centre-X of the nearest alive player (Float.NaN if none)
        float nearestX = Float.NaN;
        float nearestDist = Float.MAX_VALUE;
        for (SimPlayer p : players.values()) {
            if (!p.isAlive()) continue;
            float cx = p.physics.x + p.physics.width * 0.5f;
            for (SimNPC npc : npcs) {
                float d = Math.abs(cx - (npc.x + npc.width * 0.5f));
                if (d < nearestDist) { nearestDist = d; nearestX = cx; }
            }
        }

        for (SimNPC npc : npcs) npc.step(nearestX);
    }

    // ── Inventory wire helper ─────────────────────────────────────────────────

    private static com.indieniinja.network.InventoryState buildInventoryState(SimInventory inv) {
        com.indieniinja.network.InventoryState s = new com.indieniinja.network.InventoryState();
        s.currency      = inv.currency;
        s.equippedWeapon = inv.equippedWeapon;
        s.equippedArmor  = inv.equippedArmor;
        for (SimInventory.Slot slot : inv.slots) {
            if (slot != null) {
                s.slots.add(new com.indieniinja.network.InventoryState.SlotState(
                    slot.itemId(), slot.quantity(), slot.equipped()));
            } else {
                s.slots.add(null);
            }
        }
        return s;
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
        // Arcade difficulty: +1 HP and +5% speed per 3 depth levels
        int   hpBonus   = (gameMode == GameMode.ARCADE && arcadeDepth > 0) ? arcadeDepth / 3 : 0;
        float speedMult = (gameMode == GameMode.ARCADE && arcadeDepth > 0) ? 1f + (arcadeDepth / 3) * 0.05f : 1f;
        // Stats from Python ENEMY_DEFINITIONS (entities/enemy.py)
        return switch (spec.type()) {
            case "goblin"   -> new SimEnemy(hubId+"_goblin_"+idx,   "goblin",   spec.x(), spec.y(), 32, 48, 3+hpBonus, 1, 72f *speedMult, 200f, 32f, spec.patrolMinX(), spec.patrolMaxX(), false);
            case "bat"      -> new SimEnemy(hubId+"_bat_"+idx,      "bat",      spec.x(), spec.y(), 28, 28, 2+hpBonus, 1, 90f *speedMult, 180f, 28f, spec.patrolMinX(), spec.patrolMaxX(), true);
            case "slime"    -> new SimEnemy(hubId+"_slime_"+idx,    "slime",    spec.x(), spec.y(), 40, 32, 4+hpBonus, 2, 60f *speedMult, 160f, 40f, spec.patrolMinX(), spec.patrolMaxX(), false);
            case "skeleton" -> new SimEnemy(hubId+"_skeleton_"+idx, "skeleton", spec.x(), spec.y(), 32, 56, 3+hpBonus, 1, 60f *speedMult, 200f, 64f, spec.patrolMinX(), spec.patrolMaxX(), false);
            case "wolf"     -> new SimEnemy(hubId+"_wolf_"+idx,     "wolf",     spec.x(), spec.y(), 48, 32, 3+hpBonus, 2, 90f *speedMult, 220f, 48f, spec.patrolMinX(), spec.patrolMaxX(), false);
            default         -> new SimEnemy(hubId+"_enemy_"+idx,    spec.type(),spec.x(), spec.y(), 32, 48, 3+hpBonus, 1, 72f *speedMult, 200f, 32f, spec.patrolMinX(), spec.patrolMaxX(), false);
        };
    }

    // ── Accessors (for testing) ───────────────────────────────────────────────

    public Map<Integer, SimPlayer> getPlayers()  { return java.util.Collections.unmodifiableMap(players); }
    public List<SimEnemy>          getEnemies()  { return java.util.Collections.unmodifiableList(enemies); }
    public List<SimPickup>         getPickups()  { return java.util.Collections.unmodifiableList(pickups); }

    /**
     * Hot-swap the spatial hash used for collision resolution.
     * Called when the player crosses a room boundary so the new room's
     * tiles (plus its neighbors) become collidable.
     */
    public void updateSpatialHash(com.indieniinja.physics.SpatialHash hash) {
        this.spatialHash = hash;
        collisionSystem.setSpatialHash(hash);
    }
}
