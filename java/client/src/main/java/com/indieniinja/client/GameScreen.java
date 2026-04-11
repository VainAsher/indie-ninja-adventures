package com.indieniinja.client;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.Input;
import com.badlogic.gdx.Screen;
import com.badlogic.gdx.files.FileHandle;
import com.badlogic.gdx.graphics.GL20;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.g2d.TextureAtlas;
import com.indieniinja.client.audio.AudioManager;
import com.indieniinja.client.game.DialogueManager;
import com.indieniinja.client.game.MissionManager;
import com.indieniinja.client.game.StoryManager;
import com.indieniinja.client.network.NetworkClientThread;
import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.sim.SimPlayer;
import com.indieniinja.client.rendering.AnimationRegistry;
import com.indieniinja.client.rendering.BlobTileSet;
import com.indieniinja.client.rendering.ChunkRenderer;
import com.indieniinja.client.rendering.EntityRenderer;
import com.indieniinja.client.rendering.HudRenderer;
import com.indieniinja.client.rendering.ParticleSystem;
import com.indieniinja.client.ui.DialogueOverlay;
import com.indieniinja.client.ui.InventoryOverlay;
import com.indieniinja.client.ui.MinimapRenderer;
import com.indieniinja.client.ui.PauseScreen;
import com.indieniinja.client.ui.ShopOverlay;
import com.indieniinja.network.ShopState;
import com.indieniinja.network.NPCState;
import com.indieniinja.network.InputCommand;
import com.indieniinja.network.PlayerState;
import com.indieniinja.network.WorldRoomDescriptor;
import com.indieniinja.network.WorldSnapshot;
import com.indieniinja.world.AutotileResolver;
import com.indieniinja.physics.PhysicsConstants;
import com.indieniinja.world.WorldGenerator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * In-game screen — contains the full render + simulation loop.
 *
 * Extracted from NinjaGameClient (which now extends Game and manages screens).
 * ESC toggles a PauseScreen overlay; the network thread keeps running while
 * paused so the server stays in sync.
 */
public final class GameScreen implements Screen {

    private static final Logger log = LoggerFactory.getLogger(GameScreen.class);

    private static final float PHYSICS_DT     = PhysicsConstants.FIXED_DT;
    private static final float MAX_FRAME_TIME = PhysicsConstants.MAX_FRAME_TIME;
    private static final int   LEVEL_COLS     = PhysicsConstants.ROOM_WIDTH_TILES;   // 128
    private static final int   LEVEL_ROWS     = PhysicsConstants.ROOM_HEIGHT_TILES;  // 128

    private final NinjaGameClient game;
    private final String          host;
    private final int             port;
    private final String          gameMode;
    /** True when running offline — no NetworkClientThread, local GameSimulator only. */
    private final boolean         soloMode;

    // ── Core subsystems ───────────────────────────────────────────────────────
    private SpriteBatch         batch;
    /** Reusable matrix for translating entity draws by the current room world-space offset. */
    private final com.badlogic.gdx.math.Matrix4 entityTransform = new com.badlogic.gdx.math.Matrix4();
    private GameCamera          camera;
    private GameStateBuffer     stateBuffer;
    private InputPoller         inputPoller;
    private NetworkClientThread networkClient;

    // ── Solo mode (offline) ───────────────────────────────────────────────────
    /** Local authoritative simulator — non-null only in solo mode. */
    private GameSimulator       localSim;
    /** Monotonically increasing frame counter for the local sim. */
    private long                localFrame = 0;
    /** Room type and neighbor dirs for solo mode snapshots (GameSimulator doesn't track these). */
    private java.util.List<String> soloNeighborDirs = java.util.List.of();
    private String                 soloRoomType     = "combat";
    private long                   soloSeed         = 0;

    // ── Rendering subsystems ──────────────────────────────────────────────────
    private AnimationRegistry anims;
    private BlobTileSet       blobTileSet;
    private ChunkRenderer     chunkRenderer;
    private EntityRenderer    entityRenderer;
    private HudRenderer       hudRenderer;
    private ParticleSystem    particleSystem;

    // ── Pause overlay ─────────────────────────────────────────────────────────
    private PauseScreen pauseScreen;
    private boolean     paused = false;

    // ── Campaign / missions / dialogue / save ─────────────────────────────────
    private StoryManager    storyManager;
    private MissionManager  missionManager;
    private DialogueManager dialogueManager;
    private DialogueOverlay dialogueOverlay;
    private com.indieniinja.client.game.SaveManager saveManager;

    // ── Inventory / shop / minimap overlays ──────────────────────────────────
    private InventoryOverlay inventoryOverlay;
    private ShopOverlay      shopOverlay;
    private com.indieniinja.client.ui.CraftingOverlay craftingOverlay;
    private MinimapRenderer  minimapRenderer;
    /** Latest shop states from full snapshot — keyed by npc_id. */
    private final java.util.Map<String, ShopState> latestShopStates = new java.util.LinkedHashMap<>();
    /** Cached world room list from the most recent full snapshot (empty on delta frames). */
    private java.util.List<WorldRoomDescriptor> cachedWorldRooms = java.util.List.of();
    /** Cached portal list from the most recent full snapshot. */
    private java.util.List<com.indieniinja.network.PortalState> cachedPortals = java.util.List.of();
    /** Stable enemy list — updated on full snapshots, delta-merged otherwise; used by minimap. */
    private java.util.List<com.indieniinja.network.EnemyState>  cachedEnemies  = java.util.List.of();
    /** Stable pickup list — same lifecycle as cachedEnemies. */
    private java.util.List<com.indieniinja.network.PickupState> cachedPickups  = java.util.List.of();
    /** Tile grids keyed "gx,gy" — generated in buildMegamap; consumed by minimap tile-detail. */
    private final java.util.Map<String, byte[][]> cachedTileGrids = new java.util.HashMap<>();
    /** Rooms the local player has visited (entered at least once). */
    private final java.util.Set<String> visitedRooms = new java.util.HashSet<>();

