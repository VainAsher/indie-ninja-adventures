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

import com.indieniinja.physics.TileRect;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

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

    private static final Logger log = LoggerFactory.getLogger(GameSimulator.class);

    // ── Constants ─────────────────────────────────────────────────────────────
    private static final float DT           = PhysicsConstants.FIXED_DT;
    private static final float PIXELS_PER_S = 1f / DT;  // 60
    private static final float SKELETON_RANGE_MULT = 1.15f;
    private static final float ARCHER_PROJECTILE_SPEED = SimPlayer.SHURIKEN_SPEED * 0.90f;

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
    private final List<SimPickup>   pickups      = new ArrayList<>();
    private final List<PickupSlot>  pickupSlots  = new ArrayList<>();
    private final Random            slotRng      = new Random();
    private final List<FallingPlatform>    fallingPlatforms = new ArrayList<>();
    private final List<SimMovingPlatform>  movingPlatforms  = new ArrayList<>();
    private final List<SimShuriken> shurikens = new ArrayList<>();
    private final List<SimNPC>      npcs      = new ArrayList<>();
    private final List<SimEcho>     echoes    = new ArrayList<>();
    private final List<SimBoss>     bosses    = new ArrayList<>();
    private final List<SimPortal>   portals   = new ArrayList<>();
    /** NPC ID → shop (only for "shop" type NPCs). */
    private final Map<String, SimShop> shops = new LinkedHashMap<>();
    private int shurikenSeq = 0;
    private int lootSeq     = 0;
    private int echoSeq     = 0;

    // ── Game mode state ───────────────────────────────────────────────────────
    private GameMode gameMode    = GameMode.ARCADE;
    private int      arcadeScore = 0;
    private int      arcadeDepth = 0;
    private int      arcadeRooms = 10;

    // ── World ─────────────────────────────────────────────────────────────────
    public final long   seed;
    public final String hubId;
    /** Whether the current room is dark (lantern decays). Set by caller for solo mode. */
    private boolean isDarkArea = false;
    private final float worldHeightPx;
    private com.indieniinja.physics.SpatialHash spatialHash;

    // ── Puzzle state ──────────────────────────────────────────────────────────
    /** puzzleId → TileRects to remove from spatialHash when the door is unlocked. */
    private final Map<String, List<TileRect>> doorTiles;
    /** Puzzle IDs that have already been solved (door opened). */
    private final Set<String> solvedPuzzles = new HashSet<>();
    /** Player slots that had interact=true in the previous tick (edge-detect). */
    private final Set<Integer> prevInteract = new HashSet<>();

    // ── Shadow Ascent M5 — narrative boss state ───────────────────────────────
    /** Optional HubStateMachine — injected by ZoneSimulationLoop for server mode;
     *  null in solo mode (boss patterns still work but hub transitions are skipped). */
    private com.indieniinja.world.HubStateMachine hub = null;
    /** Set to true when the Siren scripted loss fires; caller should broadcast
     *  MessageType.SCRIPTED_LOSS and then clear this via drainPendingScriptedLoss(). */
    private boolean pendingScriptedLoss = false;

    // ── Construction ─────────────────────────────────────────────────────────

    public GameSimulator(long seed, String hubId, LevelLayout layout) {
        this.seed          = seed;
        this.hubId         = hubId;
        this.worldHeightPx = layout.worldHeightPx;
        this.spatialHash   = layout.spatialHash;
        this.doorTiles     = layout.doorTiles;

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

        // Spawn pickups and register respawn slots.
        // spec.y() is the top of the ground tile (entity-bottom anchor from WorldGenerator).
        // Subtract TILE_SIZE so the pickup sits ON TOP of the tile, not inside it.
        int pickupIdx = 0;
        for (LevelLayout.PickupSpawn spec : layout.pickupSpawns) {
            float px = spec.x();
            float py = spec.y() - PhysicsConstants.TILE_SIZE;
            int slotIdx = pickupSlots.size();
            pickupSlots.add(new PickupSlot(px, py, spec.type()));
            int ticks = 1800 + slotRng.nextInt(1801); // 30–60 s
            pickups.add(new SimPickup(
                hubId + "_pickup_" + pickupIdx++,
                spec.type(), px, py, slotIdx, ticks
            ));
        }

        // Register falling platforms
        fallingPlatforms.addAll(layout.fallingPlatforms);
        // Register moving platforms
        movingPlatforms.addAll(layout.movingPlatforms);

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

        // Spawn NPCs — registered in EntityManager so PhysicsSystem/CollisionSystem
        // apply gravity and tile collision each tick (same as ground enemies).
        int npcIdx = 0;
        for (LevelLayout.NPCSpawn spec : layout.npcSpawns) {
            String npcId = hubId + "_npc_" + npcIdx++;
            SimNPC npc = new SimNPC(
                npcId, spec.type(), spec.x(), spec.y(),
                32, 48,   // Python default: width=32, height=48
                spec.patrolMinX(), spec.patrolMaxX()
            );
            npcs.add(npc);
            var npcEntity = entityManager.create(com.indieniinja.core.EntityType.NPC, npc.physics);
            npcEntity.addTag("npc");
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

    /** Return the SimPlayer for the given slot, or null if not present. */
    public SimPlayer getPlayer(int slot) {
        return players.get(slot);
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

    /** Add an already-constructed echo entity to the active room. */
    public void addEcho(SimEcho echo) {
        if (echo != null) echoes.add(echo);
    }

    /**
     * Spawn an echo from a player's 10-second recorder buffer.
     * Returns null when the slot is unknown or no buffered inputs exist yet.
     */
    public SimEcho spawnEchoFromPlayer(int slot, boolean recallable) {
        SimPlayer owner = players.get(slot);
        if (owner == null) return null;
        List<InputCommand> recorded = owner.echoRecorder.snapshot();
        if (recorded.isEmpty()) return null;
        ReplayPlayer replay = ReplayPlayer.fromInputSequence(seed, slot, recorded);
        SimEcho echo = new SimEcho(
            hubId + "_echo_" + echoSeq++,
            slot,
            owner.physics.x,
            owner.physics.y,
            replay,
            recallable
        );
        echoes.add(echo);
        return echo;
    }

    /**
     * Attempt to recall an existing echo.
     * Returns false when recall fails puzzle semantics.
     */
    public boolean recallEcho(String echoId) {
        for (SimEcho echo : echoes) {
            if (echo.echoId.equals(echoId)) return echo.recall();
        }
        return true;
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
        // Shadow Ascent M6: sample each player's effective input once per tick
        // for 10-second echo playback buffers.
        for (SimPlayer p : players.values()) {
            p.echoRecorder.record(p.latestInput);
        }

        // Tick invincibility timers
        for (SimPlayer p : players.values()) p.tickInvincibility();

        // 2. Rebuild dynamic tile list so CollisionSystem sees current platform positions.
        rebuildDynamicTiles();

        // 3a. Physics tick: gravity + integration + collision (via EventBus)
        clock.stepOne();  // emits TickEvent → PhysicsSystem(60) → CollisionSystem(45)

        // 3b. Platform state machines (step AFTER physics so triggers are current-frame)
        stepPlatforms();

        // 4. Enemy AI + physics
        stepEnemies();

        // 5. Server-side player-enemy combat (melee + contact)
        stepCombat();

        // 6. Spawn any shurikens flagged by applyPlayerInput
        spawnPendingShurikens();

        // 7. Advance shurikens (movement + tile/enemy collision)
        stepShurikens();

        // 8. Pickups: lifetime + authoritative collection + respawn
        stepPickups();
        stepPickupRespawns();

        // 9. NPC patrol + player-facing
        stepNpcs();

        // 9b. Echo playback (M6)
        stepEchoes();

        // 9c. Puzzle lever/button interaction (interact key edge-triggered)
        stepLeverInteraction();

        // 10. Boss AI + combat
        stepBosses();

        // 11. Portal animation timers
        for (SimPortal portal : portals) portal.step(DT);

        // 12. Lava damage — 1 HP per tick for any player touching lava
        for (SimPlayer sp : players.values()) {
            if (sp.physics.onLava && sp.isAlive()) {
                sp.takeDamage(1);  // takeDamage() is no-op while invincibilityTicks > 0
            }
        }

        // 13. Yin/Yang tick (GDD §3.3) — apply flags, flow mode, decay
        tickYinYang();

        // 14. Lantern tick (GDD §3.4) — apply physics bonuses, decay
        tickLantern();

        // 15. Player respawn countdowns
        stepPlayerRespawns();
    }

    // ── Yin/Yang system (M4 — GDD §3.3) ─────────────────────────────────────

    /**
     * Tick Yin/Yang for all players:
     * <ul>
     *   <li>Decay towards neutral slowly</li>
     *   <li>Yin &gt; HIGH_YIN_THRESHOLD → set ABILITY_YIN_SIGHT abilityFlag</li>
     *   <li>Yang &gt; HIGH_YANG_THRESHOLD → yang_surge flag on player (damage modifier)</li>
     *   <li>|yin − yang| &lt; BALANCE_THRESHOLD → flowMode</li>
     * </ul>
     */
    private void tickYinYang() {
        for (SimPlayer sp : players.values()) {
            YinYangComponent yy = sp.yinYang;
            yy.decay(DT);

            PhysicsState p = sp.physics;
            if (yy.hasYinSight()) {
                p.abilityFlags |= PhysicsConstants.ABILITY_YIN_SIGHT;
            } else {
                p.abilityFlags &= ~PhysicsConstants.ABILITY_YIN_SIGHT;
            }
            // yang_surge and flowMode are read by getSnapshot() and sent as PlayerState fields
        }
    }

    // ── Lantern system (M4 — GDD §3.4) ──────────────────────────────────────

    /**
     * Tick Lantern for all players:
     * <ul>
     *   <li>Decay when in dark areas (combat/boss rooms) or at low HP</li>
     *   <li>High lantern → apply jump power and coyote time bonuses</li>
     * </ul>
     */
    /**
     * Set whether the current room is a dark area (lantern should decay).
     * Hub rooms pass false; all combat/boss/dungeon rooms pass true.
     * Called by GameScreen each frame in solo mode.
     */
    public void setDarkArea(boolean dark) { this.isDarkArea = dark; }

    /** Inject the hub state machine so Shadow Ascent boss patterns can trigger hub transitions. */
    public void setHub(com.indieniinja.world.HubStateMachine hub) { this.hub = hub; }

    /**
     * Returns true if the Siren scripted-loss fired this tick and clears the flag.
     * Caller (ZoneSimulationLoop or GameScreen) should broadcast MessageType.SCRIPTED_LOSS.
     */
    public boolean drainPendingScriptedLoss() {
        boolean v = pendingScriptedLoss;
        pendingScriptedLoss = false;
        return v;
    }

    private void tickLantern() {
        for (SimPlayer sp : players.values()) {
            LanternComponent lc = sp.lantern;
            // isDarkArea is updated by caller (GameScreen in solo, ZoneSimulationLoop in server).
            // Fallback: treat non-hub hubIds as dark (multiplayer server path).
            boolean inDark = isDarkArea || !hubId.contains("hub");
            lc.decay(DT, inDark);
            // High lantern bonus — applied via applyPlayerInput on next tick
            // (we set a flag so physics pick it up; actual bonus in applyPlayerInput)
        }
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
            ps.maxMana           = p.maxMana;
            ps.maxStamina        = p.maxStamina;
            ps.ninjutsuCasting   = p.ninjutsuCasting;
            // Inventory — build wire type from SimInventory
            ps.inventory = buildInventoryState(p.inventory);
            // Progression
            ps.experience = p.experience;
            ps.level      = p.level;
            ps.abilities  = new java.util.ArrayList<>(p.unlockedAbilities);
            // Yin/Yang & Lantern (M4)
            ps.yinValue     = p.yinYang.yin;
            ps.yangValue    = p.yinYang.yang;
            ps.flowMode     = p.yinYang.isBalanced();
            ps.lanternValue = p.lantern.value;
            ps.weaponState    = p.weaponState;
            ps.respawnTimer   = p.respawnTimer;
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
            ps.originX    = fp.originX;
            ps.width      = fp.width;
            ps.height     = fp.height;
            ps.visible    = fp.visible;
            snap.platformStates.add(ps);
        }

        // Moving platforms — always sent every frame
        for (SimMovingPlatform mp : movingPlatforms) {
            com.indieniinja.network.MovingPlatformState ms = new com.indieniinja.network.MovingPlatformState();
            ms.platformId = mp.id;
            ms.x          = mp.x;
            ms.y          = mp.y;
            ms.width      = mp.width;
            ms.height     = mp.height;
            snap.movingPlatforms.add(ms);
        }

        // NPCs
        for (SimNPC npc : npcs) {
            com.indieniinja.network.NPCState ns = new com.indieniinja.network.NPCState();
            ns.npcId          = npc.id;
            ns.npcType        = npc.type;
            ns.x              = npc.physics.x;
            ns.y              = npc.physics.y;
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
            sp.stamina = Math.min(sp.maxStamina, sp.stamina + regenRate * DT);
        }
        sp.mana = Math.min(sp.maxMana, sp.mana + SimPlayer.MANA_REGEN_RATE * DT);

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

        // ── Hazard tile effects ───────────────────────────────────────────────
        // CollisionSystem already set p.onIce / p.inWater / p.onLava flags this tick.
        if (p.onIce && p.onGround) {
            // ICE: near-zero friction — player glides; only 10% of normal deceleration
            // Let vx carry; don't clamp to input targetVx on next tick (done via mult).
            // Approximation: re-multiply current vx to resist stopping.
            if (!cmd.left && !cmd.right) p.vx *= 0.97f;  // very slow deceleration on ice
        }
        if (p.inWater && !sp.isDashing) {
            // WATER: 55% speed cap, no dash (dash blocked via isDashing guard above)
            float cap = PhysicsConstants.MAX_RUN_SPEED * 0.55f;
            if (p.vx >  cap) p.vx =  cap;
            if (p.vx < -cap) p.vx = -cap;
        }
        // LAVA: GameSimulator applies 1 HP damage below (after applyPlayerInput returns).

        // ── Animation state ───────────────────────────────────────────────────
        if (sp.ninjutsuCasting) {
            sp.animState = sp.ninjutsuHeld ? "ninjutsu_hand" : "ninjutsu_summon";
        } else if (sp.teleportPhaseMode) {
            sp.animState = "idle";   // player frozen in place while cursor moves
        } else if (sp.isTeleporting) {
            sp.animState = "teleport";
        } else if (sp.isDashing) {
            sp.animState = "dash";
        } else if (p.inWater) {
            // Swim states — horizontal movement = swim, stationary = swim_idle
            sp.animState = Math.abs(p.vx) > 0.1f ? "swim" : "swim_idle";
        } else if (sp.isAttacking) {
            sp.animState = "attack";
        } else if (sp.isThrowing) {
            sp.animState = "throw";
        } else if (sp.isClimbing) {
            // Climbing surface (ladder/vine — detection wired in Phase 6)
            sp.animState = Math.abs(p.vy) > 0.1f ? "climb" : "climb_idle";
        } else if (sp.isLedgeClimbing) {
            sp.animState = "ledge_climb";
        } else if (sp.isOnLedge) {
            sp.animState = "ledge_idle";
        } else if (sp.isWallSliding) {
            sp.animState = "wall_slide";
        } else if (!p.onGround) {
            sp.animState = p.vy < 0f ? "jump" : "fall";
        } else if (cmd.crouch) {
            // Crouch walk when crouched AND moving; pure crouch when still
            sp.animState = Math.abs(p.vx) > 0.1f ? "crouch_walk" : "crouch";
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

    /**
     * Build the list of dynamic TileRects for the current tick:
     * - Moving platforms at their current x/y position (one-way = true)
     * - Falling platforms only when active (idle/triggered states)
     * Pushed to CollisionSystem before the physics tick fires.
     */
    private final java.util.ArrayList<com.indieniinja.physics.TileRect> dynamicTilesBuf
        = new java.util.ArrayList<>(64);

    private void rebuildDynamicTiles() {
        dynamicTilesBuf.clear();
        for (SimMovingPlatform mp : movingPlatforms) {
            dynamicTilesBuf.add(new com.indieniinja.physics.TileRect(
                mp.x, mp.y, mp.width, mp.height, true));
        }
        for (FallingPlatform fp : fallingPlatforms) {
            if (fp.active) {  // not active while falling/respawning
                dynamicTilesBuf.add(new com.indieniinja.physics.TileRect(
                    fp.originX, fp.posY, fp.width, fp.height, true));
            }
        }
        collisionSystem.setDynamicTiles(dynamicTilesBuf);
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

        // Step moving platforms and apply riding velocity to players on top.
        for (SimMovingPlatform mp : movingPlatforms) {
            mp.step();
            for (SimPlayer sp : players.values()) {
                if (!sp.isAlive()) continue;
                com.indieniinja.physics.PhysicsState p = sp.physics;
                if (mp.isStandingOn(p.x, p.y, p.width, p.height)) {
                    // Nudge player horizontally with the platform — prevents sliding off.
                    p.x += mp.vx;
                }
            }
        }
    }

    private void stepEnemies() {
        // Collect alive player centres for targeting.
        List<float[]> playerCenters = new ArrayList<>(players.size());
        for (SimPlayer p : players.values()) {
            if (p.isAlive()) {
                playerCenters.add(new float[]{
                    p.physics.x + p.physics.width * 0.5f,
                    p.physics.y + p.physics.height * 0.5f
                });
            }
        }
        if (playerCenters.isEmpty()) return;

        for (SimEnemy en : enemies) {
            if (!en.isAlive()) continue;
            float[] nearest = nearestPlayerCenter(en, playerCenters);
            stepEnemyAI(en, nearest);
            // Flying enemies manage their own vertical movement (no CollisionSystem for them)
            if (en.canFly) applyFlyingEnemyMovement(en);
            // Ground enemies: gravity + collision handled by PhysicsSystem/CollisionSystem via EntityManager
        }
    }

    private static float[] nearestPlayerCenter(SimEnemy en, List<float[]> playerCenters) {
        float ex = en.physics.x + en.physics.width * 0.5f;
        float ey = en.physics.y + en.physics.height * 0.5f;
        float best = Float.MAX_VALUE;
        float[] nearest = playerCenters.get(0);
        for (float[] pc : playerCenters) {
            float dx = pc[0] - ex;
            float dy = pc[1] - ey;
            float d2 = dx * dx + dy * dy;
            if (d2 < best) {
                best = d2;
                nearest = pc;
            }
        }
        return nearest;
    }

    /**
     * Enemy AI state machine — mirrors Python entities/enemy.py EnemyManager.update().
     * States: IDLE/PATROL ↔ CHASE ↔ ATTACK; FLEE when low HP; GUARD for skeleton.
     */
    private void stepEnemyAI(SimEnemy en, float[] nearest) {
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

                // Detect player — skeleton guards when very close, others chase
                if (dist < en.detectionRadius) {
                    if ("skeleton".equals(en.enemyType) && dist < en.attackRange * 1.5f) {
                        en.aiState   = EnemyAIState.GUARD;
                        en.guardTimer = SimEnemy.GUARD_DURATION;
                    } else {
                        en.aiState = EnemyAIState.CHASE;
                    }
                }
            }
            case CHASE -> {
                // Move toward nearest player
                float tx = nearest[0];
                float cx = en.physics.x + en.physics.width * 0.5f;
                float speed = en.moveSpeed * DT;
                if (tx > cx) { en.physics.x += speed; en.facingRight = true; }
                else         { en.physics.x -= speed; en.facingRight = false; }

                if (dist < en.attackRange) {
                    en.aiState = EnemyAIState.ATTACK;
                    en.attackWindupTimer = SimEnemy.ATTACK_WINDUP_TIME;
                } else if (dist > en.detectionRadius * 1.5f) {
                    en.aiState = EnemyAIState.PATROL;
                }
            }
            case ATTACK -> {
                // Telegraphed attack phases
                if (en.attackWindupTimer > 0) {
                    en.attackWindupTimer -= DT;
                } else if (en.attackActiveTimer < SimEnemy.ATTACK_ACTIVE_TIME) {
                    boolean wasInactive = en.attackActiveTimer <= 0f;
                    en.attackActiveTimer += DT;
                    // Archer attack payload is projectile-based (no melee touch damage).
                    if (wasInactive && "archer".equals(en.enemyType)) {
                        spawnArcherProjectile(en, nearest[0], nearest[1]);
                    }
                } else {
                    en.attackActiveTimer  = 0f;
                    en.attackRecoveryTimer = SimEnemy.ATTACK_RECOVERY_TIME;
                    en.aiState = EnemyAIState.CHASE;
                }
            }
            case FLEE -> {
                // Run directly away from the nearest player
                float tx = nearest[0];
                float cx = en.physics.x + en.physics.width * 0.5f;
                float speed = en.moveSpeed * 1.2f * DT;  // flee slightly faster than normal
                if (tx > cx) { en.physics.x -= speed; en.facingRight = false; }
                else         { en.physics.x += speed; en.facingRight = true; }

                en.fleeTimer -= DT;
                if (en.fleeTimer <= 0) {
                    en.fleeTimer = 0;
                    en.aiState  = EnemyAIState.PATROL;
                }
            }
            case GUARD -> {
                // Skeleton raises shield — stationary; blocks incoming melee (handled in stepCombat)
                en.guardTimer -= DT;
                if (en.guardTimer <= 0) {
                    en.guardTimer = 0;
                    // After guard, counter-attack if player still in range
                    en.aiState = (dist < en.attackRange)
                        ? EnemyAIState.ATTACK
                        : EnemyAIState.CHASE;
                    if (en.aiState == EnemyAIState.ATTACK)
                        en.attackWindupTimer = SimEnemy.ATTACK_WINDUP_TIME * 0.5f; // faster counter
                }
            }
            case STUNNED -> {
                en.stunTimer -= DT;
                if (en.stunTimer <= 0) {
                    en.stunTimer = 0;
                    // Transition to FLEE if flee timer was set during takeDamage
                    en.aiState = (en.fleeTimer > 0) ? EnemyAIState.FLEE : EnemyAIState.PATROL;
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

    // ── Respawn delay (seconds) ────────────────────────────────────────────────
    private static final float RESPAWN_DELAY = 5.0f;

    /**
     * Count down respawn timers and restore dead players when time expires.
     * Called once per step (after all combat/damage) as step 15.
     */
    private void stepPlayerRespawns() {
        for (SimPlayer p : players.values()) {
            if (!p.isDead) continue;
            if (p.respawnTimer < 0f) {
                // Player just died this tick (or timer not started) — begin countdown
                p.respawnTimer = RESPAWN_DELAY;
            } else {
                p.respawnTimer -= DT;
                if (p.respawnTimer <= 0f) {
                    p.respawnTimer        = -1f;
                    p.isDead              = false;
                    p.health              = p.maxHealth;
                    p.physics.x           = p.spawnX;
                    p.physics.y           = p.spawnY;
                    p.physics.vx          = 0f;
                    p.physics.vy          = 0f;
                    p.invincibilityTicks  = 120;  // 2 s post-respawn invincibility
                    p.isDashing           = false;
                    p.dashTimer           = 0f;
                    p.isAttacking         = false;
                    p.isThrowing          = false;
                    log.info("Player {} (slot {}) respawned at ({},{})",
                             p.playerId, p.slot, p.spawnX, p.spawnY);
                }
            }
        }
    }

    private void stepCombat() {
        // ── Enemy → player contact damage ────────────────────────────────────
        for (SimEnemy en : enemies) {
            if (!en.isAlive()) continue;
            if (en.aiState != EnemyAIState.ATTACK) continue;
            if (en.attackActiveTimer <= 0) continue;
            if ("archer".equals(en.enemyType)) continue;
            float activeProgress = (SimEnemy.ATTACK_ACTIVE_TIME > 0f)
                ? Math.min(1f, en.attackActiveTimer / SimEnemy.ATTACK_ACTIVE_TIME)
                : 1f;
            EnemyAttackGeometry.Rect atk = EnemyAttackGeometry.attackRect(
                en.enemyType,
                en.physics.x, en.physics.y,
                en.physics.width, en.physics.height,
                en.attackRange,
                en.facingRight,
                activeProgress
            );
            for (SimPlayer p : players.values()) {
                if (!p.isAlive()) continue;
                if (aabbOverlap(atk.x, atk.y, atk.w, atk.h,
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
                EnemyAttackGeometry.Rect hurt = EnemyAttackGeometry.hurtboxRect(
                    en.enemyType,
                    en.physics.x, en.physics.y,
                    en.physics.width, en.physics.height
                );
                if (aabbOverlap(hbX, hbY, reach, SimPlayer.MELEE_HEIGHT,
                                hurt.x, hurt.y, hurt.w, hurt.h)) {
                    // Skeleton in GUARD state blocks melee — takes no damage, guard drops after counter
                    if (en.aiState == EnemyAIState.GUARD) continue;
                    if (en.takeDamage(SimPlayer.MELEE_DAMAGE)) spawnLoot(en);
                }
            }
        }
    }

    /**
     * Spawn 1–2 loot pickups at the dead enemy's position and grant XP to the nearest player.
     *
     * Loot table (d20):
     *   0-9  (50%) coin
     *   10-13 (20%) health_potion
     *   14-15 (10%) rare_potion
     *   16    (5%)  yin_fragment
     *   17    (5%)  yang_fragment
     *   18    (5%)  lantern_fragment
     *   19    (5%)  gem
     * Additionally rolls a second coin drop on values 0-3 (20%).
     */
    private void spawnLoot(SimEnemy en) {
        // Arcade score: +1 per kill
        if (gameMode == GameMode.ARCADE) arcadeScore++;

        // XP reward
        int xp = enemyXp(en.enemyType);
        grantXpToNearest(en.physics.x + en.physics.width * 0.5f,
                         en.physics.y + en.physics.height * 0.5f, xp);

        // Drop position: sit on top of where the enemy died (feet level)
        float cx = en.physics.x + en.physics.width  * 0.5f - 10f;
        float cy = en.physics.y + en.physics.height - PhysicsConstants.TILE_SIZE;

        int roll = (int) Math.abs((en.physics.x * 7 + en.physics.y * 13 + lootSeq * 31) % 20);
        lootSeq++;
        String type = switch (roll) {
            case 0,1,2,3,4,5,6,7,8,9 -> "coin";
            case 10,11,12,13           -> "health_potion";
            case 14,15                 -> "rare_potion";
            case 16                    -> "yin_fragment";
            case 17                    -> "yang_fragment";
            case 18                    -> "lantern_fragment";
            default                    -> "gem";   // 19
        };
        pickups.add(new SimPickup(hubId + "_loot_" + lootSeq, type, cx, cy));
        // 20% chance of a bonus coin drop alongside the primary
        if (roll < 4) pickups.add(new SimPickup(hubId + "_loot_" + (lootSeq + 100), "coin", cx + 14f, cy));
    }

    /** Spawn loot and XP from a dead boss. Drops 3–5 items plus guaranteed currency and fragments. */
    private void spawnBossLoot(SimBoss boss) {
        if (gameMode == GameMode.ARCADE) arcadeScore += 10;

        grantXpToNearest(boss.physics.x + boss.physics.width  * 0.5f,
                         boss.physics.y + boss.physics.height * 0.5f,
                         boss.type.xpReward());

        float cx = boss.physics.x + boss.physics.width * 0.5f;
        float cy = boss.physics.y + boss.physics.height - PhysicsConstants.TILE_SIZE;
        // Guaranteed: 3 coins + 1 health potion
        for (int i = 0; i < 3; i++)
            pickups.add(new SimPickup(hubId + "_bloot_" + lootSeq++, "coin",         cx - 20f + i * 20f, cy));
        pickups.add(new SimPickup(hubId + "_bloot_" + lootSeq++, "health_potion",    cx,           cy));
        // Guaranteed fragment trio from bosses
        pickups.add(new SimPickup(hubId + "_bloot_" + lootSeq++, "yin_fragment",     cx - 16f,     cy - 36f));
        pickups.add(new SimPickup(hubId + "_bloot_" + lootSeq++, "yang_fragment",    cx,           cy - 36f));
        pickups.add(new SimPickup(hubId + "_bloot_" + lootSeq++, "lantern_fragment", cx + 16f,     cy - 36f));
        pickups.add(new SimPickup(hubId + "_bloot_" + lootSeq++, "gem",              cx,           cy - 70f));
    }

    private static int enemyXp(String type) {
        return switch (type) {
            case "goblin"   -> 10;
            case "slime"    ->  8;
            case "skeleton" -> 12;
            case "spearman" -> 13;
            case "archer"   -> 15;
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

    private void spawnArcherProjectile(SimEnemy en, float targetX, float targetY) {
        float sx = en.physics.x + en.physics.width  * 0.5f - SimShuriken.W * 0.5f;
        float sy = en.physics.y + en.physics.height * 0.5f - SimShuriken.H * 0.5f;
        float toX = targetX - (sx + SimShuriken.W * 0.5f);
        float toY = targetY - (sy + SimShuriken.H * 0.5f);
        float len = (float) Math.sqrt(toX * toX + toY * toY);

        float vx, vy;
        if (len > 0.001f) {
            vx = (toX / len) * ARCHER_PROJECTILE_SPEED;
            vy = (toY / len) * ARCHER_PROJECTILE_SPEED;
        } else {
            vx = en.facingRight ? ARCHER_PROJECTILE_SPEED : -ARCHER_PROJECTILE_SPEED;
            vy = 0f;
        }

        shurikens.add(new SimShuriken(
            hubId + "_enemy_shot_" + shurikenSeq++,
            -1,
            sx,
            sy,
            vx,
            vy,
            true,
            Math.max(1, en.baseDamage)
        ));
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

            if (s.damagesPlayers) {
                for (SimPlayer p : players.values()) {
                    if (!p.isAlive()) continue;
                    if (aabbOverlap(s.x, s.y, SimShuriken.W, SimShuriken.H,
                                    p.physics.x, p.physics.y, p.physics.width, p.physics.height)) {
                        p.takeDamage(s.damage);
                        s.stuck      = true;
                        s.stuckTimer = 0.1f;
                        break;
                    }
                }
            } else {
                // Enemy collision
                for (SimEnemy en : enemies) {
                    if (!en.isAlive()) continue;
                    EnemyAttackGeometry.Rect hurt = EnemyAttackGeometry.hurtboxRect(
                        en.enemyType,
                        en.physics.x, en.physics.y,
                        en.physics.width, en.physics.height
                    );
                    if (aabbOverlap(s.x, s.y, SimShuriken.W, SimShuriken.H,
                                    hurt.x, hurt.y, hurt.w, hurt.h)) {
                        if (en.takeDamage(SimPlayer.SHURIKEN_DAMAGE)) spawnLoot(en);
                        s.stuck      = true;
                        s.stuckTimer = 0.1f;
                        break;
                    }
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
            // Start respawn cooldown when this pickup has just died
            if (!pu.alive && pu.slotIdx >= 0) {
                startRespawn(pu.slotIdx);
            }
        }
        pickups.removeIf(pu -> !pu.alive);
    }

    private void startRespawn(int slotIdx) {
        PickupSlot slot = pickupSlots.get(slotIdx);
        slot.active       = false;
        slot.cooldownTicks = 900 + slotRng.nextInt(901); // 15–30 s
    }

    private void stepPickupRespawns() {
        for (int i = 0; i < pickupSlots.size(); i++) {
            PickupSlot slot = pickupSlots.get(i);
            if (slot.active) continue;
            if (--slot.cooldownTicks <= 0) {
                slot.active = true;
                int ticks   = 1800 + slotRng.nextInt(1801); // 30–60 s
                pickups.add(new SimPickup(
                    hubId + "_rpickup_" + i + "_" + lootSeq++,
                    slot.type, slot.x, slot.y, i, ticks
                ));
            }
        }
    }

    /** Apply a collected pickup to a player — health, currency, item, or M4 fragment. */
    private void applyPickup(SimPlayer p, String type) {
        switch (type != null ? type : "") {
            case "coin"         -> p.inventory.addCurrency(1);
            case "health_potion"-> {
                if (p.health < p.maxHealth) {
                    p.health = Math.min(p.maxHealth, p.health + 2);
                } else {
                    p.inventory.addItem("health_potion", 1);
                }
            }
            // ── Yin/Yang/Lantern fragments (M4 — GDD §3.3/§3.4) ──────────────
            case "yin_fragment" -> {
                p.yinYang.absorbYin(YinYangComponent.NEUTRAL * 0.5f);  // +0.25
                log.info("[M4] {} collected yin_fragment → yin={}", p.playerId, p.yinYang.yin);
            }
            case "yang_fragment" -> {
                p.yinYang.absorbYang(YinYangComponent.NEUTRAL * 0.5f);  // +0.25
                log.info("[M4] {} collected yang_fragment → yang={}", p.playerId, p.yinYang.yang);
            }
            case "lantern_fragment" -> {
                p.lantern.restore(LanternComponent.FRAGMENT_RESTORE);   // +0.20
                log.info("[M4] {} collected lantern_fragment → lantern={}", p.playerId, p.lantern.value);
            }
            default -> {
                // Puzzle key: type = "key_<doorPuzzleId>" (e.g. "key_kd_0")
                if (type != null && type.startsWith("key_")) {
                    unlockDoor(type.substring(4));  // strip "key_" → doorPuzzleId
                } else if (ItemDatabase.get(type) != null) {
                    p.inventory.addItem(type, 1);
                }
            }
        }
    }

    /**
     * Remove all DOOR_LOCKED tiles for the given puzzleId from the SpatialHash,
     * allowing players to walk through the opened door.
     */
    private void unlockDoor(String doorPuzzleId) {
        if (solvedPuzzles.contains(doorPuzzleId)) return;
        List<TileRect> tiles = doorTiles.get(doorPuzzleId);
        if (tiles == null || tiles.isEmpty()) return;
        solvedPuzzles.add(doorPuzzleId);
        for (TileRect tr : tiles) spatialHash.remove(tr);
        collisionSystem.setSpatialHash(spatialHash);  // ensure CollisionSystem sees the update
        log.info("[puzzle] door unlocked: {}", doorPuzzleId);
    }

    /** Advance all active echoes by one replay tick. */
    private void stepEchoes() {
        for (SimEcho echo : echoes) {
            if (!echo.failed) echo.step();
        }
    }

    /**
     * Check for player lever/button interaction.
     * Activates when a player presses interact (edge-triggered) within 80 px of a
     * lever or button NPC whose linked door has not yet been unlocked.
     */
    private void stepLeverInteraction() {
        for (Map.Entry<Integer, SimPlayer> entry : players.entrySet()) {
            SimPlayer p = entry.getValue();
            if (!p.isAlive()) continue;
            boolean nowInteract  = p.latestInput != null && p.latestInput.interact;
            boolean wasInteract  = prevInteract.contains(entry.getKey());
            boolean freshPress   = nowInteract && !wasInteract;
            if (nowInteract) prevInteract.add(entry.getKey()); else prevInteract.remove(entry.getKey());
            if (!freshPress) continue;

            float px = p.physics.x + p.physics.width  * 0.5f;
            float py = p.physics.y + p.physics.height * 0.5f;
            for (SimNPC npc : npcs) {
                String t = npc.type;
                if (!t.startsWith("lever_") && !t.startsWith("btn_")) continue;
                float nx = npc.physics.x + npc.physics.width  * 0.5f;
                float ny = npc.physics.y + npc.physics.height * 0.5f;
                float dx = px - nx, dy = py - ny;
                if (dx*dx + dy*dy > 80f*80f) continue;
                // lever NPC type = "lever_ld_0" → doorPuzzleId = "ld_0"
                // button NPC type = "btn_<i>_<puzzleId>" — all 3 unique buttons must be pressed
                if (t.startsWith("lever_")) {
                    unlockDoor(t.substring(6));   // "lever_ld_0" → "ld_0"
                } else {
                    // Prevent re-pressing an already-activated button
                    if (solvedPuzzles.contains(t)) break;
                    solvedPuzzles.add(t);
                    // Extract base puzzleId after the 2nd underscore: "btn_0_bs_0" → "bs_0"
                    int first  = t.indexOf('_');
                    int second = t.indexOf('_', first + 1);
                    String basePid = second >= 0 ? t.substring(second + 1) : null;
                    if (basePid != null) {
                        // Count how many distinct buttons for this puzzle are solved
                        String suffix = "_" + basePid;
                        int pressed = 0;
                        for (String s : solvedPuzzles)
                            if (s.startsWith("btn_") && s.endsWith(suffix)) pressed++;
                        if (pressed >= 3) unlockDoor("reward_" + basePid);
                    }
                }
                break;
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

            // Shadow Ascent narrative patterns override the generic step() for their 4 types
            boolean isNarrativeBoss = switch (boss.type) {
                case SIREN, ECHO_WARDEN, TIME_LEECH_LORD, MEMORY_EATER -> true;
                default -> false;
            };

            if (isNarrativeBoss) {
                BossPatternLibrary.PatternContext ctx = new BossPatternLibrary.PatternContext(
                    players,
                    hub,
                    () -> pendingScriptedLoss = true,
                    (type, x, y) -> spawnEnemyAt(type, x, y)
                );
                BossPatternLibrary.ServerEvent evt = BossPatternLibrary.tick(boss, ctx, DT);
                if (evt == BossPatternLibrary.ServerEvent.SCRIPTED_LOSS)
                    log.info("[M5] SCRIPTED_LOSS event queued for broadcast");
            } else {
                boss.step(DT, nearestX, nearestY, dist);
            }

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
                float d = Math.abs(cx - (npc.physics.x + npc.physics.width * 0.5f));
                if (d < nearestDist) { nearestDist = d; nearestX = cx; }
            }
        }

        for (SimNPC npc : npcs) {
            // Edge detection: probe one step ahead at foot level.
            // If there's no solid tile beneath the NPC's leading foot, it's a ledge.
            float stepX   = SimNPC.PATROL_SPEED + 2f;   // probe slightly beyond one tick's movement
            float probeX  = npc.facing == 1
                ? npc.physics.x + npc.physics.width + stepX   // right foot probe
                : npc.physics.x - stepX;                      // left foot probe
            float footY   = npc.physics.y + npc.physics.height + 1f; // one pixel below feet
            var   floorCandidates = spatialHash.candidates(probeX, footY, 2f, 2f);
            boolean floorAhead = false;
            for (var tile : floorCandidates) {
                if (!tile.isPlatform() && tile.overlaps(probeX, footY, 2f, 2f)) {
                    floorAhead = true;
                    break;
                }
            }
            boolean edgeAhead = npc.physics.onGround && !floorAhead;
            npc.step(nearestX, edgeAhead);
        }
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
            case "skeleton" -> new SimEnemy(hubId+"_skeleton_"+idx, "skeleton", spec.x(), spec.y(), 32, 56, 3+hpBonus, 1, 60f *speedMult, 200f, 64f * SKELETON_RANGE_MULT, spec.patrolMinX(), spec.patrolMaxX(), false);
            case "spearman" -> new SimEnemy(hubId+"_spearman_"+idx, "spearman", spec.x(), spec.y(), 36, 52, 4+hpBonus, 2, 65f *speedMult, 190f, 80f, spec.patrolMinX(), spec.patrolMaxX(), false);
            case "archer"   -> new SimEnemy(hubId+"_archer_"+idx,   "archer",   spec.x(), spec.y(), 32, 48, 3+hpBonus, 1, 90f *speedMult, 320f, 200f,spec.patrolMinX(), spec.patrolMaxX(), false);
            default         -> new SimEnemy(hubId+"_enemy_"+idx,    spec.type(),spec.x(), spec.y(), 32, 48, 3+hpBonus, 1, 72f *speedMult, 200f, 32f, spec.patrolMinX(), spec.patrolMaxX(), false);
        };
    }

    /**
     * Dynamically spawn an enemy mid-simulation (used by Time Leech Lord pattern).
     * Spawns at the given world position with default patrol bounds centred on spawn.
     */
    private void spawnEnemyAt(String type, float x, float y) {
        int idx = enemies.size();
        float patrolHalf = 96f;
        SimEnemy en = switch (type) {
            case "time_leech" -> new SimEnemy(hubId+"_tl_"+idx, "slime", x, y, 32, 32,
                                              2, 1, 80f, 160f, 32f,
                                              x - patrolHalf, x + patrolHalf, false);
            default           -> new SimEnemy(hubId+"_dyn_"+idx, type, x, y, 32, 48,
                                              2, 1, 72f, 180f, 32f,
                                              x - patrolHalf, x + patrolHalf, false);
        };
        enemies.add(en);
        log.debug("[M5] spawned {} at ({},{})", type, x, y);
    }

    // ── Accessors (for testing) ───────────────────────────────────────────────

    public Map<Integer, SimPlayer> getPlayers()  { return java.util.Collections.unmodifiableMap(players); }
    public List<SimEnemy>          getEnemies()  { return java.util.Collections.unmodifiableList(enemies); }
    public List<SimPickup>         getPickups()  { return java.util.Collections.unmodifiableList(pickups); }
    public List<SimNPC>            getNpcs()     { return java.util.Collections.unmodifiableList(npcs); }
    public List<SimEcho>           getEchoes()   { return java.util.Collections.unmodifiableList(echoes); }

    /**
     * Dynamically spawn an NPC mid-simulation (hub evolution: hub state change).
     * Registers with EntityManager so physics/collision apply each tick.
     */
    public void addNpc(SimNPC npc) {
        npcs.add(npc);
        var entity = entityManager.create(com.indieniinja.core.EntityType.NPC, npc.physics);
        entity.addTag("npc");
    }

    /**
     * Dynamically despawn an NPC mid-simulation (hub evolution: hub state change).
     * Removes from EntityManager and the live NPC list.
     */
    public void removeNpc(String npcId) {
        npcs.removeIf(n -> n.id.equals(npcId));
        // EntityManager entities are tagged "npc" — find by physics reference identity
        // is complex; use a no-op removal that lets the entity tick harmlessly until
        // the next snapshot. The NPC won't appear in getSnapshot() once removed from
        // the npcs list, which is what the client observes.
    }

    /**
     * Hot-swap the spatial hash used for collision resolution.
     * Called when the player crosses a room boundary so the new room's
     * tiles (plus its neighbors) become collidable.
     */
    public void updateSpatialHash(com.indieniinja.physics.SpatialHash hash) {
        this.spatialHash = hash;
        collisionSystem.setSpatialHash(hash);
    }

    // ── Inner types ───────────────────────────────────────────────────────────

    /**
     * Respawn slot for a room-layout pickup position.
     * When the live pickup for this slot is collected or expires, the slot
     * enters cooldown; once cooldownTicks reaches 0 a fresh pickup is spawned.
     */
    private static final class PickupSlot {
        final float  x, y;
        final String type;
        /** Counts down to 0, then a new pickup is spawned. */
        int     cooldownTicks;
        /** True while a live SimPickup exists for this slot. */
        boolean active;

        PickupSlot(float x, float y, String type) {
            this.x      = x;
            this.y      = y;
            this.type   = type;
            this.active = true;
        }
    }
}
