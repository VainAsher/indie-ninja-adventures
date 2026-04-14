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
import com.indieniinja.client.game.MissionDefinition;
import com.indieniinja.client.game.MissionLocationTriggerRegistry;
import com.indieniinja.client.game.MissionManager;
import com.indieniinja.client.game.MissionObjective;
import com.indieniinja.client.game.ObjectiveType;
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
import com.indieniinja.client.ui.MissionSelectOverlay;
import com.indieniinja.client.ui.PauseScreen;
import com.indieniinja.client.ui.ShopOverlay;
import com.indieniinja.network.ShopState;
import com.indieniinja.network.NPCState;
import com.indieniinja.network.InputCommand;
import com.indieniinja.network.PlayerState;
import com.indieniinja.network.WorldRoomDescriptor;
import com.indieniinja.network.WorldSnapshot;
import com.indieniinja.world.AutotileResolver;
import com.indieniinja.world.WorldGraph;
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
    /** WorldGraph for the solo session — drives the multi-room megamap. */
    private WorldGraph          soloWorldGraph;
    /** Current room grid coords in solo mode (derived from player position). */
    private int                 soloCurrentGridX = 0;
    private int                 soloCurrentGridY = 0;
    /** Room type and neighbor dirs for solo mode snapshots (GameSimulator doesn't track these). */
    private java.util.List<String> soloNeighborDirs = java.util.List.of();
    private String                 soloRoomType     = "combat";
    private long                   soloSeed         = 0;
    /** World-space spawn position for solo mode — used by portal travel to warp back to start. */
    private float                  soloSpawnX       = 0f;
    private float                  soloSpawnY       = 0f;
    /** Records per-frame inputs in solo mode when -Dninja.record=true is set. */
    private final com.indieniinja.sim.InputRecorder soloRecorder = new com.indieniinja.sim.InputRecorder();

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
    private boolean     scriptedLossOverlay = false;

    // ── Campaign / missions / dialogue / save ─────────────────────────────────
    private StoryManager    storyManager;
    private MissionManager  missionManager;
    private DialogueManager dialogueManager;
    private DialogueOverlay dialogueOverlay;
    private MissionSelectOverlay missionSelectOverlay;
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

    // ── Debug ─────────────────────────────────────────────────────────────────
    /** Toggle with H key — draws physics AABB outlines over all entities. */
    private boolean debugHitboxes = false;
    private com.badlogic.gdx.graphics.glutils.ShapeRenderer hitboxRenderer;

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
    /** Local player inventory totals from previous frame — diff used for collect_items objectives. */
    private final java.util.Map<String, Integer>  prevInventoryTotals = new java.util.HashMap<>();
    /** Dialogue event telemetry: key -> count processed this session. */
    private final java.util.Map<String, Integer>  dialogueEventCounts = new java.util.HashMap<>();
    /** Per-mission reached location ids to avoid replaying one-shot objective triggers. */
    private final java.util.Set<String> missionReachedLocations = new java.util.HashSet<>();
    private String missionTriggerMissionId = "";
    /** Mission contact volumes rebuilt from room entities each frame (debug-visible with H). */
    private final java.util.List<MissionContactVolume> missionContactVolumes = new java.util.ArrayList<>();
    /** Authored REACH_LOCATION trigger map loaded from data/mission_location_triggers.json. */
    private MissionLocationTriggerRegistry missionLocationTriggers = MissionLocationTriggerRegistry.load(null);
    /** Missing trigger warnings already emitted (avoid per-frame spam). */
    private final java.util.Set<String> missingMissionTriggerWarnings = new java.util.HashSet<>();

    private record MissionContactVolume(String id, float x, float y, float width, float height, String source) {}

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
        FileHandle unarmedDir = Gdx.files.internal("assets/sprites/player/unarmed");
        FileHandle swordDir   = Gdx.files.internal("assets/sprites/player/sword");
        if (atlasFile.exists()) {
            anims.loadAtlas(new TextureAtlas(atlasFile));
        } else if (playerDir.exists()) {
            anims.loadSpriteSheets(playerDir);  // legacy flat directory fallback
        } else {
            anims.loadPlaceholder();
        }
        // Load extracted template sheets (override legacy flat-dir mappings when present).
        if (unarmedDir.exists()) anims.loadUnarmedSheets(unarmedDir);  // animation Phase 3
        if (swordDir.exists())   anims.loadSwordSheets(swordDir);      // animation Phase 3
        // Load per-enemy-type animations (falls back to colored placeholders if
        // assets/sprites/characters/{type}/ does not exist).
        anims.loadEnemySprites(enemyBaseDir);
        // Load stitched enemy spritesheets from tools/stitch_enemy_frames.py output.
        // Overrides the colored placeholders above when the sheets are present.
        FileHandle enemySheetDir = Gdx.files.internal("assets/sprites/enemies");
        if (enemySheetDir.exists()) anims.loadEnemySheets(enemySheetDir);
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
        hitboxRenderer = new com.badlogic.gdx.graphics.glutils.ShapeRenderer();

        pauseScreen = new PauseScreen(game, this::resume);

        if (soloMode) {
            // Offline path — build a multi-room WorldGraph and unified layout;
            // no NetworkClientThread needed.
            long seed = System.currentTimeMillis();
            soloSeed       = seed;
            soloWorldGraph = WorldGraph.generate(seed, 12, WorldGraph.WorldShape.BLOB);
            WorldGraph.RoomNode startRoom = soloWorldGraph.startRoom();
            soloCurrentGridX = startRoom.gridX;
            soloCurrentGridY = startRoom.gridY;
            soloRoomType     = startRoom.type.wire();
            soloNeighborDirs = new java.util.ArrayList<>(startRoom.neighborDirs());
            LevelLayout layout = LevelLayout.buildUnifiedWorldLayout(soloWorldGraph, "solo_hub");
            localSim = new GameSimulator(startRoom.seed, "solo_hub", layout);
            localSim.setDarkArea(true);  // solo dungeon is always dark — lantern decays
            soloSpawnX = layout.spawnX;
            soloSpawnY = layout.spawnY;
            SimPlayer player = new SimPlayer("solo_player", 0, layout.spawnX, layout.spawnY);
            localSim.addPlayer(player);
            // Start replay recording if -Dninja.record=true was passed to this JVM.
            if (Boolean.getBoolean("ninja.record")) soloRecorder.startRecording(soloSeed);
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
        missionLocationTriggers = MissionLocationTriggerRegistry.load(
            Gdx.files.internal("data/mission_location_triggers.json"));
        java.util.List<String> missingReachObjectives =
            missionLocationTriggers.findMissingReachObjectives(missionManager);
        if (!missingReachObjectives.isEmpty()) {
            log.error("[Mission] missing authored location triggers for {} objective(s): {}",
                missingReachObjectives.size(), missingReachObjectives);
        } else {
            log.info("[Mission] loaded {} authored mission location triggers",
                missionLocationTriggers.size());
        }
        dialogueManager = new DialogueManager();
        dialogueManager.setStoryContext(storyManager.toConditionContext());
        dialogueManager.setEventCallback(this::handleDialogueEvent);
        dialogueOverlay = new DialogueOverlay(dialogueManager);
        missionSelectOverlay = new MissionSelectOverlay(missionManager);
        missionSelectOverlay.setOnStartMission(missionId -> {
            missionManager.startMission(missionId);
            missionReachedLocations.clear();
            missionTriggerMissionId = missionId;
            if (saveManager != null) saveManager.markDirty();
            log.info("[Mission] started via overlay: {}", missionId);
        });
        missionSelectOverlay.setOnClose(() -> dialogueManager.setStoryContext(storyManager.toConditionContext()));
        saveManager     = new com.indieniinja.client.game.SaveManager(storyManager, missionManager);
        saveManager.load();
        missionManager.setOnMissionComplete(() -> saveManager.markDirty());
        missionManager.setOnMissionFail(    () -> saveManager.markDirty());

        // Inventory / shop / minimap overlays
        inventoryOverlay = new InventoryOverlay();
        shopOverlay      = new ShopOverlay();
        craftingOverlay  = new com.indieniinja.client.ui.CraftingOverlay();
        craftingOverlay.setOnCraft(recipeId -> {
            if (networkClient != null)
                networkClient.sendMessage(
                    com.indieniinja.network.MessageType.CRAFT_REQUEST,
                    java.util.Map.of("recipe_id", recipeId));
        });
        minimapRenderer  = new MinimapRenderer();
        // Solo mode: GameSimulator.getSnapshot() never populates worldRooms, so
        // cachedWorldRooms stays empty and the minimap guard blocks rendering.
        // Build the single-room descriptor now so M-key works immediately.
        if (soloMode) {
            // Build the full multi-room megamap from the WorldGraph we generated above.
            java.util.List<WorldRoomDescriptor> soloRooms = new java.util.ArrayList<>();
            for (WorldGraph.RoomNode r : soloWorldGraph.allRooms()) {
                WorldRoomDescriptor d = new WorldRoomDescriptor();
                d.gridX        = r.gridX;
                d.gridY        = r.gridY;
                d.seed         = r.seed;
                d.roomType     = r.type.wire();
                d.neighborDirs = new java.util.ArrayList<>(r.neighborDirs());
                d.biomeIndex   = r.biomeIndex;
                soloRooms.add(d);
            }
            buildMegamap(soloRooms);
            cachedWorldRooms = soloRooms;
            WorldGraph.RoomNode startRoom = soloWorldGraph.startRoom();
            visitedRooms.add(startRoom.gridX + "," + startRoom.gridY);
        }
        shopOverlay.setOnTrade(req -> {
            if (networkClient == null) return;
            java.util.Map<String, Object> payload = new java.util.LinkedHashMap<>();
            payload.put("npc_id",   req.npcId());
            payload.put("item_id",  req.itemId());
            payload.put("quantity", req.qty());
            payload.put("is_buy",   req.isBuy());
            networkClient.sendMessage(
                com.indieniinja.network.MessageType.TRADE_REQUEST, payload);
        });
        inventoryOverlay.setOnUseItem(itemId -> {
            if (networkClient == null) return;
            java.util.Map<String, Object> payload = new java.util.LinkedHashMap<>();
            payload.put("item_id", itemId);
            networkClient.sendMessage(
                com.indieniinja.network.MessageType.USE_ITEM, payload);
        });
        inventoryOverlay.setOnEquipItem(itemId -> {
            if (networkClient == null) return;
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
        if (stateBuffer.pollScriptedLoss()) {
            scriptedLossOverlay = true;
        }
        boolean scriptedLossConsumed = handleScriptedLossOverlayInput();

        // ── Overlay input priority: crafting > shop > inventory > dialogue > game
        // Use prevSnap (last frame's snapshot) since this frame's snap hasn't been polled yet.
        PlayerState prevLocal = prevSnap == null ? null : prevSnap.players.stream()
            .filter(p -> p.slot == localSlot).findFirst().orElse(null);
        boolean craftConsumed = false;
        boolean shopConsumed  = false;
        boolean invConsumed   = false;
        if (!scriptedLossConsumed) {
            craftConsumed = craftingOverlay.handleInputAndRender(batch, prevLocal, delta);
            shopConsumed  = !craftConsumed && shopOverlay.handleInput(prevLocal);
            invConsumed   = !craftConsumed && !shopConsumed && inventoryOverlay.handleInput();
        }

        // ── Dialogue input (consumes keys when dialogue is open) ─────────────
        boolean dialogueConsumed = !scriptedLossConsumed
            && !shopConsumed && !invConsumed && dialogueOverlay.handleInput();
        boolean missionOverlayConsumed = !scriptedLossConsumed
            && !craftConsumed && !shopConsumed && !invConsumed
            && !dialogueConsumed
            && missionSelectOverlay.handleInput(storyManager.currentAct().wire());

        // ── I key: toggle inventory (when no other overlay active) ────────────
        if (!shopConsumed && !invConsumed && !dialogueConsumed && !missionOverlayConsumed && !paused
                && Gdx.input.isKeyJustPressed(Input.Keys.I)) {
            inventoryOverlay.toggle();
        }
        // ── M key: toggle minimap ─────────────────────────────────────────────
        if (!shopConsumed && !invConsumed && !dialogueConsumed && !missionOverlayConsumed && !paused) {
            minimapRenderer.handleInput();
        }

        // ── ESC toggles pause (only when no overlay active) ───────────────────
        boolean anyOverlay = scriptedLossConsumed || craftConsumed || shopConsumed || invConsumed
            || dialogueConsumed || missionOverlayConsumed;

        // ── H key: toggle hitbox debug overlay ───────────────────────────────
        if (!anyOverlay && !paused && Gdx.input.isKeyJustPressed(Input.Keys.H)) {
            debugHitboxes = !debugHitboxes;
        }
        if (!anyOverlay && Gdx.input.isKeyJustPressed(Input.Keys.ESCAPE)) {
            if (paused) resume(); else pause();
        }

        if (!paused && !dialogueConsumed && !missionOverlayConsumed && !scriptedLossConsumed) {
            accumulator += delta;
            while (accumulator >= PHYSICS_DT) {
                InputCommand cmd = inputPoller.poll();
                if (soloMode) {
                    // Offline: step local sim directly and push snapshot to stateBuffer.
                    if (soloRecorder.isRecording()) soloRecorder.record(localFrame, 0, cmd);
                    localSim.step(java.util.Map.of(0, cmd));
                    if (localSim.drainPendingScriptedLoss()) {
                        stateBuffer.markScriptedLoss();
                    }
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
            missionContactVolumes.clear();
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
        if (snap != null) tickMissionContactVolumes(snap);

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
                float pcx = localPlayer.posX + 14f;  // player centre (width=28/2)
                float pcy = localPlayer.posY + 28f;  // player centre (height=56/2)
                for (com.indieniinja.network.PortalState portal : cachedPortals) {
                    if (!portal.isActive) continue;
                    float poCx = portal.x + portal.width  * 0.5f;
                    float poCy = portal.y + portal.height * 0.5f;
                    float dx = pcx - poCx, dy = pcy - poCy;
                    if (dx * dx + dy * dy <= 56f * 56f) {
                        if (missionManager.isActive() && isMissionExitPortal(portal, snap)) {
                            if (missionManager.isExitLocked()) {
                                log.info("[Mission] exit blocked until objectives are complete");
                                portalTriggered = true;
                                break;
                            }
                            missionManager.completeMission();
                            if (saveManager != null) saveManager.markDirty();
                            missionReachedLocations.clear();
                            missionTriggerMissionId = "";
                            log.info("[Mission] completed on exit contact before portal travel");
                        }
                        if (networkClient == null) {
                            // Solo mode: warp player directly to the destination room
                            // in the unified world-space layout.
                            handleSoloPortalTravel(portal.destinationId);
                        } else {
                            // Multiplayer: let the server handle the zone transition.
                            networkClient.sendMessage(com.indieniinja.network.MessageType.PORTAL_TRAVEL,
                                java.util.Map.of("destination_id", portal.destinationId));
                        }
                        portalTriggered = true;
                        break;
                    }
                }
            }

            if (!portalTriggered) {
                NPCState closestNpc = null;
                if (localPlayer != null) {
                    float pcx = localPlayer.posX + 14f;
                    float pcy = localPlayer.posY + 28f;
                    float bestD2 = Float.MAX_VALUE;
                    for (NPCState npc : snap.npcs) {
                        if (!npc.isInteractable) continue;
                        float ncx = npc.x + 14f;
                        float ncy = npc.y + 28f;
                        float dx = pcx - ncx;
                        float dy = pcy - ncy;
                        float d2 = dx * dx + dy * dy;
                        if (d2 < bestD2) {
                            bestD2 = d2;
                            closestNpc = npc;
                        }
                    }
                }
                if (closestNpc != null) {
                    if (closestNpc.npcType != null
                            && (closestNpc.npcType.startsWith("btn_") || closestNpc.npcType.startsWith("lever_"))) {
                        String activeMissionId = missionManager.getActiveMissionId();
                        if (activeMissionId != null && !activeMissionId.isBlank()) {
                            missionManager.onSwitchActivated(activeMissionId + ":" + closestNpc.npcId);
                            log.debug("[Mission] switch activation tagged for mission {} via {}",
                                activeMissionId, closestNpc.npcId);
                        }
                    } else if ("shop".equals(closestNpc.npcType) && latestShopStates.containsKey(closestNpc.npcId)) {
                        inventoryOverlay.hide();
                        shopOverlay.open(latestShopStates.get(closestNpc.npcId));
                    } else if ("crafter".equals(closestNpc.npcType)) {
                        inventoryOverlay.hide();
                        shopOverlay.hide();
                        craftingOverlay.open();
                    } else {
                        String dialogueId = npcDialogueId(closestNpc.npcType);
                        dialogueManager.setStoryContext(storyManager.toConditionContext());
                        dialogueManager.startNpcDialogue(dialogueId);
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
                missionContactVolumes.clear();
                latestShopStates.clear();
                cachedPortals = java.util.List.of();
                cachedEnemies = java.util.List.of();
                cachedPickups = java.util.List.of();
                // Room entry is a meaningful checkpoint — trigger auto-save
                if (saveManager != null) saveManager.markDirty();
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

            // ── Hub state → StoryManager → Act FSM ───────────────────────────
            if (snap.hubState != null && !snap.hubState.isEmpty()) {
                storyManager.onHubStateUpdate(snap.hubState);
                dialogueManager.setStoryContext(storyManager.toConditionContext());
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

        // Pass 0 — update Lantern vignette intensity from local player state (M4)
        if (snap != null) {
            for (com.indieniinja.network.PlayerState lp : snap.players) {
                if (lp.slot == localSlot) {
                    chunkRenderer.setLanternValue(lp.lanternValue);
                    break;
                }
            }
        }

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

        // Pass 2c — Debug hitbox overlay (H key toggle).
        if (debugHitboxes && snap != null) {
            Gdx.gl.glEnable(com.badlogic.gdx.graphics.GL20.GL_BLEND);
            hitboxRenderer.setProjectionMatrix(camera.cam.combined);
            hitboxRenderer.begin(com.badlogic.gdx.graphics.glutils.ShapeRenderer.ShapeType.Line);
            entityRenderer.renderHitboxes(hitboxRenderer, snap);
            for (MissionContactVolume v : missionContactVolumes) {
                if (v == null) continue;
                if ("portal".equals(v.source)) {
                    hitboxRenderer.setColor(0.20f, 0.90f, 1.00f, 1f);
                } else {
                    hitboxRenderer.setColor(1.00f, 0.80f, 0.25f, 1f);
                }
                hitboxRenderer.rect(v.x, v.y, v.width, v.height);
            }
            hitboxRenderer.end();
            Gdx.gl.glDisable(com.badlogic.gdx.graphics.GL20.GL_BLEND);
        }

        // Pass 2b — Lantern vignette (screen-space overlay drawn after world, before HUD) (M4)
        chunkRenderer.renderVignette(hudRenderer.shapeRenderer(),
            Gdx.graphics.getWidth(), Gdx.graphics.getHeight());

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

        if (missionSelectOverlay.isVisible()) {
            batch.setProjectionMatrix(hudRenderer.screenProjection());
            batch.begin();
            missionSelectOverlay.render(batch, storyManager.currentAct().wire());
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

        // ── Death / respawn overlay ───────────────────────────────────────────
        if (snap != null) {
            PlayerState localPlayer = snap.players.stream()
                .filter(p -> p.slot == localSlot)
                .findFirst().orElse(null);
            if (localPlayer != null && localPlayer.isDead) {
                hudRenderer.renderDeathOverlay(localPlayer.respawnTimer);
            }
        }

        if (scriptedLossOverlay) {
            hudRenderer.renderScriptedLossOverlay();
        }

        // ── Pause overlay (rendered on top) ───────────────────────────────────
        if (paused) {
            pauseScreen.render(delta);
        }

        // ── Persist snapshot for next frame's overlay input handling ──────────
        if (snap != null) prevSnap = snap;
    }

    private boolean handleScriptedLossOverlayInput() {
        if (!scriptedLossOverlay) return false;
        boolean continuePressed =
            Gdx.input.isKeyJustPressed(Input.Keys.ENTER)
                || Gdx.input.isKeyJustPressed(Input.Keys.SPACE)
                || (Gdx.input.justTouched()
                    && hudRenderer.scriptedLossButtonHit(Gdx.input.getX(), Gdx.input.getY()));
        if (continuePressed) {
            scriptedLossOverlay = false;
            storyManager.onVeilMaidenDefeatedAct1();
            dialogueManager.setStoryContext(storyManager.toConditionContext());
        }
        return true;
    }

    /**
     * Contact-volume mission logic:
     * - REACH_LOCATION objectives fire when player overlaps a volume matching locationId.
     * - Mission completes only when objectives are met and player reaches exit contact.
     */
    private void tickMissionContactVolumes(WorldSnapshot snap) {
        String activeMissionId = missionManager.getActiveMissionId();
        if (activeMissionId == null || activeMissionId.isBlank()) {
            missionTriggerMissionId = "";
            missionReachedLocations.clear();
            missionContactVolumes.clear();
            return;
        }

        if (!activeMissionId.equals(missionTriggerMissionId)) {
            missionTriggerMissionId = activeMissionId;
            missionReachedLocations.clear();
        }

        MissionDefinition def = missionManager.getActiveDefinition();
        if (def == null) return;

        PlayerState local = snap.players.stream()
            .filter(p -> p.slot == localSlot)
            .findFirst().orElse(null);
        if (local == null) return;

        buildMissionContactVolumes(snap, def, activeMissionId);
        float px = local.posX + 14f;
        float py = local.posY + 28f;

        for (MissionObjective obj : def.objectives) {
            if (obj.type != ObjectiveType.REACH_LOCATION || obj.location == null || obj.location.isBlank()) continue;
            String loc = normalizeKey(obj.location);
            if (missionReachedLocations.contains(loc)) continue;
            if (playerOverlapsVolume(loc, px, py)) {
                missionManager.onReachLocation(loc);
                missionReachedLocations.add(loc);
                log.info("[Mission] location reached: {} (mission {})", loc, activeMissionId);
            }
        }

        if (!missionManager.isExitLocked() && playerOverlapsVolume("exit", px, py)) {
            missionManager.completeMission();
            if (saveManager != null) saveManager.markDirty();
            missionReachedLocations.clear();
            missionTriggerMissionId = "";
            log.info("[Mission] completed by reaching exit contact volume");
        }
    }

    private void buildMissionContactVolumes(WorldSnapshot snap, MissionDefinition def, String activeMissionId) {
        missionContactVolumes.clear();

        // Exit volume stays portal-driven for mission completion.
        for (com.indieniinja.network.PortalState portal : cachedPortals) {
            if (!portal.isActive) continue;
            missionContactVolumes.add(new MissionContactVolume(
                "exit", portal.x, portal.y, portal.width, portal.height, "portal"));
        }

        if (missionLocationTriggers == null || def == null || activeMissionId == null || activeMissionId.isBlank()) {
            return;
        }

        int[] anchorRoom = resolveMissionAnchorRoom(snap);
        int anchorGridX = anchorRoom[0];
        int anchorGridY = anchorRoom[1];

        for (MissionObjective obj : def.objectives) {
            if (obj.type != ObjectiveType.REACH_LOCATION || obj.location == null || obj.location.isBlank()) continue;
            String locationId = normalizeKey(obj.location);
            MissionLocationTriggerRegistry.TriggerDef triggerDef =
                missionLocationTriggers.get(activeMissionId, locationId);
            if (triggerDef == null) {
                String missing = normalizeKey(activeMissionId) + ":" + locationId;
                if (missingMissionTriggerWarnings.add(missing)) {
                    log.error("[Mission] missing authored trigger mapping for {}", missing);
                }
                continue;
            }
            missionContactVolumes.add(
                buildAuthoredReachLocationVolume(activeMissionId, locationId, triggerDef, anchorGridX, anchorGridY));
        }
    }

    private boolean playerOverlapsVolume(String id, float px, float py) {
        String key = normalizeKey(id);
        for (MissionContactVolume v : missionContactVolumes) {
            if (!v.id.equals(key)) continue;
            if (px >= v.x && px <= v.x + v.width && py >= v.y && py <= v.y + v.height) {
                return true;
            }
        }
        return false;
    }

    private int[] resolveMissionAnchorRoom(WorldSnapshot snap) {
        for (WorldRoomDescriptor room : cachedWorldRooms) {
            if ("start".equalsIgnoreCase(room.roomType)) {
                return new int[] { room.gridX, room.gridY };
            }
        }
        return new int[] { snap.roomGridX, snap.roomGridY };
    }

    private MissionContactVolume buildAuthoredReachLocationVolume(
        String missionId,
        String locationId,
        MissionLocationTriggerRegistry.TriggerDef triggerDef,
        int anchorGridX,
        int anchorGridY
    ) {
        int targetGridX = anchorGridX + triggerDef.roomGridXOffset();
        int targetGridY = anchorGridY + triggerDef.roomGridYOffset();
        float roomPxX = LEVEL_COLS * PhysicsConstants.TILE_SIZE;
        float roomPxY = LEVEL_ROWS * PhysicsConstants.TILE_SIZE;
        float roomOriginX = (targetGridX - megamapMinGridX) * roomPxX;
        float roomOriginY = (targetGridY - megamapMinGridY) * roomPxY;

        MissionContactVolume volume = new MissionContactVolume(
            locationId,
            roomOriginX + triggerDef.x(),
            roomOriginY + triggerDef.y(),
            Math.max(24f, triggerDef.width()),
            Math.max(24f, triggerDef.height()),
            "mission_authored");

        if (triggerDef.snapToReachableGround()) {
            volume = snapMissionVolumeToReachableGround(volume, targetGridX, targetGridY, triggerDef.maxSnapRadiusTiles());
        }
        volume = clampVolumeToRoom(volume, targetGridX, targetGridY);
        log.debug("[Mission] trigger {}:{} @ ({}, {}) size ({}, {}) source={}",
            normalizeKey(missionId), locationId, volume.x, volume.y, volume.width, volume.height, volume.source);
        return volume;
    }

    private MissionContactVolume snapMissionVolumeToReachableGround(
        MissionContactVolume volume, int roomGridX, int roomGridY, int maxSnapRadiusTiles
    ) {
        byte[][] grid = tileGridForRoom(roomGridX, roomGridY);
        if (grid == null) return volume;

        int tile = PhysicsConstants.TILE_SIZE;
        float roomPxX = LEVEL_COLS * tile;
        float roomPxY = LEVEL_ROWS * tile;
        float roomOriginX = (roomGridX - megamapMinGridX) * roomPxX;
        float roomOriginY = (roomGridY - megamapMinGridY) * roomPxY;

        float anchorX = clampFloat(volume.x + volume.width * 0.5f, roomOriginX, roomOriginX + roomPxX - 1f);
        float anchorY = clampFloat(volume.y + volume.height, roomOriginY, roomOriginY + roomPxY - 1f);
        int anchorCol = clampInt((int) ((anchorX - roomOriginX) / tile), 0, LEVEL_COLS - 1);
        int anchorRow = clampInt((int) ((anchorY - roomOriginY) / tile), 1, LEVEL_ROWS - 1);

        int[] best = findNearestReachableGroundCell(grid, anchorRow, anchorCol, Math.max(0, maxSnapRadiusTiles));
        if (best == null) {
            // Hard guarantee: authored triggers always land on a standable cell if the room has one.
            best = findNearestReachableGroundCell(grid, anchorRow, anchorCol, Math.max(LEVEL_COLS, LEVEL_ROWS));
            if (best == null) return volume;
        }

        int r = best[0];
        int c = best[1];
        float snappedX = roomOriginX + c * tile + (tile - volume.width) * 0.5f;
        float snappedY = roomOriginY + r * tile - volume.height;
        return new MissionContactVolume(volume.id, snappedX, snappedY, volume.width, volume.height, volume.source + ":snapped");
    }

    private byte[][] tileGridForRoom(int roomGridX, int roomGridY) {
        String key = roomGridX + "," + roomGridY;
        byte[][] cached = cachedTileGrids.get(key);
        if (cached != null) return cached;

        for (WorldRoomDescriptor room : cachedWorldRooms) {
            if (room.gridX != roomGridX || room.gridY != roomGridY) continue;
            byte[][] generated = WorldGenerator.generate(
                room.seed, LEVEL_COLS, LEVEL_ROWS, room.neighborDirs, room.roomType);
            cachedTileGrids.put(key, generated);
            return generated;
        }
        return null;
    }

    private int[] findNearestReachableGroundCell(byte[][] grid, int anchorRow, int anchorCol, int radiusTiles) {
        int minRow = clampInt(anchorRow - radiusTiles, 1, LEVEL_ROWS - 1);
        int maxRow = clampInt(anchorRow + radiusTiles, 1, LEVEL_ROWS - 1);
        int minCol = clampInt(anchorCol - radiusTiles, 0, LEVEL_COLS - 1);
        int maxCol = clampInt(anchorCol + radiusTiles, 0, LEVEL_COLS - 1);
        int bestRow = -1;
        int bestCol = -1;
        int bestDistSq = Integer.MAX_VALUE;

        for (int r = minRow; r <= maxRow; r++) {
            for (int c = minCol; c <= maxCol; c++) {
                if (!isReachableGroundCell(grid, r, c)) continue;
                int dr = r - anchorRow;
                int dc = c - anchorCol;
                int distSq = dr * dr + dc * dc;
                if (distSq < bestDistSq) {
                    bestDistSq = distSq;
                    bestRow = r;
                    bestCol = c;
                }
            }
        }
        return bestRow >= 0 ? new int[] { bestRow, bestCol } : null;
    }

    private boolean isReachableGroundCell(byte[][] grid, int row, int col) {
        if (grid == null) return false;
        if (row <= 0 || row >= LEVEL_ROWS || col < 0 || col >= LEVEL_COLS) return false;
        byte tile = grid[row][col];
        byte above = grid[row - 1][col];
        return isSolidForStanding(tile) && above == WorldGenerator.AIR;
    }

    private static boolean isSolidForStanding(byte tile) {
        return tile == WorldGenerator.SOLID
            || tile == WorldGenerator.PLATFORM
            || tile == WorldGenerator.ICE
            || tile == WorldGenerator.LAVA
            || tile == WorldGenerator.DOOR_LOCKED;
    }

    private MissionContactVolume clampVolumeToRoom(MissionContactVolume volume, int roomGridX, int roomGridY) {
        float roomPxX = LEVEL_COLS * PhysicsConstants.TILE_SIZE;
        float roomPxY = LEVEL_ROWS * PhysicsConstants.TILE_SIZE;
        float roomOriginX = (roomGridX - megamapMinGridX) * roomPxX;
        float roomOriginY = (roomGridY - megamapMinGridY) * roomPxY;
        float maxX = Math.max(roomOriginX, roomOriginX + roomPxX - volume.width);
        float maxY = Math.max(roomOriginY, roomOriginY + roomPxY - volume.height);
        float x = clampFloat(volume.x, roomOriginX, maxX);
        float y = clampFloat(volume.y, roomOriginY, maxY);
        return new MissionContactVolume(volume.id, x, y, volume.width, volume.height, volume.source);
    }

    private static int clampInt(int value, int min, int max) {
        if (value < min) return min;
        if (value > max) return max;
        return value;
    }

    private static float clampFloat(float value, float min, float max) {
        if (value < min) return min;
        if (value > max) return max;
        return value;
    }

    private static String normalizeKey(String value) {
        return value == null ? "" : value.trim().toLowerCase(java.util.Locale.ROOT);
    }

    private boolean isMissionExitPortal(com.indieniinja.network.PortalState portal, WorldSnapshot snap) {
        if (portal == null || snap == null) return false;
        if ("exit".equalsIgnoreCase(snap.roomType)) return true;
        return "hub".equalsIgnoreCase(portal.portalType);
    }

    // ── Solo-mode helpers ─────────────────────────────────────────────────────

    /**
     * Stamps room-context fields that GameSimulator doesn't track onto a solo snapshot.
     * The single-room tile fallback in render() reads these to generate the tile grid.
     */
    private static final int SOLO_ROOM_PX =
        PhysicsConstants.ROOM_WIDTH_TILES * PhysicsConstants.TILE_SIZE;  // 4096

    private void stampSoloFields(WorldSnapshot snap) {
        // Derive current room from the local player's world-space position.
        if (soloWorldGraph != null && !snap.players.isEmpty()) {
            PlayerState ps = snap.players.get(0);
            int minGX = Integer.MAX_VALUE, minGY = Integer.MAX_VALUE;
            for (WorldGraph.RoomNode r : soloWorldGraph.allRooms()) {
                if (r.gridX < minGX) minGX = r.gridX;
                if (r.gridY < minGY) minGY = r.gridY;
            }
            int gx = (int) Math.floor(ps.posX / SOLO_ROOM_PX) + minGX;
            int gy = (int) Math.floor(ps.posY / SOLO_ROOM_PX) + minGY;
            WorldGraph.RoomNode room = soloWorldGraph.roomAt(gx, gy);
            if (room != null && (gx != soloCurrentGridX || gy != soloCurrentGridY)) {
                soloCurrentGridX = gx;
                soloCurrentGridY = gy;
                soloRoomType     = room.type.wire();
                soloNeighborDirs = new java.util.ArrayList<>(room.neighborDirs());
            }
            snap.roomGridX    = soloCurrentGridX;
            snap.roomGridY    = soloCurrentGridY;
        }
        snap.roomType     = soloRoomType;
        snap.neighborDirs = soloNeighborDirs;
    }

    /**
     * Handles portal interaction in solo mode by warping the player directly to
     * the start room's spawn point within the unified world layout.
     * <p>
     * In multiplayer, PORTAL_TRAVEL is a server-side zone transition; in solo mode
     * there are no separate zones — the whole world is a single unified layout —
     * so we treat every portal as a shortcut back to the START room (which acts as
     * the hub in solo play).
     */
    private void handleSoloPortalTravel(String destinationId) {
        if (localSim == null) return;
        com.indieniinja.sim.SimPlayer sp = localSim.getPlayer(0);
        if (sp == null) return;
        // Warp to the start-room spawn saved when the solo session was initialised.
        sp.physics.x  = soloSpawnX;
        sp.physics.y  = soloSpawnY;
        sp.physics.vx = 0f;
        sp.physics.vy = 0f;
        // Reset room tracking so stampSoloFields picks up the new position next frame.
        if (soloWorldGraph != null) {
            com.indieniinja.world.WorldGraph.RoomNode startRoom = soloWorldGraph.startRoom();
            soloCurrentGridX = startRoom.gridX;
            soloCurrentGridY = startRoom.gridY;
            soloRoomType     = startRoom.type.wire();
            soloNeighborDirs = new java.util.ArrayList<>(startRoom.neighborDirs());
        }
        log.info("[GameScreen] solo portal travel → start room ({})", destinationId);
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
        String key = parts[0];
        String arg = parts.length > 1 ? parts[1] : "";
        dialogueEventCounts.merge(key, 1, Integer::sum);

        switch (key) {
            case "start_mission" -> {
                if (!arg.isBlank()) {
                    missionManager.startMission(arg);
                    missionReachedLocations.clear();
                    missionTriggerMissionId = arg;
                    if (saveManager != null) saveManager.markDirty();
                }
            }
            case "open_shop"     -> { /* stub — shop UI not yet implemented */ }
            case "advance_act"   -> storyManager.advanceAct();
            // Known authored narrative events from data/dialogues.json.
            // Preserve them as story flags even when they do not map to an immediate gameplay action.
            case "tutorial_completed",
                 "town_lore_learned",
                 "act2_elder_conversation_complete",
                 "act2_elder_patience_shown",
                 "act3_final_blessing_received",
                 "act3_elder_final_conversation" -> {
                storyManager.setFlag(key, "true");
            }
            case "open_mission_menu" -> {
                storyManager.setFlag(key, "true");
                inventoryOverlay.hide();
                shopOverlay.hide();
                craftingOverlay.close();
                missionSelectOverlay.open(storyManager.currentAct().wire());
                log.info("[Dialogue] opened mission select overlay");
            }
            // Generic mission adapters (optional authored dialogue hooks).
            case "switch_activated" -> missionManager.onSwitchActivated(arg);
            case "reach_location" -> missionManager.onReachLocation(arg);
            case "collect_item" -> missionManager.onItemCollected(arg, 1);
            default -> {
                String value = arg.isBlank() ? "true" : arg;
                storyManager.setFlag(key, value);
                log.warn("[Dialogue] unknown event '{}'; stored as story flag='{}' (count={})",
                    key, value, dialogueEventCounts.getOrDefault(key, 1));
            }
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
                missionManager.onEnemyKilled(kills);
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
                missionManager.onBossDefeated(boss.bossType);
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

        // Inventory gains (collect_items objective wiring).
        if (localP != null && localP.inventory != null) {
            java.util.Map<String, Integer> currentTotals = new java.util.HashMap<>();
            for (var slot : localP.inventory.slots) {
                if (slot == null) continue;
                String itemId = slot.itemId();
                if (itemId == null || itemId.isBlank()) continue;
                currentTotals.merge(itemId.toLowerCase(java.util.Locale.ROOT), slot.quantity(), Integer::sum);
            }
            for (var e : currentTotals.entrySet()) {
                int prevQty = prevInventoryTotals.getOrDefault(e.getKey(), 0);
                int gained = e.getValue() - prevQty;
                if (gained > 0) {
                    missionManager.onItemCollected(e.getKey(), gained);
                    log.debug("[Mission] item gain {} +{}", e.getKey(), gained);
                }
            }
            prevInventoryTotals.clear();
            prevInventoryTotals.putAll(currentTotals);
        }
    }

    /**
     * If a solo replay is in progress, stop it and write the .ndjson file to
     * user_data/replays/. Called from hide() and dispose() so no session is lost.
     */
    private void flushSoloReplay() {
        if (!soloRecorder.isRecording()) return;
        try {
            java.nio.file.Path dir = java.nio.file.Paths.get("user_data", "replays");
            java.nio.file.Files.createDirectories(dir);
            String fname = "replay_solo_" + System.currentTimeMillis() + ".ndjson";
            soloRecorder.stopRecording(dir.resolve(fname));
            log.info("[GameScreen] solo replay saved: {}", fname);
        } catch (java.io.IOException e) {
            log.warn("[GameScreen] failed to save solo replay: {}", e.getMessage());
        }
    }

    /**
     * Synchronise current in-memory game state into SaveManager's liveData before
     * a write.  Called from hide() and dispose() so nothing is lost on exit.
     *
     * Covers fields that SaveData.capture(story, missions) doesn't reach:
     *   world seed, visited rooms, player inventory, currency, abilities.
     */
    private void syncSaveState() {
        if (saveManager == null) return;
        com.indieniinja.client.game.SaveData live = saveManager.getSaveData();
        if (live == null) return;

        // World seed (solo session only; multiplayer seed lives on the server)
        if (soloSeed != 0) live.worldSeed = soloSeed;

        // Fog-of-war: rooms visited this session
        live.visitedRoomKeys = new java.util.ArrayList<>(visitedRooms);

        // Player state from solo sim
        if (localSim != null) {
            com.indieniinja.sim.SimPlayer sp = localSim.getPlayer(0);
            if (sp != null) {
                live.currency       = sp.inventory.currency;
                live.equippedWeapon = sp.inventory.equippedWeapon;
                live.equippedArmor  = sp.inventory.equippedArmor;
                live.unlockedAbilities = new java.util.ArrayList<>(sp.unlockedAbilities);

                // Flatten inventory slots → itemId → total quantity
                live.playerInventory = new java.util.HashMap<>();
                for (com.indieniinja.sim.SimInventory.Slot slot : sp.inventory.slots) {
                    if (slot != null) {
                        live.playerInventory.merge(slot.itemId(), slot.quantity(), Integer::sum);
                    }
                }
            }
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
    @Override public void hide()   { if (saveManager != null) { syncSaveState(); saveManager.save(); } flushSoloReplay(); }

    @Override
    public void dispose() {
        if (saveManager    != null) { syncSaveState(); saveManager.save(); }
        flushSoloReplay();
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
        if (missionSelectOverlay != null) missionSelectOverlay.dispose();
        if (inventoryOverlay != null) inventoryOverlay.dispose();
        if (shopOverlay      != null) shopOverlay.dispose();
        if (craftingOverlay  != null) craftingOverlay.dispose();
        if (minimapRenderer  != null) minimapRenderer.dispose();
        if (hitboxRenderer   != null) hitboxRenderer.dispose();
    }
}