    // ── Audio ─────────────────────────────────────────────────────────────────
    private AudioManager audioManager;
    /** Previous animState per player slot — for state-transition SFX detection. */
    private final java.util.Map<Integer,String>  prevAnimState = new java.util.HashMap<>();
    /** Previous health per player slot — for hurt/death SFX detection. */
    private final java.util.Map<Integer,Integer> prevHealth    = new java.util.HashMap<>();

    /** Most recently received snapshot — retained between frames for overlay input. */
    private WorldSnapshot prevSnap = null;

    // ── Mission progress tracking (Loop 18) ──────────────────────────────────
    /** Enemy IDs seen last frame — diff used to detect kills for mission objectives. */
    private final java.util.Set<String>           prevEnemyIds  = new java.util.HashSet<>();
    /** Boss alive state last frame — transition true→false signals defeat. */
    private final java.util.Map<String, Boolean>  prevBossAlive = new java.util.HashMap<>();

    // ── Ability unlock toasts (Loop 20) ──────────────────────────────────────
    /** Abilities seen last frame for local player — new entries trigger toast notification. */
    private final java.util.Set<String> prevLocalAbilities = new java.util.HashSet<>();

    /** NPC type → default dialogue id (Python: NPCDefinition.dialogue_id). */
    private static String npcDialogueId(String npcType) {
        return switch (npcType != null ? npcType : "lore") {
            case "shop"          -> "shop_keeper";
            case "mission_giver" -> "mission_elder";
            case "tutorial"      -> "tutorial_elder";
            default              -> "tutorial_elder";   // "lore" and unknown
        };
    }

    // ── Fixed-timestep state ──────────────────────────────────────────────────
    private float accumulator     = 0f;
    private int   localSlot       = 0;
    private long  loadedSeed      = Long.MIN_VALUE;   // tracks which seed we've generated tiles for
    private java.util.List<String> loadedNeighborDirs = java.util.List.of();
    /** Previous room grid position — used to detect same-hub room crossings. */
    private int   prevRoomGridX   = Integer.MIN_VALUE;
    private int   prevRoomGridY   = Integer.MIN_VALUE;

    // ── Megamap state ─────────────────────────────────────────────────────────
    /** Number of rooms in the built megamap (0 = not built yet). */
    private int     megamapRoomCount = 0;
    /** Grid coordinate of the top-left room in the megamap. */
    private int     megamapMinGridX  = 0;
    private int     megamapMinGridY  = 0;
    /** Full megamap size in tiles (for camera clamping). */
    private int     megamapW         = LEVEL_COLS;
    private int     megamapH         = LEVEL_ROWS;
    /**
     * Set true on zone transition so the next full-snapshot megamap rebuild is
     * forced regardless of room count.
     */
    private boolean megamapStale     = false;

    public GameScreen(NinjaGameClient game, String host, int port) {
        this(game, host, port, "arcade");
    }

    public GameScreen(NinjaGameClient game, String host, int port, String gameMode) {
        this.game     = game;
        this.host     = host;
        this.port     = port;
        this.gameMode = gameMode;
        this.soloMode = "solo".equals(gameMode);
    }

    // ── Screen lifecycle ──────────────────────────────────────────────────────

    @Override
    public void show() {
        batch       = new SpriteBatch();
        camera      = new GameCamera(Gdx.graphics.getWidth(), Gdx.graphics.getHeight());
        // Snap to spawn area. Base floor PLATFORM at row 126 → y=4032.
        // Camera centres on the player's expected position (centre-x, base-floor level).
        camera.snapTo(
            LEVEL_COLS * PhysicsConstants.TILE_SIZE / 2f,   // centre horizontally
            (LEVEL_ROWS - 4) * PhysicsConstants.TILE_SIZE   // near base floor (Y-DOWN)
        );
        stateBuffer = new GameStateBuffer();
        inputPoller = new InputPoller();

        anims = new AnimationRegistry();
        FileHandle atlasFile    = Gdx.files.internal("assets/characters.atlas");
        FileHandle playerDir    = Gdx.files.internal("assets/sprites/player");
        FileHandle enemyBaseDir = Gdx.files.internal("assets/sprites/characters");
        if (atlasFile.exists()) {
            anims.loadAtlas(new TextureAtlas(atlasFile));
        } else if (playerDir.exists()) {
            anims.loadSpriteSheets(playerDir);
        } else {
            anims.loadPlaceholder();
        }
        // Load per-enemy-type animations (falls back to colored placeholders if
        // assets/sprites/characters/{type}/ does not exist).
        anims.loadEnemySprites(enemyBaseDir);
        // Load per-NPC-type animations + dot texture for indicators/companions.
        FileHandle npcBaseDir = Gdx.files.internal("assets/sprites/npc");
        anims.loadNpcSprites(npcBaseDir);

        // Try to load the mk_nature blob autotile set.  Falls back to placeholder
        // if the asset files are not present (allows running without full assets).
        FileHandle blobPng  = Gdx.files.internal("assets/tileset/mk_nature.png");
        FileHandle blobJson = Gdx.files.internal("assets/tileset/mk_nature_blob_sets.json");
        if (blobPng.exists() && blobJson.exists()) {
            blobTileSet = new BlobTileSet(blobPng, blobJson);
        }

        chunkRenderer = new ChunkRenderer();
        chunkRenderer.loadPlaceholderLayout(LEVEL_COLS, LEVEL_ROWS);

        particleSystem = new ParticleSystem();
        entityRenderer = new EntityRenderer(anims, particleSystem);
        hudRenderer    = new HudRenderer();

        pauseScreen = new PauseScreen(game, this::resume);

        if (soloMode) {
            // Offline path — build a local GameSimulator; no network thread needed.
            long seed = System.currentTimeMillis();
            soloSeed         = seed;
            soloRoomType     = "combat";
            soloNeighborDirs = java.util.List.of();
            LevelLayout layout = LevelLayout.buildProceduralLayout(seed);
            localSim = new GameSimulator(seed, "solo_hub", layout);
            SimPlayer player = new SimPlayer("solo_player", 0, layout.spawnX, layout.spawnY);
            localSim.addPlayer(player);
            // Push an initial full snapshot so GameScreen has something to render immediately.
            com.indieniinja.network.WorldSnapshot initSnap = localSim.getSnapshot(localFrame++);
            stampSoloFields(initSnap);
            stateBuffer.update(initSnap);
            stateBuffer.markConnected();
        } else {
            networkClient = new NetworkClientThread(host, port, stateBuffer);
            networkClient.setGameMode(gameMode);
            networkClient.start();
        }

        // Campaign / missions / dialogue / save systems
        storyManager    = new StoryManager();
        missionManager  = new MissionManager();
        dialogueManager = new DialogueManager();
        dialogueManager.setStoryContext(storyManager.toConditionContext());
        dialogueManager.setEventCallback(this::handleDialogueEvent);
        dialogueOverlay = new DialogueOverlay(dialogueManager);
        saveManager     = new com.indieniinja.client.game.SaveManager(storyManager, missionManager);
        saveManager.load();
        missionManager.setOnMissionComplete(() -> saveManager.markDirty());
        missionManager.setOnMissionFail(    () -> saveManager.markDirty());

        // Inventory / shop / minimap overlays
        inventoryOverlay = new InventoryOverlay();
        shopOverlay      = new ShopOverlay();
        craftingOverlay  = new com.indieniinja.client.ui.CraftingOverlay();
        craftingOverlay.setOnCraft(recipeId ->
            networkClient.sendMessage(
                com.indieniinja.network.MessageType.CRAFT_REQUEST,
                java.util.Map.of("recipe_id", recipeId)));
        minimapRenderer  = new MinimapRenderer();
        // Solo mode: GameSimulator.getSnapshot() never populates worldRooms, so
        // cachedWorldRooms stays empty and the minimap guard blocks rendering.
        // Build the single-room descriptor now so M-key works immediately.
        if (soloMode) {
            WorldRoomDescriptor soloRoom = new WorldRoomDescriptor();
            soloRoom.gridX        = 0;
            soloRoom.gridY        = 0;
            soloRoom.seed         = soloSeed;
            soloRoom.roomType     = soloRoomType;
            soloRoom.neighborDirs = new java.util.ArrayList<>(soloNeighborDirs);
            buildMegamap(java.util.List.of(soloRoom));
            cachedWorldRooms = java.util.List.of(soloRoom);
            visitedRooms.add("0,0");
        }
        shopOverlay.setOnTrade(req -> {
            java.util.Map<String, Object> payload = new java.util.LinkedHashMap<>();
            payload.put("npc_id",   req.npcId());
            payload.put("item_id",  req.itemId());
            payload.put("quantity", req.qty());
            payload.put("is_buy",   req.isBuy());
            networkClient.sendMessage(
                com.indieniinja.network.MessageType.TRADE_REQUEST, payload);
        });
        inventoryOverlay.setOnUseItem(itemId -> {
            java.util.Map<String, Object> payload = new java.util.LinkedHashMap<>();
            payload.put("item_id", itemId);
            networkClient.sendMessage(
                com.indieniinja.network.MessageType.USE_ITEM, payload);
        });
        inventoryOverlay.setOnEquipItem(itemId -> {
            java.util.Map<String, Object> payload = new java.util.LinkedHashMap<>();
            payload.put("item_id", itemId);
            networkClient.sendMessage(
                com.indieniinja.network.MessageType.EQUIP_ITEM, payload);
        });

        // Audio
        audioManager = new AudioManager(0.8f);
        audioManager.loadSounds(Gdx.files.internal("assets/audio/sfx"));

        Gdx.input.setInputProcessor(null);  // InputPoller polls directly; ESC handled in render
    }

    @Override
    public void render(float delta) {
        delta = Math.min(delta, MAX_FRAME_TIME);

        // ── Consume slot assignment from SERVER_HELLO ─────────────────────────
        int pendingSlot = stateBuffer.pollPendingLocalSlot();
        if (pendingSlot >= 0) {
            log.info("[GameScreen] Local slot assigned: {}", pendingSlot);
            localSlot = pendingSlot;
        }

        // ── Overlay input priority: crafting > shop > inventory > dialogue > game
        // Use prevSnap (last frame's snapshot) since this frame's snap hasn't been polled yet.
        PlayerState prevLocal = prevSnap == null ? null : prevSnap.players.stream()
            .filter(p -> p.slot == localSlot).findFirst().orElse(null);
        boolean craftConsumed = craftingOverlay.handleInputAndRender(batch, prevLocal, delta);
        boolean shopConsumed  = !craftConsumed && shopOverlay.handleInput(prevLocal);
        boolean invConsumed   = !craftConsumed && !shopConsumed && inventoryOverlay.handleInput();

        // ── Dialogue input (consumes keys when dialogue is open) ─────────────
        boolean dialogueConsumed = !shopConsumed && !invConsumed && dialogueOverlay.handleInput();

        // ── I key: toggle inventory (when no other overlay active) ────────────
        if (!shopConsumed && !invConsumed && !dialogueConsumed && !paused
                && Gdx.input.isKeyJustPressed(Input.Keys.I)) {
            inventoryOverlay.toggle();
        }
        // ── M key: toggle minimap ─────────────────────────────────────────────
        if (!shopConsumed && !invConsumed && !dialogueConsumed && !paused) {
            minimapRenderer.handleInput();
        }

        // ── ESC toggles pause (only when no overlay active) ───────────────────
        boolean anyOverlay = craftConsumed || shopConsumed || invConsumed || dialogueConsumed;
        if (!anyOverlay && Gdx.input.isKeyJustPressed(Input.Keys.ESCAPE)) {
            if (paused) resume(); else pause();
        }

        if (!paused && !dialogueConsumed) {
            accumulator += delta;
            while (accumulator >= PHYSICS_DT) {
                InputCommand cmd = inputPoller.poll();
                if (soloMode) {
                    // Offline: step local sim directly and push snapshot to stateBuffer.
                    localSim.step(java.util.Map.of(0, cmd));
                    com.indieniinja.network.WorldSnapshot soloSnap = localSim.getSnapshot(localFrame++);
                    stampSoloFields(soloSnap);
                    stateBuffer.update(soloSnap);
                } else {
                    networkClient.sendInput(cmd);
                }
                accumulator -= PHYSICS_DT;
            }
        }

        // ── Hub/world transition (portal or arcade depth advance): full reset ────
        // Same-hub room crossings do NOT send WORLD_TRANSITION — they are handled
        // smoothly via prevRoomGridX/Y detection in the snapshot path below.
        if (stateBuffer.pollZoneTransition()) {
            megamapStale       = true;
            megamapRoomCount   = 0;  // world graph changed; must rebuild from scratch
            megamapMinGridX    = 0;
            megamapMinGridY    = 0;
            megamapW           = LEVEL_COLS;
            megamapH           = LEVEL_ROWS;
            loadedSeed         = Long.MIN_VALUE;
            loadedNeighborDirs = java.util.List.of();
            cachedWorldRooms   = java.util.List.of();
            cachedPortals      = java.util.List.of();
            latestShopStates.clear();
            prevSnap           = null;
            prevRoomGridX      = Integer.MIN_VALUE;
            prevRoomGridY      = Integer.MIN_VALUE;
            prevEnemyIds.clear();
            prevBossAlive.clear();
            cachedEnemies  = java.util.List.of();
            cachedPickups  = java.util.List.of();
            cachedTileGrids.clear();
            visitedRooms.clear();
            minimapRenderer.clearState();
            chunkRenderer.loadPlaceholderLayout(LEVEL_COLS, LEVEL_ROWS);
        }

        WorldSnapshot snap = stateBuffer.poll();

        // ── Mission timer + auto-save ─────────────────────────────────────────
        missionManager.tick(delta);
        saveManager.tick(delta);

        // ── Audio: state-transition SFX ──────────────────────────────────────
        if (snap != null) tickAudio(snap);

        // ── Mission objective progress (enemy kills, boss defeat) ────────────
        if (snap != null) tickMissionProgress(snap);

        // ── E-key: interact with nearest interactable NPC or portal ─────────────
        if (!anyOverlay && !paused && snap != null
                && Gdx.input.isKeyJustPressed(Input.Keys.E)) {
            // Update shop states cache from latest full snapshot
            for (ShopState ss : snap.shopStates) latestShopStates.put(ss.npcId, ss);

            // Check portal interaction first (portals are closer to the player than NPCs typically)
            boolean portalTriggered = false;
            PlayerState localPlayer = snap.players.stream()
                .filter(p -> p.slot == localSlot).findFirst().orElse(null);
            if (localPlayer != null) {
                for (com.indieniinja.network.PortalState portal : cachedPortals) {
                    if (!portal.isActive) continue;
                    float pcx = localPlayer.posX + 14f;  // player centre (width=28/2)
                    float pcy = localPlayer.posY + 28f;  // player centre (height=56/2)
                    float poCx = portal.x + portal.width  * 0.5f;
                    float poCy = portal.y + portal.height * 0.5f;
                    float dx = pcx - poCx, dy = pcy - poCy;
                    if (dx * dx + dy * dy <= 56f * 56f) {
                        // Send PORTAL_TRAVEL to server
                        networkClient.sendMessage(com.indieniinja.network.MessageType.PORTAL_TRAVEL,
                            java.util.Map.of("destination_id", portal.destinationId));
                        portalTriggered = true;
                        break;
                    }
                }
            }

            if (!portalTriggered) {
                for (NPCState npc : snap.npcs) {
                    if (npc.isInteractable) {
                        if ("shop".equals(npc.npcType) && latestShopStates.containsKey(npc.npcId)) {
                            inventoryOverlay.hide();
                            shopOverlay.open(latestShopStates.get(npc.npcId));
                        } else if ("crafter".equals(npc.npcType)) {
                            inventoryOverlay.hide();
                            shopOverlay.hide();
                            craftingOverlay.open();
                        } else {
                            String dialogueId = npcDialogueId(npc.npcType);
                            dialogueManager.setStoryContext(storyManager.toConditionContext());
                            dialogueManager.startNpcDialogue(dialogueId);
                        }
                        break;
                    }
                }
            }
        }

        if (snap != null) {
            // ── Room change detection (for cache clearing and minimap fog) ────────
            // With unified world-space the player simply walks across room boundaries
            // without any zone transition — detect room change from roomGridX/Y
            // to keep entity caches and fog-of-war consistent.
            boolean roomChanged = (snap.roomGridX != prevRoomGridX || snap.roomGridY != prevRoomGridY)
                                  && prevRoomGridX != Integer.MIN_VALUE;
            if (roomChanged) {
                // megamapStale intentionally NOT set here — the unified world tiles don't
                // change when the player crosses a room boundary; only hub transitions
                // (WORLD_TRANSITION) need a megamap rebuild.
                prevEnemyIds.clear();         // avoid false kill counts across rooms
                prevBossAlive.clear();
                latestShopStates.clear();
                cachedPortals = java.util.List.of();
                cachedEnemies = java.util.List.of();
                cachedPickups = java.util.List.of();
                log.debug("[GameScreen] room changed ({},{})→({},{})",
                    prevRoomGridX, prevRoomGridY, snap.roomGridX, snap.roomGridY);
                // No camera snap needed — entities are already in world-space so the
                // camera spring-lerp follows the player's continuous position naturally.
            }
            prevRoomGridX = snap.roomGridX;
            prevRoomGridY = snap.roomGridY;

            // ── Mark current room as visited (fog of war) ─────────────────────
            visitedRooms.add(snap.roomGridX + "," + snap.roomGridY);

            // ── Keep stable entity caches for minimap (full snapshots only) ───
            if (!snap.isDelta) {
                cachedEnemies = snap.enemies;
                cachedPickups = snap.pickups;
            }

            // ── Update shop states cache (full snapshots have non-empty shopStates) ─
            if (!snap.shopStates.isEmpty()) {
                for (ShopState ss : snap.shopStates) latestShopStates.put(ss.npcId, ss);
            }

            // ── Cache world rooms from full snapshots (empty on delta frames) ──
            if (!snap.worldRooms.isEmpty()) {
                cachedWorldRooms = snap.worldRooms;
            }

            // ── Cache portal list from full snapshots ─────────────────────────
            if (!snap.portals.isEmpty()) {
                cachedPortals = snap.portals;
            }

            // ── Megamap: build stitched world tilemap when full room list arrives ─
            // Rebuild if: room count changed (new hub) OR stale flag set (zone transition).
            if (!snap.worldRooms.isEmpty() && (megamapStale || snap.worldRooms.size() != megamapRoomCount)) {
                megamapStale = false;
                buildMegamap(snap.worldRooms);
                // Snap camera to player's world-space position directly —
                // entities are in world-space so posX/Y are already the correct target.
                if (!snap.players.isEmpty()) {
                    PlayerState snapLocal = snap.players.stream()
                        .filter(p -> p.slot == localSlot).findFirst()
                        .orElse(snap.players.get(0));
                    camera.snapTo(snapLocal.posX, snapLocal.posY);
                }
            }

            // ── Single-room fallback: generate tiles for current room only ───────
            // Used until the first full snapshot (with worldRooms) arrives, and as
            // a safety net when worldRooms is missing.
            if (megamapRoomCount == 0) {
                boolean seedChanged = snap.seed != 0 && snap.seed != loadedSeed;
                boolean dirsChanged = !snap.neighborDirs.equals(loadedNeighborDirs);
                if (seedChanged || dirsChanged) {
                    loadedSeed         = snap.seed;
                    loadedNeighborDirs = snap.neighborDirs;
                    String rType = snap.roomType != null ? snap.roomType : "combat";
                    byte[][] grid2d = WorldGenerator.generate(
                        snap.seed, LEVEL_COLS, LEVEL_ROWS, snap.neighborDirs, rType);
                    log.info("[GameScreen] single-room grid seed={} type={} dirs={}",
                        snap.seed, rType, snap.neighborDirs);
                    if (blobTileSet != null) {
                        int biomeIdx = BlobTileSet.biomeFromSeed(snap.seed);
                        chunkRenderer.loadBlobTiles(blobTileSet, biomeIdx, grid2d, LEVEL_COLS, LEVEL_ROWS);
                    } else {
                        byte[] flat = new byte[LEVEL_ROWS * LEVEL_COLS];
                        for (int r = 0; r < LEVEL_ROWS; r++)
                            System.arraycopy(grid2d[r], 0, flat, r * LEVEL_COLS, LEVEL_COLS);
                        chunkRenderer.loadProceduralTiles(flat, LEVEL_COLS, LEVEL_ROWS);
                    }
                }
            }

            // ── Camera follow ─────────────────────────────────────────────────
            // Entities and player are in world-space — follow posX/Y directly.
            if (!snap.players.isEmpty()) {
                PlayerState local = snap.players.stream()
                    .filter(p -> p.slot == localSlot)
                    .findFirst()
                    .orElse(snap.players.get(0));
                camera.follow(local.posX, local.posY);
                camera.clampToBounds(
                    megamapW * PhysicsConstants.TILE_SIZE,
                    megamapH * PhysicsConstants.TILE_SIZE
                );
            }
        }

        // ── Render world ──────────────────────────────────────────────────────
        Gdx.gl.glClearColor(0.08f, 0.08f, 0.12f, 1f);
        Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT);

        particleSystem.update(delta);

        batch.setProjectionMatrix(camera.cam.combined);

        // Pass 1 — tiles: megamap tiles are already in world-space coords, identity transform.
        batch.setTransformMatrix(entityTransform.idt());
        batch.begin();
            chunkRenderer.render(batch, camera);
        batch.end();

        // Pass 2 — entities: already in world-space, identity transform.
        batch.setTransformMatrix(entityTransform.idt());
        batch.begin();
            entityRenderer.render(batch, snap, delta);
            particleSystem.render(batch);
        batch.end();

        entityRenderer.pruneEntities(snap);

        hudRenderer.render(snap, soloMode || stateBuffer.isConnected(),
            Gdx.graphics.getFramesPerSecond(), localSlot);

        // ── Ability unlock toasts ─────────────────────────────────────────────
        hudRenderer.renderToasts(delta);

        // ── Dialogue overlay (rendered on top of HUD, below pause) ────────────
        if (dialogueManager.isActive()) {
            batch.setProjectionMatrix(hudRenderer.screenProjection());
            batch.begin();
            dialogueOverlay.render(batch);
            batch.end();
            batch.setProjectionMatrix(camera.cam.combined);
        }

        // ── Minimap (large centred overlay) ──────────────────────────────────
        if (minimapRenderer.isVisible() && !cachedWorldRooms.isEmpty()) {
            WorldSnapshot snapForMap = snap != null ? snap : prevSnap;
            PlayerState localForMap = snapForMap != null
                ? snapForMap.players.stream().filter(p -> p.slot == localSlot).findFirst()
                    .orElse(!snapForMap.players.isEmpty() ? snapForMap.players.get(0) : null)
                : null;
            int   gridX   = snapForMap != null ? snapForMap.roomGridX : 0;
            int   gridY   = snapForMap != null ? snapForMap.roomGridY : 0;
            float roomPx  = PhysicsConstants.ROOM_WIDTH_TILES  * PhysicsConstants.TILE_SIZE;
            float roomPy  = PhysicsConstants.ROOM_HEIGHT_TILES * PhysicsConstants.TILE_SIZE;
            // Player position is world-space; convert to room-local for the minimap dot.
            float worldPx = localForMap != null ? localForMap.posX : 0f;
            float worldPy = localForMap != null ? localForMap.posY : 0f;
            float lpx = worldPx - (gridX - megamapMinGridX) * roomPx;
            float lpy = worldPy - (gridY - megamapMinGridY) * roomPy;
            batch.setProjectionMatrix(hudRenderer.screenProjection());
            // MinimapRenderer manages its own batch.begin/end; do NOT open batch here.
            minimapRenderer.render(batch, cachedWorldRooms, gridX, gridY, lpx, lpy, roomPx, roomPy,
                cachedTileGrids, visitedRooms, snapForMap,
                cachedEnemies, cachedPickups, cachedPortals, localSlot);
            batch.setProjectionMatrix(camera.cam.combined);
        }

        // ── Inventory overlay (screen-space, centre) ──────────────────────────
        if (inventoryOverlay.isVisible() && snap != null) {
            PlayerState localInv = snap.players.stream()
                .filter(p -> p.slot == localSlot).findFirst()
                .orElse(!snap.players.isEmpty() ? snap.players.get(0) : null);
            batch.setProjectionMatrix(hudRenderer.screenProjection());
            batch.begin();
            inventoryOverlay.render(batch, localInv);
            batch.end();
            batch.setProjectionMatrix(camera.cam.combined);
        }

        // ── Shop overlay (screen-space, centre) ───────────────────────────────
        if (shopOverlay.isVisible() && snap != null) {
            PlayerState localShop = snap.players.stream()
                .filter(p -> p.slot == localSlot).findFirst()
                .orElse(!snap.players.isEmpty() ? snap.players.get(0) : null);
            batch.setProjectionMatrix(hudRenderer.screenProjection());
            batch.begin();
            shopOverlay.render(batch, localShop);
            batch.end();
            batch.setProjectionMatrix(camera.cam.combined);
        }

        // ── Pause overlay (rendered on top) ───────────────────────────────────
        if (paused) {
            pauseScreen.render(delta);
        }

        // ── Persist snapshot for next frame's overlay input handling ──────────
        if (snap != null) prevSnap = snap;
    }

    // ── Solo-mode helpers ─────────────────────────────────────────────────────

    /**
     * Stamps room-context fields that GameSimulator doesn't track onto a solo snapshot.
     * The single-room tile fallback in render() reads these to generate the tile grid.
     */
    private void stampSoloFields(WorldSnapshot snap) {
        snap.roomType     = soloRoomType;
        snap.neighborDirs = soloNeighborDirs;
        // roomGridX/Y default to 0,0 — correct for a single-room solo layout
    }

    // ── Megamap construction ──────────────────────────────────────────────────

    /**
     * Stitch all room tilemaps into a single unified TextureRegion array and
     * load it into ChunkRenderer.
     *
     * Java port of Python systems/megamap.py build_megamap().
     * Each room is at tile offset (gx - minGX) * ROOM_W, (gy - minGY) * ROOM_H.
     */
    private void buildMegamap(java.util.List<WorldRoomDescriptor> rooms) {
        int minGX = rooms.stream().mapToInt(r -> r.gridX).min().getAsInt();
        int minGY = rooms.stream().mapToInt(r -> r.gridY).min().getAsInt();
        int maxGX = rooms.stream().mapToInt(r -> r.gridX).max().getAsInt();
        int maxGY = rooms.stream().mapToInt(r -> r.gridY).max().getAsInt();

        int spanW = maxGX - minGX + 1;
        int spanH = maxGY - minGY + 1;
        int megaW = spanW * LEVEL_COLS;
        int megaH = spanH * LEVEL_ROWS;

        log.info("[GameScreen] building megamap {}×{} rooms → {}×{} tiles",
            spanW, spanH, megaW, megaH);

        com.badlogic.gdx.graphics.g2d.TextureRegion[][] mega =
            new com.badlogic.gdx.graphics.g2d.TextureRegion[megaH][megaW];

        // Discard old tile-detail textures; minimap will rebuild lazily.
        minimapRenderer.clearState();
        cachedTileGrids.clear();

        for (WorldRoomDescriptor room : rooms) {
            byte[][] grid = WorldGenerator.generate(
                room.seed, LEVEL_COLS, LEVEL_ROWS, room.neighborDirs, room.roomType);

            // Cache for minimap tile-detail feature.
            cachedTileGrids.put(room.gridX + "," + room.gridY, grid);

            int offX = (room.gridX - minGX) * LEVEL_COLS;
            int offY = (room.gridY - minGY) * LEVEL_ROWS;

            if (blobTileSet != null) {
                for (int r = 0; r < LEVEL_ROWS; r++) {
                    for (int c = 0; c < LEVEL_COLS; c++) {
                        byte tile = grid[r][c];
                        if (tile == WorldGenerator.SOLID) {
                            int role = AutotileResolver.computeRole(grid, r, c, LEVEL_ROWS, LEVEL_COLS);
                            mega[offY + r][offX + c] = blobTileSet.getFrame(room.biomeIndex, role);
                        } else if (tile == WorldGenerator.PLATFORM) {
                            mega[offY + r][offX + c] = blobTileSet.getPlatformFrame(room.biomeIndex);
                        } else {
                            // Hazard tiles (ICE, WATER, LAVA) use colour-coded placeholders
                            mega[offY + r][offX + c] = chunkRenderer.tileTexture(tile);
                        }
                    }
                }
            } else {
                for (int r = 0; r < LEVEL_ROWS; r++) {
                    for (int c = 0; c < LEVEL_COLS; c++) {
                        byte tile = grid[r][c];
                        mega[offY + r][offX + c] = chunkRenderer.tileTexture(tile);
                    }
                }
            }
        }

        chunkRenderer.loadTileMap(mega, megaW, megaH);

        megamapMinGridX  = minGX;
        megamapMinGridY  = minGY;
        megamapW         = megaW;
        megamapH         = megaH;
        megamapRoomCount = rooms.size();
        log.info("[GameScreen] megamap ready: {} rooms, origin grid=({},{})",
            megamapRoomCount, minGX, minGY);
    }

    // ── Audio event detection ─────────────────────────────────────────────────

    /**
     * Detect player state transitions and play corresponding SFX.
     * Python parity: AudioManager.play() call-sites in demo_game.py.
     */
    private void tickAudio(WorldSnapshot snap) {
        for (PlayerState p : snap.players) {
            String curAnim   = p.animState != null ? p.animState : "";
            String prev      = prevAnimState.getOrDefault(p.slot, "");
            int    prevHp    = prevHealth.getOrDefault(p.slot, p.health);

            // Jump / double_jump onset
            if (!prev.equals("jump") && !prev.equals("double_jump")
                    && (curAnim.equals("jump") || curAnim.equals("double_jump"))) {
                audioManager.play("jump");
            }
            // Land: was airborne (jump/fall), now grounded
            if ((prev.equals("jump") || prev.equals("fall") || prev.equals("double_jump"))
                    && !curAnim.equals("jump") && !curAnim.equals("fall")
                    && !curAnim.equals("double_jump")) {
                audioManager.play("land");
            }
            // Dash onset
            if (!prev.equals("dash") && curAnim.equals("dash")) {
                audioManager.play("dash");
            }
            // Melee attack onset
            if (!prev.equals("attack") && curAnim.equals("attack")) {
                audioManager.play("swing");
            }
            // Hurt (hp decreased, player not dead)
            if (p.health < prevHp && !p.isDead) {
                audioManager.play("player_hurt");
            }
            // Death onset
            boolean wasDead = prevAnimState.containsKey(p.slot)
                && prev.equals("dead");
            if (p.isDead && !wasDead && !prev.equals("dead")) {
                audioManager.play("player_death");
            }

            prevAnimState.put(p.slot, curAnim);
            prevHealth.put(p.slot,    p.health);
        }
    }

    // ── Dialogue event handler ────────────────────────────────────────────────

    /**
     * Receives events emitted by dialogue choices and node exits.
     * Format: "event_key" or "event_key:arg".
     */
    private void handleDialogueEvent(String event) {
        if (event == null) return;
        String[] parts = event.split(":", 2);
        switch (parts[0]) {
            case "start_mission" -> {
                if (parts.length > 1) missionManager.startMission(parts[1]);
            }
            case "open_shop"     -> { /* stub — shop UI not yet implemented */ }
            case "advance_act"   -> storyManager.advanceAct();
            default              -> { /* unknown event — no-op */ }
        }
    }

    // ── Mission objective progress ────────────────────────────────────────────

    /**
     * Detects enemy kills and boss defeats from snapshot diffs, then forwards
     * progress to MissionManager so KILL_ALL_ENEMIES / DEFEAT_BOSS objectives advance.
     *
     * Uses prevEnemyIds (populated each frame) so zone transitions (which clear it)
     * won't spuriously count the old room's enemies as kills.
     */
    private void tickMissionProgress(WorldSnapshot snap) {
        // ── Enemy kills ───────────────────────────────────────────────────────
        java.util.Set<String> currentIds = new java.util.HashSet<>();
        for (com.indieniinja.network.EnemyState e : snap.enemies) currentIds.add(e.enemyId);

        if (!prevEnemyIds.isEmpty()) {
            // Any ID in prev but not in current = killed this frame
            int kills = 0;
            for (String id : prevEnemyIds) if (!currentIds.contains(id)) kills++;
            if (kills > 0) {
                missionManager.progressObjective("kill_all_enemies_", kills);
                log.debug("[Mission] {} enemy kill(s) detected", kills);
                // Persist to save stats
                var sd = saveManager.getSaveData();
                if (sd != null) {
                    sd.totalEnemiesKilled += kills;
                    sd.totalDeathsStat   += kills;  // legacy compat field
                    saveManager.markDirty();
                }
            }
        }
        prevEnemyIds.clear();
        prevEnemyIds.addAll(currentIds);

        // ── Boss defeats ──────────────────────────────────────────────────────
        for (com.indieniinja.network.BossState boss : snap.bosses) {
            boolean wasAlive = prevBossAlive.getOrDefault(boss.bossId, true);
            if (wasAlive && !boss.alive) {
                missionManager.progressObjective("defeat_boss_", 1);
                // Also try keyed by boss type in case mission specifies one
                if (boss.bossType != null && !boss.bossType.isEmpty()) {
                    missionManager.progressObjective("defeat_boss_" + boss.bossType, 1);
                }
                log.debug("[Mission] boss {} defeated", boss.bossId);
            }
            prevBossAlive.put(boss.bossId, boss.alive);
        }

        // ── Ability unlocks (Loop 20) ─────────────────────────────────────────
        com.indieniinja.network.PlayerState localP = snap.players.stream()
            .filter(p -> p.slot == localSlot).findFirst().orElse(null);
        if (localP != null) {
            for (String ab : localP.abilities) {
                if (!prevLocalAbilities.contains(ab)) {
                    hudRenderer.notifyAbilityUnlock(ab);
                    log.info("[Ability] unlocked: {}", ab);
                }
            }
            prevLocalAbilities.clear();
            prevLocalAbilities.addAll(localP.abilities);
        }
    }

    @Override
    public void resize(int w, int h) {
        camera.resize(w, h);
        hudRenderer.resize(w, h);
        batch.setProjectionMatrix(camera.cam.combined);
        if (pauseScreen != null) pauseScreen.resize(w, h);
    }

    @Override public void pause()  { paused = true;  pauseScreen.activate(); }
    @Override public void resume() { paused = false; Gdx.input.setInputProcessor(null); }
    @Override public void hide()   {}

    @Override
    public void dispose() {
        if (saveManager    != null) saveManager.save();
        if (audioManager   != null) audioManager.dispose();
        if (networkClient  != null) networkClient.shutdown();
        if (batch          != null) batch.dispose();
        if (anims          != null) anims.dispose();
        if (blobTileSet    != null) blobTileSet.dispose();
        if (chunkRenderer  != null) chunkRenderer.dispose();
        if (particleSystem != null) particleSystem.dispose();
        if (hudRenderer    != null) hudRenderer.dispose();
        if (pauseScreen    != null) pauseScreen.dispose();
        if (dialogueOverlay  != null) dialogueOverlay.dispose();
        if (inventoryOverlay != null) inventoryOverlay.dispose();
        if (shopOverlay      != null) shopOverlay.dispose();
        if (craftingOverlay  != null) craftingOverlay.dispose();
        if (minimapRenderer  != null) minimapRenderer.dispose();
    }
}
