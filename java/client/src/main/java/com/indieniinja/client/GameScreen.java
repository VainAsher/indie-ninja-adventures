package com.indieniinja.client;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.Input;
import com.badlogic.gdx.InputAdapter;
import com.badlogic.gdx.InputProcessor;
import com.badlogic.gdx.Screen;
import com.badlogic.gdx.files.FileHandle;
import com.badlogic.gdx.graphics.GL20;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.g2d.TextureAtlas;
import com.indieniinja.content.ContentLoadException;
import com.indieniinja.content.ContentLoader;
import com.indieniinja.content.ContentRegistry;
import com.indieniinja.client.audio.AudioManager;
import com.indieniinja.client.audio.MusicManager;
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
import com.indieniinja.client.rendering.DecorationGenerator;
import com.indieniinja.client.rendering.EntityRenderer;
import com.indieniinja.client.rendering.HudRenderer;
import com.indieniinja.client.rendering.ParallaxRenderer;
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
    private static final float TAB_FULL_MAP_HOLD_SECONDS = 0.28f;
    private static final int   LEVEL_COLS     = PhysicsConstants.ROOM_WIDTH_TILES;   // 128
    private static final int   LEVEL_ROWS     = PhysicsConstants.ROOM_HEIGHT_TILES;  // 128
    private static final String PORTAL_TRANSITION_INTER_HUB = "inter_hub";
    private static final String PORTAL_TRANSITION_MISSION_RETURN = "mission_return";
    private static final String ENTITY_EVENT_MISSION_SEED_PICKUPS = "mission_seed_pickups";
    private static final String ENTITY_EVENT_MISSION_SEED_PICKUPS_CLEAR = "mission_seed_pickups_clear";

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
    private KeyBindings         keyBindings;
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
    /** Hub the solo player is currently in — mirrors SaveData.currentHubId for in-session tracking. */
    private String                 soloCurrentHubId = "central_hub";
    /** Records per-frame inputs in solo mode when -Dninja.record=true is set. */
    private final com.indieniinja.sim.InputRecorder soloRecorder = new com.indieniinja.sim.InputRecorder();
    /** Non-null during replay playback — drives inputs instead of the keyboard. */
    private com.indieniinja.sim.ReplayPlayer soloReplay;
    /** Absolute path to the .ndjson replay file to load on show(), or null for live play. */
    private final String replayPath;

    // ── Content registry (shared between sim + renderer) ─────────────────────
    private ContentRegistry clientContentRegistry;

    // ── Developer console (dev builds only) ──────────────────────────────────
    private final DevConsole devConsole = new DevConsole();
    /**
     * Console text-input bridge.
     * Game input is poll-based; keyTyped events are only needed for console commands.
     */
    private final InputAdapter devConsoleInputAdapter = new InputAdapter() {
        @Override
        public boolean keyTyped(char character) {
            if (!devConsole.isVisible()) return false;
            devConsole.typeChar(character);
            return true;
        }
    };

    // ── Rendering subsystems ──────────────────────────────────────────────────
    private AnimationRegistry anims;
    private BlobTileSet       blobTileSet;
    private int               currentBiomeIndex = 0;  // active biome for current room (S0)
    private byte[][]          currentTileGrid;         // tile grid for current room (S0)
    private ChunkRenderer     chunkRenderer;
    private ParallaxRenderer  parallaxRenderer;
    private EntityRenderer    entityRenderer;
    private HudRenderer       hudRenderer;
    private ParticleSystem    particleSystem;

    // ── Pause overlay ─────────────────────────────────────────────────────────
    private PauseScreen pauseScreen;
    private boolean     paused = false;
    private boolean     scriptedLossOverlay = false;
    private float       scriptedLossCollapseTimer = 0f;

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
    /** Last frame TAB held-state (tap/hold map split). */
    private boolean tabKeyDownLastFrame = false;
    /** Accumulated TAB hold duration while held. */
    private float tabKeyHeldSeconds = 0f;
    /** True once full-map hold path has been activated for current TAB press. */
    private boolean fullMapHoldActive = false;
    /** Whether quick-map and full-map share at least one key (tap/hold behavior). */
    private boolean sharedMapBinding = true;

    // ── Debug ─────────────────────────────────────────────────────────────────
    /** Toggle with H key — draws physics AABB outlines over all entities. */
    private boolean debugHitboxes = false;
    /** Toggle with F1 key — launcher-friendly controls panel. */
    private boolean showControlsOverlay = false;
    /** Toggle with F3 key — runtime telemetry panel for playtesting. */
    private boolean showDebugOverlay = false;
    private com.badlogic.gdx.graphics.glutils.ShapeRenderer hitboxRenderer;

    // ── Audio ─────────────────────────────────────────────────────────────────
    private AudioManager audioManager;
    private MusicManager musicManager;
    /** Previous animState per player slot — for state-transition SFX detection. */
    private final java.util.Map<Integer,String>  prevAnimState = new java.util.HashMap<>();
    /** Previous health per player slot — for hurt/death SFX detection. */
    private final java.util.Map<Integer,Integer> prevHealth    = new java.util.HashMap<>();
    /** Last local stance logged for playtest trace transitions. */
    private String lastLoggedStanceMode = null;
    /** Last local flow state logged for playtest trace transitions. */
    private Boolean lastLoggedFlowMode = null;
    /** Last local lantern band logged for playtest trace transitions. */
    private int lastLoggedLanternBand = Integer.MIN_VALUE;

    /** Most recently received snapshot — retained between frames for overlay input. */
    private WorldSnapshot prevSnap = null;

    // ── Mission progress tracking (Loop 18) ──────────────────────────────────
    /** Enemy IDs seen last frame — diff used to detect kills for mission objectives. */
    private final java.util.Set<String>           prevEnemyIds  = new java.util.HashSet<>();
    /** Boss alive state last frame — transition true→false signals defeat. */
    private final java.util.Map<String, Boolean>  prevBossAlive = new java.util.HashMap<>();
    /** Local player inventory totals from previous frame — diff used for collect_items objectives. */
    private final java.util.Map<String, Integer>  prevInventoryTotals = new java.util.HashMap<>();
    private int prevInventoryCurrency = 0;
    private boolean prevInventoryBaselineReady = false;
    /** Dialogue event telemetry: key -> count processed this session. */
    private final java.util.Map<String, Integer>  dialogueEventCounts = new java.util.HashMap<>();
    /** Per-mission reached location ids to avoid replaying one-shot objective triggers. */
    private final java.util.Set<String> missionReachedLocations = new java.util.HashSet<>();
    /** Per-mission activated fallback switch IDs (prevents duplicate activate_switches increments). */
    private final java.util.Set<String> missionActivatedSwitches = new java.util.HashSet<>();
    private final java.util.Map<String, Integer> inventoryTotalsScratch = new java.util.HashMap<>();
    private final java.util.List<String> missionTrackerLinesScratch = new java.util.ArrayList<>();
    private final java.util.List<com.indieniinja.client.ui.MinimapRenderer.ObjectiveMarker>
        minimapObjectiveMarkersScratch = new java.util.ArrayList<>();
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
    /** One-shot onboarding toasts for first-launch guidance. */
    private int onboardingToastStage = 0;
    private float onboardingToastCooldown = 1.2f;
    /** Last mission ID we emitted a "mission started" toast for. */
    private String lastMissionToastId = "";
    /** Active multiplayer mission pickup seed contract tracked client-side for lifecycle clear events. */
    private String multiplayerMissionPickupSeedMissionId = "";

    /**
     * Resolve dialogue tree id for an NPC.
     * Named characters (characterId non-empty) use their authored dialogue directly.
     * Generic role types fall back to the type-based routing table.
     */
    private static String npcDialogueId(String npcType, String characterId) {
        if (characterId != null && !characterId.isEmpty()) {
            return switch (characterId) {
                case "samson"         -> "samson_act0";
                case "sophia"         -> "sophia_act0";
                case "marcel"         -> "marcel_act0";
                case "hazel"          -> "hazel_act0";
                case "linzi"          -> "linzi_hub_early";
                case "instructor_tai" -> "tutorial_elder";
                default               -> characterId;  // fall through to authored tree by id
            };
        }
        return switch (npcType != null ? npcType : "lore") {
            case "shop"          -> "shop_keeper";
            case "mission_giver" -> "forest_ranger";
            case "siren",
                 "siren_phase1",
                 "siren_phase2",
                 "siren_phase3",
                 "siren_phase4"  -> "siren_first_quest";
            case "tutorial"      -> "tutorial_elder";
            default              -> "tutorial_elder";
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
    /**
     * Render-frame-latched gameplay input.
     *
     * One-shot actions are OR-latched until consumed by a physics tick so
     * quick taps are not lost between 60 Hz updates.
     */
    private final InputCommand latchedRealtimeInput = new InputCommand();
    private final java.util.Map<Integer, InputCommand> soloStepInputs = new java.util.HashMap<>(1);

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

    private int saveSlot = 1;

    public GameScreen(NinjaGameClient game, String host, int port) {
        this(game, host, port, "arcade", null, 1);
    }

    public GameScreen(NinjaGameClient game, String host, int port, String gameMode) {
        this(game, host, port, gameMode, null, 1);
    }

    public GameScreen(NinjaGameClient game, String host, int port, String gameMode, String replayPath) {
        this(game, host, port, gameMode, replayPath, 1);
    }

    public GameScreen(NinjaGameClient game, String host, int port, String gameMode, String replayPath, int saveSlot) {
        this.game       = game;
        this.host       = host;
        this.port       = port;
        this.gameMode   = gameMode;
        this.replayPath = replayPath;
        this.soloMode   = "solo".equals(gameMode) || replayPath != null;
        this.saveSlot   = saveSlot;
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
        FileHandle settingsFile = Gdx.files.local("user_data/settings/settings.json");
        keyBindings = KeyBindings.load(settingsFile);
        inputPoller = new InputPoller(keyBindings);
        sharedMapBinding = keyBindings.sharesAnyKey("minimap", "fullmap");
        log.info("[Playtest][Controls] preset=GDD-10.3.13 {}", inputPoller.controlPresetSummary());

        anims = new AnimationRegistry();
        FileHandle atlasFile    = Gdx.files.internal("assets/characters.atlas");
        FileHandle playerDir    = Gdx.files.internal("assets/sprites/player");
        FileHandle enemyBaseDir = Gdx.files.internal("assets/sprites/characters");
        FileHandle bossBaseDir  = Gdx.files.internal("assets/sprites/bosses");
        FileHandle unarmedDir = Gdx.files.internal("assets/sprites/player/unarmed");
        FileHandle swordDir   = Gdx.files.internal("assets/sprites/player/sword");
        FileHandle pistolDir  = Gdx.files.internal("assets/sprites/player/pistol");
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
        if (pistolDir.exists())  anims.loadPistolSheets(pistolDir);    // Arcade mode reserved
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
        anims.loadBossSprites(bossBaseDir);

        // Try to load the mk_nature blob autotile set.  Falls back to placeholder
        // if the asset files are not present (allows running without full assets).
        FileHandle blobPng  = Gdx.files.internal("assets/tileset/mk_nature.png");
        FileHandle blobJson = Gdx.files.internal("assets/tileset/mk_nature_blob_sets.json");
        if (blobPng.exists() && blobJson.exists()) {
            blobTileSet = new BlobTileSet(blobPng, blobJson);
        }

        chunkRenderer    = new ChunkRenderer();
        parallaxRenderer = new ParallaxRenderer();
        chunkRenderer.loadPlaceholderLayout(LEVEL_COLS, LEVEL_ROWS);

        particleSystem = new ParticleSystem();
        entityRenderer = new EntityRenderer(anims, particleSystem);
        clientContentRegistry = loadClientContentRegistry();
        entityRenderer.setContentRegistry(clientContentRegistry);
        devConsole.setAnimationRegistry(anims);
        devConsole.setContentRegistry(clientContentRegistry);
        devConsole.setMultiplayer(!"solo".equals(gameMode) && replayPath == null);
        registerVisualDevCommands();
        hudRenderer    = new HudRenderer();
        hitboxRenderer = new com.badlogic.gdx.graphics.glutils.ShapeRenderer();

        pauseScreen = new PauseScreen(game, this::resume);

        if (soloMode) {
            if (replayPath != null) {
                // Replay playback — load the file, seed the sim from the recording header.
                try {
                    soloReplay = com.indieniinja.sim.ReplayPlayer.load(java.nio.file.Paths.get(replayPath));
                    initializeSoloSimulation(soloReplay.seed(), false);
                    log.info("[Replay] loaded {} entries from {}", soloReplay.totalEntries(), replayPath);
                } catch (java.io.IOException e) {
                    log.error("[Replay] failed to load replay file {}: {}", replayPath, e.getMessage());
                    soloReplay = null;
                    initializeSoloSimulation(System.currentTimeMillis(), false);
                }
            } else {
                // Offline path — build local sim world immediately (may be replaced by saved seed below).
                initializeSoloSimulation(System.currentTimeMillis(), Boolean.getBoolean("ninja.record"));
            }
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
        missionSelectOverlay.setOnStartMission(missionId -> startMissionFlow(missionId, "overlay"));
        missionSelectOverlay.setOnClose(() -> dialogueManager.setStoryContext(storyManager.toConditionContext()));
        saveManager     = new com.indieniinja.client.game.SaveManager(saveSlot, storyManager, missionManager);
        saveManager.setPreSaveSync(this::syncSaveState);
        saveManager.load();
        dialogueManager.setStoryContext(storyManager.toConditionContext());
        missionManager.setOnMissionComplete(() -> {
            requestMultiplayerMissionObjectivePickupClear(
                multiplayerMissionPickupSeedMissionId,
                "mission_complete"
            );
            multiplayerMissionPickupSeedMissionId = "";
            saveManager.markDirty();
        });
        missionManager.setOnMissionFail(() -> {
            requestMultiplayerMissionObjectivePickupClear(
                multiplayerMissionPickupSeedMissionId,
                "mission_fail"
            );
            multiplayerMissionPickupSeedMissionId = "";
            saveManager.markDirty();
        });

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
        if (soloMode) {
            // Build initial minimap data and then rehydrate persisted solo runtime state.
            refreshSoloWorldRoomCache();
            restoreSoloRuntimeStateFromSave();
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
        musicManager = new MusicManager();
        musicManager.loadTracks(Gdx.files.internal("assets/audio/music"));

        Gdx.input.setInputProcessor(null);  // InputPoller polls directly; ESC handled in render
    }

    @Override
    public void render(float delta) {
        delta = Math.min(delta, MAX_FRAME_TIME);
        if (musicManager != null) musicManager.update(delta);

        // ── Consume slot assignment from SERVER_HELLO ─────────────────────────
        int pendingSlot = stateBuffer.pollPendingLocalSlot();
        if (pendingSlot >= 0) {
            log.info("[GameScreen] Local slot assigned: {}", pendingSlot);
            localSlot = pendingSlot;
        }
        if (stateBuffer.pollScriptedLoss()) {
            scriptedLossOverlay = true;
            scriptedLossCollapseTimer = Math.max(scriptedLossCollapseTimer, 0.85f);
            log.info("[Playtest][ScriptedLoss] received hub={} frame={}",
                prevSnap != null ? prevSnap.hubId : "unknown",
                prevSnap != null ? prevSnap.frame : -1);
        }
        devConsole.processInput();
        syncDevConsoleInputFocus();
        boolean consoleVisible = devConsole.isVisible();
        boolean scriptedLossConsumed = !consoleVisible && handleScriptedLossOverlayInput();

        // ── Overlay input priority: crafting > shop > inventory > dialogue > game
        // Use prevSnap (last frame's snapshot) since this frame's snap hasn't been polled yet.
        PlayerState prevLocal = prevSnap == null ? null : findPlayerBySlot(prevSnap.players, localSlot);
        boolean craftConsumed = false;
        boolean shopConsumed  = false;
        boolean invConsumed   = false;
        if (!scriptedLossConsumed && !consoleVisible) {
            craftConsumed = craftingOverlay.handleInputAndRender(batch, prevLocal, delta);
            shopConsumed  = !craftConsumed && shopOverlay.handleInput(prevLocal);
            invConsumed   = !craftConsumed && !shopConsumed && inventoryOverlay.handleInput();
        }

        // ── Dialogue input (consumes keys when dialogue is open) ─────────────
        boolean dialogueConsumed = !scriptedLossConsumed && !consoleVisible
            && !shopConsumed && !invConsumed && dialogueOverlay.handleInput();
        boolean missionOverlayConsumed = !scriptedLossConsumed && !consoleVisible
            && !craftConsumed && !shopConsumed && !invConsumed
            && !dialogueConsumed
            && missionSelectOverlay.handleInput(storyManager.currentAct().wire());

        // ── I key: toggle inventory (when no other overlay active) ────────────
        if (!consoleVisible && !shopConsumed && !invConsumed && !dialogueConsumed && !missionOverlayConsumed && !paused
                && keyBindings.isJustPressed("inventory")) {
            inventoryOverlay.toggle();
        }
        if (!consoleVisible && !shopConsumed && !invConsumed && !dialogueConsumed && !missionOverlayConsumed && !paused
                && keyBindings.isJustPressed("mission_menu")) {
            openMissionSelectOverlay("hotkey_o");
        }
        // ── TAB key: tap=quick map toggle, hold=full map while held ──────────
        if (!consoleVisible && !shopConsumed && !invConsumed && !dialogueConsumed && !missionOverlayConsumed && !paused) {
            boolean fullMapDown = keyBindings.isHeld("fullmap");
            if (sharedMapBinding) {
                if (fullMapDown) {
                    tabKeyHeldSeconds = tabKeyDownLastFrame ? (tabKeyHeldSeconds + delta) : 0f;
                    if (!fullMapHoldActive && tabKeyHeldSeconds >= TAB_FULL_MAP_HOLD_SECONDS) {
                        minimapRenderer.showFull();
                        fullMapHoldActive = true;
                        log.info("[Playtest][Map] mode=full trigger=map_hold threshold_ms={}",
                            (int) (TAB_FULL_MAP_HOLD_SECONDS * 1000f));
                    }
                } else if (tabKeyDownLastFrame) {
                    if (fullMapHoldActive) {
                        minimapRenderer.hide();
                        log.info("[Playtest][Map] mode=full trigger=map_release close=true");
                    } else {
                        minimapRenderer.toggleQuick();
                        log.info("[Playtest][Map] mode=quick trigger=map_tap visible={}", minimapRenderer.isVisible());
                    }
                    tabKeyHeldSeconds = 0f;
                    fullMapHoldActive = false;
                }
                tabKeyDownLastFrame = fullMapDown;
            } else {
                // Separate bindings: quick-map is edge-triggered, full-map is hold-to-show.
                if (keyBindings.isJustPressed("minimap")) {
                    minimapRenderer.toggleQuick();
                    log.info("[Playtest][Map] mode=quick trigger=minimap_key visible={}", minimapRenderer.isVisible());
                }
                if (fullMapDown && !tabKeyDownLastFrame) {
                    minimapRenderer.showFull();
                    fullMapHoldActive = true;
                    log.info("[Playtest][Map] mode=full trigger=fullmap_key_down");
                } else if (!fullMapDown && tabKeyDownLastFrame && fullMapHoldActive) {
                    minimapRenderer.hide();
                    fullMapHoldActive = false;
                    log.info("[Playtest][Map] mode=full trigger=fullmap_key_up close=true");
                }
                tabKeyDownLastFrame = fullMapDown;
                tabKeyHeldSeconds = 0f;
            }

            // In-map controls (zoom/detail/fog/entities/pan/esc).
            minimapRenderer.handleInput();
        } else {
            tabKeyDownLastFrame = false;
            tabKeyHeldSeconds = 0f;
            fullMapHoldActive = false;
        }

        // ── ESC toggles pause (only when no overlay active) ───────────────────
        boolean anyOverlay = scriptedLossConsumed || craftConsumed || shopConsumed || invConsumed
            || dialogueConsumed || missionOverlayConsumed || consoleVisible;

        // ── H key: toggle hitbox debug overlay ───────────────────────────────
        if (!anyOverlay && !paused && keyBindings.isJustPressed("toggle_hitboxes")) {
            debugHitboxes = !debugHitboxes;
            log.info("[Debug] hitbox overlay {}", debugHitboxes ? "enabled" : "disabled");
        }
        if (!anyOverlay && !paused && keyBindings.isJustPressed("controls_overlay")) {
            showControlsOverlay = !showControlsOverlay;
            log.info("[Debug] controls overlay {}", showControlsOverlay ? "enabled" : "disabled");
        }
        if (!anyOverlay && !paused && keyBindings.isJustPressed("debug_overlay")) {
            showDebugOverlay = !showDebugOverlay;
            log.info("[Debug] telemetry overlay {}", showDebugOverlay ? "enabled" : "disabled");
        }
        // F9: toggle all abilities on/off (solo mode only — playtest helper)
        if (!anyOverlay && !paused && soloMode && Gdx.input.isKeyJustPressed(Input.Keys.F9)) {
            toggleDebugAbilities();
        }
        if (!anyOverlay && keyBindings.isJustPressed("menu_back")) {
            if (paused) resume(); else pause();
        }

        boolean gameplayInputEnabled = !paused
            && !dialogueConsumed
            && !missionOverlayConsumed
            && !scriptedLossConsumed
            && !consoleVisible;

        if (soloReplay != null || !gameplayInputEnabled) {
            clearLatchedRealtimeInput();
        } else {
            latchRealtimeInput(inputPoller.poll());
        }

        if (gameplayInputEnabled) {
            accumulator += delta;
            while (accumulator >= PHYSICS_DT) {
                InputCommand cmd = (soloReplay != null)
                        ? inputForReplayTick(localFrame)
                        : consumeLatchedRealtimeInput();
                if (soloMode) {
                    // Offline: step local sim directly and push snapshot to stateBuffer.
                    if (soloRecorder.isRecording()) soloRecorder.record(localFrame, 0, cmd);
                    soloStepInputs.clear();
                    soloStepInputs.put(0, cmd);
                    localSim.step(soloStepInputs);
                    if (localSim.drainPendingScriptedLoss()) {
                        stateBuffer.markScriptedLoss();
                    }
                    com.indieniinja.network.WorldSnapshot soloSnap = localSim.getSnapshot(localFrame++);
                    stampSoloFields(soloSnap);
                    stateBuffer.update(soloSnap);
                    if (soloReplay != null && soloReplay.isDone(localFrame)) {
                        log.info("[Replay] playback complete at tick {}", localFrame);
                        soloReplay = null;
                        pause();
                    }
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
            lastLoggedStanceMode = null;
            lastLoggedFlowMode = null;
            lastLoggedLanternBand = Integer.MIN_VALUE;
            minimapRenderer.clearState();
            chunkRenderer.loadPlaceholderLayout(LEVEL_COLS, LEVEL_ROWS);
            // Solo: rebuild megamap immediately from the new world graph and snap camera.
            // Must happen AFTER the clear above so cachedWorldRooms is repopulated (not wiped).
            if (soloMode && soloWorldGraph != null) {
                refreshSoloWorldRoomCache();
                if (camera != null) camera.snapTo(soloSpawnX, soloSpawnY);
            }
        }

        WorldSnapshot snap = stateBuffer.poll();
        applyScriptedLossCollapseState(snap, delta);

        // ── Mission timer + auto-save ─────────────────────────────────────────
        missionManager.tick(delta);
        saveManager.tick(delta);

        // ── Audio: state-transition SFX ──────────────────────────────────────
        if (snap != null) tickAudio(snap);

        // ── Mission objective progress (enemy kills, boss defeat) ────────────
        if (snap != null) tickMissionProgress(snap);
        if (snap != null) tickMissionContactVolumes(snap);
        syncMissionTrackerHud();
        tickOnboardingToasts(delta, snap);

        // ── E-key: interact with nearest interactable NPC or portal ─────────────
        if (!anyOverlay && !paused && snap != null
                && keyBindings.isJustPressed("interact")) {
            // Update shop states cache from latest full snapshot
            for (ShopState ss : snap.shopStates) latestShopStates.put(ss.npcId, ss);

            // Check portal interaction first (portals are closer to the player than NPCs typically)
            boolean portalTriggered = false;
            PlayerState localPlayer = findPlayerBySlot(snap.players, localSlot);
            if (localPlayer != null) {
                float pcx = localPlayer.posX + 14f;  // player centre (width=28/2)
                float pcy = localPlayer.posY + 28f;  // player centre (height=56/2)
                for (com.indieniinja.network.PortalState portal : cachedPortals) {
                    if (!portal.isActive) continue;
                    float poCx = portal.x + portal.width  * 0.5f;
                    float poCy = portal.y + portal.height * 0.5f;
                    float dx = pcx - poCx, dy = pcy - poCy;
                    if (dx * dx + dy * dy <= 56f * 56f) {
                        boolean missionExitPortal = missionManager.isActive() && isMissionExitPortal(portal, snap);
                        if (missionExitPortal) {
                            if (missionManager.isExitLocked()) {
                                log.info("[Mission] exit blocked until objectives are complete");
                                portalTriggered = true;
                                break;
                            }
                            missionManager.completeMission();
                            if (saveManager != null) saveManager.markDirty();
                            missionReachedLocations.clear();
                            missionActivatedSwitches.clear();
                            missionTriggerMissionId = "";
                            log.info("[Mission] completed on exit contact before portal travel");
                        }
                        String transitionType = missionExitPortal
                            ? PORTAL_TRANSITION_MISSION_RETURN
                            : PORTAL_TRANSITION_INTER_HUB;
                        if (networkClient == null) {
                            // Solo mode: warp player directly to the destination room
                            // in the unified world-space layout.
                            handleSoloPortalTravel(portal.destinationId, transitionType);
                        } else {
                            // Multiplayer: let the server handle the zone transition.
                            networkClient.sendMessage(com.indieniinja.network.MessageType.PORTAL_TRAVEL,
                                java.util.Map.of(
                                    "destination_id", portal.destinationId,
                                    "transition_type", transitionType
                                ));
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
                    } else if ("mission_giver".equals(closestNpc.npcType)) {
                        openMissionSelectOverlay("npc_mission_giver");
                    } else {
                        String dialogueId = npcDialogueId(closestNpc.npcType, closestNpc.characterId);
                        dialogueManager.setStoryContext(storyManager.toConditionContext());
                        dialogueManager.startNpcDialogue(dialogueId);
                        // Advance TALK_TO_NPC objectives for named characters.
                        // characterId matches the location field in mission objectives
                        // (e.g. "instructor_tai", "samson", "hazel").
                        if (closestNpc.characterId != null && !closestNpc.characterId.isEmpty()) {
                            missionManager.onNpcTalkedTo(closestNpc.characterId);
                        }
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
                PlayerState lp = findPlayerBySlotOrFirst(snap.players, localSlot);
                float px = lp != null ? lp.posX : 0f;
                float py = lp != null ? lp.posY : 0f;
                log.info("[Playtest][Room] changed hub={} ({},{})→({},{}) pos=({}, {})",
                    snap.hubId, prevRoomGridX, prevRoomGridY, snap.roomGridX, snap.roomGridY,
                    (int) px, (int) py);
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

            // ── Zone BGM: trigger cross-fade on hub or act change ─────────────
            if (musicManager != null) {
                String snapHub = snap.hubId != null ? snap.hubId : "";
                int    snapAct = storyManager != null ? storyManager.currentAct().wire() : 0;
                musicManager.playZone(snapHub, snapAct);
            }

            // ── Cache world rooms from full snapshots (empty on delta frames) ──
            if (!snap.worldRooms.isEmpty()) {
                cachedWorldRooms = snap.worldRooms;
            }

            // ── Cache portal list from full snapshots ─────────────────────────
            if (!snap.portals.isEmpty()) {
                cachedPortals = snap.portals;
            }

            logLocalPlaytestState(snap);

            // ── Megamap: build stitched world tilemap when full room list arrives ─
            // Rebuild if: room count changed (new hub) OR stale flag set (zone transition).
            if (!snap.worldRooms.isEmpty() && (megamapStale || snap.worldRooms.size() != megamapRoomCount)) {
                megamapStale = false;
                buildMegamap(snap.worldRooms);
                // Snap camera to player's world-space position directly —
                // entities are in world-space so posX/Y are already the correct target.
                if (!snap.players.isEmpty()) {
                    PlayerState snapLocal = findPlayerBySlotOrFirst(snap.players, localSlot);
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
                        // S5: use biomeIndex from snapshot (set by server from WorldGraph).
                        // biomeFromSeed() is the pre-S5 fallback; snapshot field defaults to 0
                        // for old servers so the terrain stays stable on mixed-version connects.
                        int biomeIdx = snap.biomeIndex > 0
                            ? snap.biomeIndex
                            : BlobTileSet.biomeFromSeed(snap.seed);
                        currentBiomeIndex = biomeIdx;
                        currentTileGrid   = grid2d;
                        chunkRenderer.loadBlobTiles(blobTileSet, biomeIdx, grid2d, LEVEL_COLS, LEVEL_ROWS);
                        parallaxRenderer.loadBiome(
                            parallaxSetFor(biomeIdx),
                            com.badlogic.gdx.Gdx.files.internal("assets"));
                        // S4 — decoration layer (client-side only, never sent over wire)
                        DecorationGenerator.DecoRuleSet decoRules =
                            loadDecoRuleSet(decoSetFor(biomeIdx));
                        byte[][] decoGrid = DecorationGenerator.generate(
                            grid2d, snap.seed, biomeIdx, decoRules, LEVEL_COLS, LEVEL_ROWS);
                        chunkRenderer.loadDecoMap(decoGrid, blobTileSet, biomeIdx);
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
                PlayerState local = findPlayerBySlotOrFirst(snap.players, localSlot);
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

        // Pass 0b — parallax background (S3): screen-space strips behind all world content.
        // ParallaxRenderer wraps its own begin/end and restores the projection afterward.
        parallaxRenderer.render(batch, camera);

        // Pass 1 — tiles: megamap tiles are already in world-space coords, identity transform.
        batch.setProjectionMatrix(camera.cam.combined);
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
                } else if ("mission_switch_fallback".equals(v.source)) {
                    hitboxRenderer.setColor(1.00f, 0.20f, 0.25f, 1f);
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

        // ── Minimap overlay (quick/full modes) ───────────────────────────────
        if (minimapRenderer.isVisible() && !cachedWorldRooms.isEmpty()) {
            WorldSnapshot snapForMap = snap != null ? snap : prevSnap;
            PlayerState localForMap = snapForMap != null
                ? findPlayerBySlotOrFirst(snapForMap.players, localSlot)
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
            java.util.List<com.indieniinja.client.ui.MinimapRenderer.ObjectiveMarker> objectiveMarkers =
                buildMinimapObjectiveMarkers();
            batch.setProjectionMatrix(hudRenderer.screenProjection());
            // MinimapRenderer manages its own batch.begin/end; do NOT open batch here.
            minimapRenderer.render(batch, cachedWorldRooms, gridX, gridY, lpx, lpy, roomPx, roomPy,
                cachedTileGrids, visitedRooms, snapForMap,
                cachedEnemies, cachedPickups, cachedPortals, localSlot, objectiveMarkers);
            batch.setProjectionMatrix(camera.cam.combined);
        }

        // ── Inventory overlay (screen-space, centre) ──────────────────────────
        if (inventoryOverlay.isVisible() && snap != null) {
            PlayerState localInv = findPlayerBySlotOrFirst(snap.players, localSlot);
            batch.setProjectionMatrix(hudRenderer.screenProjection());
            batch.begin();
            inventoryOverlay.render(batch, localInv);
            batch.end();
            batch.setProjectionMatrix(camera.cam.combined);
        }

        // ── Shop overlay (screen-space, centre) ───────────────────────────────
        if (shopOverlay.isVisible() && snap != null) {
            PlayerState localShop = findPlayerBySlotOrFirst(snap.players, localSlot);
            batch.setProjectionMatrix(hudRenderer.screenProjection());
            batch.begin();
            shopOverlay.render(batch, localShop);
            batch.end();
            batch.setProjectionMatrix(camera.cam.combined);
        }

        // ── Death / respawn overlay ───────────────────────────────────────────
        if (snap != null) {
            PlayerState localPlayer = findPlayerBySlot(snap.players, localSlot);
            if (localPlayer != null && localPlayer.isDead) {
                hudRenderer.renderDeathOverlay(localPlayer.respawnTimer);
            }
        }

        if (scriptedLossOverlay) {
            hudRenderer.renderScriptedLossOverlay();
        }
        if (showControlsOverlay) {
            hudRenderer.renderControlsOverlay(keyBindings);
        }
        if (showDebugOverlay) {
            hudRenderer.renderDebugOverlay(snap, localSlot, soloMode || stateBuffer.isConnected(), gameMode);
        }

        // ── Pause overlay (rendered on top) ───────────────────────────────────
        if (paused) {
            pauseScreen.render(delta);
        }

        // ── Dev console (topmost layer — always rendered last) ────────────────
        batch.setProjectionMatrix(hudRenderer.screenProjection());
        int sw = Gdx.graphics.getWidth();
        int sh = Gdx.graphics.getHeight();
        devConsole.render(batch, sw, sh);
        devConsole.renderFpsOverlay(batch, sw, sh);

        // ── Persist snapshot for next frame's overlay input handling ──────────
        if (snap != null) prevSnap = snap;
    }

    private boolean handleScriptedLossOverlayInput() {
        if (!scriptedLossOverlay) return false;
        boolean continuePressed =
            keyBindings.isJustPressed("menu_confirm")
                || Gdx.input.isKeyJustPressed(Input.Keys.SPACE)
                || (Gdx.input.justTouched()
                    && hudRenderer.scriptedLossButtonHit(Gdx.input.getX(), Gdx.input.getY()));
        if (continuePressed) {
            scriptedLossOverlay = false;
            scriptedLossCollapseTimer = 0f;
            storyManager.onVeilMaidenDefeatedAct1();
            dialogueManager.setStoryContext(storyManager.toConditionContext());
            log.info("[Playtest][ScriptedLoss] continue hub={} act={}",
                prevSnap != null ? prevSnap.hubId : "unknown",
                storyManager.currentAct().wire());
        }
        return true;
    }

    private void applyScriptedLossCollapseState(WorldSnapshot snap, float delta) {
        if (scriptedLossCollapseTimer > 0f) {
            scriptedLossCollapseTimer = Math.max(0f, scriptedLossCollapseTimer - Math.max(0f, delta));
        }
        if (snap == null || scriptedLossCollapseTimer <= 0f || snap.players == null || snap.players.isEmpty()) {
            return;
        }
        PlayerState local = findPlayerBySlotOrFirst(snap.players, localSlot);
        if (local == null || local.isDead) return;
        local.animState = "collapse";
    }

    private void startMissionFlow(String missionId, String source) {
        if (missionId == null || missionId.isBlank()) return;
        MissionDefinition def = missionManager.getDefinition(missionId);
        if (def == null) {
            log.warn("[Mission] start ignored for unknown mission id '{}'", missionId);
            return;
        }

        clearPriorMultiplayerMissionPickupContractOnMissionSwitch(missionId);
        missionManager.startMission(missionId);
        multiplayerMissionPickupSeedMissionId = "";
        java.util.Map<String, Integer> objectiveItemCounts = collectMissionObjectiveItemCounts(def);
        if (soloMode) {
            rebuildSoloWorldForMission(def, objectiveItemCounts);
        } else {
            requestMultiplayerMissionObjectivePickups(def, objectiveItemCounts);
        }
        missionReachedLocations.clear();
        missionActivatedSwitches.clear();
        missionTriggerMissionId = missionId;
        lastMissionToastId = missionId;

        hudRenderer.notifyToast("MISSION STARTED: " + def.missionName);
        if (saveManager != null) saveManager.markDirty();
        log.info("[Mission] started via {}: {} (rooms={}, shape={})",
            source, missionId, def.roomCount, def.shape);
    }

    /**
     * Mission switch hardening for hosted sessions.
     * Consecutive mission starts (A -> B) must clear any prior mission pickup
     * contract first so late-join/rejoin cannot reseed A in B's lifecycle.
     */
    private void clearPriorMultiplayerMissionPickupContractOnMissionSwitch(String nextMissionId) {
        if (soloMode || networkClient == null) return;

        String priorContractMissionId = normalizeKey(multiplayerMissionPickupSeedMissionId);
        if (priorContractMissionId.isBlank()) {
            priorContractMissionId = normalizeKey(missionManager.getActiveMissionId());
        }
        if (priorContractMissionId.isBlank()) return;

        String nextId = normalizeKey(nextMissionId);
        String reason = priorContractMissionId.equals(nextId)
            ? "mission_restart"
            : "mission_switch_start";
        requestMultiplayerMissionObjectivePickupClear(priorContractMissionId, reason);
    }

    private void rebuildSoloWorldForMission(MissionDefinition def, java.util.Map<String, Integer> objectiveItemCounts) {
        if (!soloMode || def == null) return;
        int targetRooms = targetRoomCountForAct(def);
        WorldGraph.WorldShape shape = parseWorldShape(def.shape);
        long seed = System.currentTimeMillis();
        initializeSoloSimulation(seed, Boolean.getBoolean("ninja.record"), targetRooms, shape);
        seedSoloMissionObjectivePickups(def, objectiveItemCounts);
        refreshSoloWorldRoomCache();
        hudRenderer.notifyToast("WORLD BUILT: " + targetRooms + " ROOMS");
    }

    private java.util.Map<String, Integer> collectMissionObjectiveItemCounts(MissionDefinition def) {
        java.util.Map<String, Integer> requiredByItem = new java.util.LinkedHashMap<>();
        if (def == null || def.objectives == null) return requiredByItem;

        for (MissionObjective obj : def.objectives) {
            if (obj == null || obj.type != ObjectiveType.COLLECT_ITEMS) continue;
            String itemId = normalizeKey(obj.item);
            if (itemId.isBlank() || "coin".equals(itemId)) continue;
            requiredByItem.merge(itemId, objectiveTarget(obj), Integer::sum);
        }
        return requiredByItem;
    }

    private void requestMultiplayerMissionObjectivePickups(
        MissionDefinition def,
        java.util.Map<String, Integer> objectiveItemCounts
    ) {
        if (soloMode || networkClient == null || def == null) return;
        if (objectiveItemCounts == null || objectiveItemCounts.isEmpty()) return;

        java.util.Map<String, Object> payload = new java.util.LinkedHashMap<>();
        payload.put("event", ENTITY_EVENT_MISSION_SEED_PICKUPS);
        payload.put("request_id", java.util.UUID.randomUUID().toString());
        String missionId = normalizeKey(def.missionId);
        payload.put("mission_id", missionId);
        payload.put("item_counts", new java.util.LinkedHashMap<>(objectiveItemCounts));
        networkClient.sendMessage(com.indieniinja.network.MessageType.ENTITY_EVENT, payload);
        multiplayerMissionPickupSeedMissionId = missionId;
        log.info("[Mission] requested multiplayer objective pickups for {}: {}",
            def.missionId, objectiveItemCounts);
    }

    private void requestMultiplayerMissionObjectivePickupClear(String missionId, String reason) {
        if (soloMode || networkClient == null) return;
        String normalizedMissionId = normalizeKey(missionId);
        if (normalizedMissionId.isBlank()) return;

        java.util.Map<String, Object> payload = new java.util.LinkedHashMap<>();
        payload.put("event", ENTITY_EVENT_MISSION_SEED_PICKUPS_CLEAR);
        payload.put("mission_id", normalizedMissionId);
        payload.put("reason", reason == null ? "" : reason);
        networkClient.sendMessage(com.indieniinja.network.MessageType.ENTITY_EVENT, payload);
        log.info("[Mission] cleared multiplayer objective pickup contract for {} via {}",
            normalizedMissionId, reason);
    }

    /**
     * Ensure collect_items mission objectives always have pickup sources in solo worlds.
     * These mission pickups are persistent (no timed despawn) to prevent soft locks.
     */
    private void seedSoloMissionObjectivePickups(
        MissionDefinition def,
        java.util.Map<String, Integer> objectiveItemCounts
    ) {
        if (!soloMode || def == null || localSim == null) return;
        java.util.Map<String, Integer> requiredByItem =
            objectiveItemCounts == null
                ? collectMissionObjectiveItemCounts(def)
                : objectiveItemCounts;
        if (requiredByItem.isEmpty()) return;

        java.util.List<float[]> anchors = new java.util.ArrayList<>();
        for (com.indieniinja.sim.SimPickup pickup : localSim.getPickups()) {
            if (pickup == null || !pickup.alive) continue;
            anchors.add(new float[]{pickup.x, pickup.y});
        }

        SimPlayer player = localSim.getPlayer(0);
        float originX = player != null
            ? player.physics.x + player.physics.width * 0.5f
            : soloSpawnX;
        float originY = player != null ? player.physics.y : soloSpawnY;

        int anchorIndex = 0;
        int seededCount = 0;
        for (var entry : requiredByItem.entrySet()) {
            String itemId = entry.getKey();
            int count = Math.max(1, entry.getValue());
            for (int i = 0; i < count; i++) {
                float spawnX;
                float spawnY;
                if (anchorIndex < anchors.size()) {
                    float[] anchor = anchors.get(anchorIndex);
                    spawnX = anchor[0];
                    spawnY = anchor[1];
                } else {
                    int extraIdx = anchorIndex - anchors.size();
                    int ring = 1 + (extraIdx / 8);
                    int spoke = extraIdx % 8;
                    float angle = (float) ((Math.PI * 2.0 * spoke) / 8.0);
                    float radius = 72f + ring * 40f;
                    spawnX = originX + (float) Math.cos(angle) * radius;
                    spawnY = originY + 12f + ((ring & 1) == 0 ? 0f : 10f);
                }
                localSim.addPersistentPickup(itemId, spawnX, spawnY);
                anchorIndex++;
                seededCount++;
            }
        }

        log.info("[Mission] seeded {} persistent objective pickup(s) for mission {}: {}",
            seededCount, def.missionId, requiredByItem);
    }

    private int targetRoomCountForAct(MissionDefinition def) {
        int authored = def != null ? Math.max(1, def.roomCount) : 12;
        int actWire = storyManager != null ? storyManager.currentAct().wire() : 0;
        if (actWire <= 1) {
            return clampInt(authored, 4, 9);   // Act I/II onboarding scale
        }
        return clampInt(authored, 12, 60);     // Act III+ expanded mission worlds
    }

    private static WorldGraph.WorldShape parseWorldShape(String shapeWire) {
        if (shapeWire == null || shapeWire.isBlank()) return WorldGraph.WorldShape.BLOB;
        try {
            return WorldGraph.WorldShape.valueOf(shapeWire.trim().toUpperCase(java.util.Locale.ROOT));
        } catch (IllegalArgumentException ex) {
            return WorldGraph.WorldShape.BLOB;
        }
    }

    private void openMissionSelectOverlay(String reason) {
        if (missionSelectOverlay == null || missionSelectOverlay.isVisible()) return;
        inventoryOverlay.hide();
        shopOverlay.hide();
        craftingOverlay.close();
        dialogueManager.setStoryContext(storyManager.toConditionContext());
        missionSelectOverlay.open(storyManager.currentAct().wire());
        log.info("[Mission] opened mission select overlay via {}", reason);
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
            missionActivatedSwitches.clear();
            missionContactVolumes.clear();
            return;
        }

        if (!activeMissionId.equals(missionTriggerMissionId)) {
            missionTriggerMissionId = activeMissionId;
            missionReachedLocations.clear();
            missionActivatedSwitches.clear();
        }

        MissionDefinition def = missionManager.getActiveDefinition();
        if (def == null) return;

        PlayerState local = findPlayerBySlot(snap.players, localSlot);
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
                log.info(
                    "[Mission] location reached: {} (mission {}) hub={} room=({}, {}) pos=({}, {})",
                    loc, activeMissionId, snap.hubId, snap.roomGridX, snap.roomGridY,
                    (int) px, (int) py);
            }
        }

        boolean interactPressed = keyBindings.isJustPressed("interact")
            || keyBindings.isJustPressed("throw");
        if (interactPressed) {
            int requiredSwitches = requiredSwitchActivationCount(def);
            for (int i = 1; i <= requiredSwitches; i++) {
                String switchTag = normalizeKey(activeMissionId) + ":switch_" + i;
                if (missionActivatedSwitches.contains(switchTag)) continue;
                if (playerOverlapsVolume(switchTag, px, py)) {
                    missionManager.onSwitchActivated(switchTag);
                    missionActivatedSwitches.add(switchTag);
                    log.info(
                        "[Mission] fallback switch activated: {} hub={} room=({}, {}) pos=({}, {})",
                        switchTag, snap.hubId, snap.roomGridX, snap.roomGridY, (int) px, (int) py);
                }
            }
        }

        if (!missionManager.isExitLocked() && playerOverlapsVolume("exit", px, py)) {
            missionManager.completeMission();
            if (saveManager != null) saveManager.markDirty();
            missionReachedLocations.clear();
            missionActivatedSwitches.clear();
            missionTriggerMissionId = "";
            log.info(
                "[Mission] completed by reaching exit contact volume hub={} room=({}, {}) pos=({}, {})",
                snap.hubId, snap.roomGridX, snap.roomGridY, (int) px, (int) py);
        }
    }

    private void syncMissionTrackerHud() {
        MissionDefinition def = missionManager.getActiveDefinition();
        if (def == null) {
            hudRenderer.clearMissionTracker();
            return;
        }

        java.util.Map<String, Integer> progress = missionManager.getObjectiveProgressView();
        missionTrackerLinesScratch.clear();
        float missionTimer = missionManager.getMissionTimer();

        for (MissionObjective obj : def.objectives) {
            if (obj == null || obj.type == null) continue;
            missionTrackerLinesScratch.add(formatObjectiveLine(def, obj, progress, missionTimer));
        }

        hudRenderer.setMissionTracker(def.missionName, missionTrackerLinesScratch,
            missionManager.isExitLocked(), missionTimer);
    }

    private String formatObjectiveLine(
        MissionDefinition def,
        MissionObjective obj,
        java.util.Map<String, Integer> progress,
        float missionTimer
    ) {
        boolean done = isObjectiveComplete(def, obj, progress, missionTimer);
        String base = (obj.description != null && !obj.description.isBlank())
            ? obj.description
            : switch (obj.type) {
                case COLLECT_ITEMS -> "Collect " + (obj.item == null ? "items" : obj.item);
                case KILL_ALL_ENEMIES -> "Defeat enemies";
                case ACTIVATE_SWITCHES -> "Activate switches";
                case REACH_LOCATION -> "Reach " + (obj.location == null ? "target" : obj.location);
                case DEFEAT_BOSS -> "Defeat boss";
                case TIME_CHALLENGE -> "Beat timer";
                case TALK_TO_NPC -> "Speak with " + (obj.location == null ? "NPC" : obj.location);
            };

        String suffix = "";
        if (obj.type == ObjectiveType.TIME_CHALLENGE) {
            float limit = obj.timeLimit > 0f ? obj.timeLimit : def.timeLimit;
            float remaining = Math.max(0f, limit - missionTimer);
            suffix = " (" + formatClock(remaining) + " left)";
        } else {
            int target = objectiveTarget(obj);
            int current = progress.getOrDefault(objectiveKeyForHud(obj), 0);
            if (obj.type == ObjectiveType.REACH_LOCATION || obj.type == ObjectiveType.DEFEAT_BOSS) {
                suffix = done ? " (done)" : " (pending)";
            } else if (target > 1) {
                suffix = " (" + Math.min(current, target) + "/" + target + ")";
            }
        }
        return (done ? "[x] " : "[ ] ") + base + suffix;
    }

    private boolean isObjectiveComplete(
        MissionDefinition def,
        MissionObjective obj,
        java.util.Map<String, Integer> progress,
        float missionTimer
    ) {
        if (obj.type == ObjectiveType.TIME_CHALLENGE) {
            float limit = obj.timeLimit > 0f ? obj.timeLimit : def.timeLimit;
            return limit <= 0f || missionTimer <= limit;
        }
        int current = progress.getOrDefault(objectiveKeyForHud(obj), 0);
        return current >= objectiveTarget(obj);
    }

    private int objectiveTarget(MissionObjective obj) {
        return switch (obj.type) {
            case COLLECT_ITEMS     -> Math.max(1, obj.count);
            case KILL_ALL_ENEMIES  -> Math.max(1, obj.target);
            case ACTIVATE_SWITCHES -> Math.max(1, obj.count > 0 ? obj.count : obj.target);
            case REACH_LOCATION,
                 DEFEAT_BOSS,
                 TIME_CHALLENGE,
                 TALK_TO_NPC       -> 1;
        };
    }

    private String objectiveKeyForHud(MissionObjective obj) {
        return switch (obj.type) {
            case COLLECT_ITEMS  -> objectiveKey(obj.type, obj.item);
            case REACH_LOCATION -> objectiveKey(obj.type, obj.location);
            case DEFEAT_BOSS    -> objectiveKey(obj.type, obj.boss);
            default             -> objectiveKey(obj.type, null);
        };
    }

    private String objectiveKey(ObjectiveType type, String qualifier) {
        String q = qualifier == null ? "" : normalizeKey(qualifier);
        return type.name().toLowerCase(java.util.Locale.ROOT) + "_" + q;
    }

    private void tickOnboardingToasts(float delta, WorldSnapshot snap) {
        if (hudRenderer == null || snap == null) return;

        String activeMission = missionManager.getActiveMissionId();
        if (activeMission == null || activeMission.isBlank()) {
            lastMissionToastId = "";
        } else if (!activeMission.equals(lastMissionToastId)) {
            MissionDefinition def = missionManager.getActiveDefinition();
            if (def != null) {
                hudRenderer.notifyToast("MISSION STARTED: " + def.missionName);
            }
            lastMissionToastId = activeMission;
        }

        if (onboardingToastStage >= 3) return;
        onboardingToastCooldown -= delta;
        if (onboardingToastCooldown > 0f) return;

        switch (onboardingToastStage) {
            case 0 -> hudRenderer.notifyToast("ACT I ONBOARDING: PRESS F1 FOR CONTROLS.");
            case 1 -> hudRenderer.notifyToast("PRESS O TO OPEN MISSION BOARD. NPCS WITH ! ARE INTERACTABLE.");
            case 2 -> hudRenderer.notifyToast("TRACK OBJECTIVES ON THE TOP-RIGHT PANEL. TAB OPENS MINIMAP.");
            default -> { }
        }
        log.info("[Onboarding] toast stage={} shown", onboardingToastStage);
        onboardingToastStage++;
        onboardingToastCooldown = 4.0f;
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

        appendFallbackSwitchVolumes(snap, def, activeMissionId);
    }

    private java.util.List<com.indieniinja.client.ui.MinimapRenderer.ObjectiveMarker> buildMinimapObjectiveMarkers() {
        minimapObjectiveMarkersScratch.clear();
        if (!missionManager.isActive() || missionContactVolumes.isEmpty()) return minimapObjectiveMarkersScratch;
        for (MissionContactVolume v : missionContactVolumes) {
            if (v == null) continue;
            String id = normalizeKey(v.id);
            if ("exit".equals(id) && missionManager.isExitLocked()) {
                continue; // reduce noise until objective gate opens
            }
            if (missionReachedLocations.contains(id)) continue;
            if (missionActivatedSwitches.contains(id)) continue;

            String markerType;
            if ("exit".equals(id)) markerType = "exit";
            else if ("mission_switch_fallback".equals(v.source) || id.contains(":switch_")) markerType = "switch";
            else markerType = "reach";

            float cx = v.x + v.width * 0.5f;
            float cy = v.y + v.height * 0.5f;
            minimapObjectiveMarkersScratch.add(
                new com.indieniinja.client.ui.MinimapRenderer.ObjectiveMarker(cx, cy, markerType));
        }
        return minimapObjectiveMarkersScratch;
    }

    private int requiredSwitchActivationCount(MissionDefinition def) {
        if (def == null) return 0;
        int total = 0;
        for (MissionObjective obj : def.objectives) {
            if (obj.type != ObjectiveType.ACTIVATE_SWITCHES) continue;
            total += Math.max(1, obj.count > 0 ? obj.count : obj.target);
        }
        return total;
    }

    private void appendFallbackSwitchVolumes(WorldSnapshot snap, MissionDefinition def, String activeMissionId) {
        int required = requiredSwitchActivationCount(def);
        if (required <= 0) return;

        // Preserve authored world interactions when present.
        boolean hasAuthoredSwitchNpc = false;
        for (NPCState npc : snap.npcs) {
            if (npc == null || npc.npcType == null) continue;
            if (npc.npcType.startsWith("btn_") || npc.npcType.startsWith("lever_")) {
                hasAuthoredSwitchNpc = true;
                break;
            }
        }
        if (hasAuthoredSwitchNpc) return;

        int roomGridX = snap.roomGridX;
        int roomGridY = snap.roomGridY;
        byte[][] grid = tileGridForRoom(roomGridX, roomGridY);
        int tile = PhysicsConstants.TILE_SIZE;
        float roomPxX = LEVEL_COLS * tile;
        float roomPxY = LEVEL_ROWS * tile;
        float roomOriginX = (roomGridX - megamapMinGridX) * roomPxX;
        float roomOriginY = (roomGridY - megamapMinGridY) * roomPxY;

        for (int i = 0; i < required; i++) {
            float fraction = (i + 1f) / (required + 1f);
            int anchorCol = clampInt(Math.round(fraction * (LEVEL_COLS - 1)), 0, LEVEL_COLS - 1);
            int anchorRow = LEVEL_ROWS - 2;
            int[] cell = grid != null
                ? findNearestReachableGroundCell(grid, anchorRow, anchorCol, Math.max(LEVEL_COLS, LEVEL_ROWS))
                : null;
            if (cell == null) {
                cell = new int[] { clampInt(LEVEL_ROWS - 2, 1, LEVEL_ROWS - 1), anchorCol };
            }

            float width = 24f;
            float height = 40f;
            float x = roomOriginX + cell[1] * tile + (tile - width) * 0.5f;
            float y = roomOriginY + cell[0] * tile - height;
            String switchTag = normalizeKey(activeMissionId) + ":switch_" + (i + 1);
            missionContactVolumes.add(clampVolumeToRoom(
                new MissionContactVolume(switchTag, x, y, width, height, "mission_switch_fallback"),
                roomGridX, roomGridY));
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
            || tile == WorldGenerator.CLIMBABLE
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

    private static String formatClock(float seconds) {
        int total = Math.max(0, (int) seconds);
        int mins = total / 60;
        int secs = total % 60;
        return String.format(java.util.Locale.ROOT, "%02d:%02d", mins, secs);
    }

    private boolean isMissionExitPortal(com.indieniinja.network.PortalState portal, WorldSnapshot snap) {
        if (portal == null || snap == null) return false;
        if ("exit".equalsIgnoreCase(snap.roomType)) return true;
        return "hub".equalsIgnoreCase(portal.portalType);
    }

    // ── Solo-mode helpers ─────────────────────────────────────────────────────

    private void initializeSoloSimulation(long seed, boolean startRecording) {
        initializeSoloSimulation(seed, startRecording, 10, WorldGraph.WorldShape.BLOB, "lantern_heights");
    }

    private void initializeSoloSimulation(
        long seed, boolean startRecording, int roomCount, WorldGraph.WorldShape worldShape
    ) {
        initializeSoloSimulation(seed, startRecording, roomCount, worldShape, "lantern_heights");
    }

    private void initializeSoloSimulation(
        long seed, boolean startRecording, int roomCount, WorldGraph.WorldShape worldShape, String hubId
    ) {
        soloSeed = seed;
        String resolvedHubId = (hubId == null || hubId.isBlank()) ? "central_hub" : hubId;
        int generatedRoomCount = clampInt(roomCount, 4, 60);
        WorldGraph.WorldShape shape = worldShape == null ? WorldGraph.WorldShape.BLOB : worldShape;
        soloWorldGraph = WorldGraph.generate(seed, generatedRoomCount, shape);
        WorldGraph.RoomNode startRoom = soloWorldGraph.startRoom();
        soloCurrentGridX = startRoom.gridX;
        soloCurrentGridY = startRoom.gridY;
        soloRoomType     = startRoom.type.wire();
        soloNeighborDirs = new java.util.ArrayList<>(startRoom.neighborDirs());

        LevelLayout layout = LevelLayout.buildUnifiedWorldLayout(soloWorldGraph, resolvedHubId);
        localSim = new GameSimulator(startRoom.seed, resolvedHubId, layout);
        localSim.setContentRegistry(clientContentRegistry);
        devConsole.setSimulator(localSim);
        localSim.setMode(com.indieniinja.sim.GameMode.CAMPAIGN, 0, 0);
        localSim.setDarkArea(true);  // solo dungeon is always dark — lantern decays
        soloSpawnX = layout.spawnX;
        soloSpawnY = layout.spawnY;

        SimPlayer player = new SimPlayer("solo_player", 0, layout.spawnX, layout.spawnY);
        localSim.addPlayer(player);

        if (startRecording && Boolean.getBoolean("ninja.record")) {
            soloRecorder.startRecording(soloSeed);
        }

        localFrame = 0;
        loadedSeed = Long.MIN_VALUE;
        loadedNeighborDirs = java.util.List.of();
        prevRoomGridX = Integer.MIN_VALUE;
        prevRoomGridY = Integer.MIN_VALUE;
        prevEnemyIds.clear();
        prevBossAlive.clear();
        prevInventoryTotals.clear();
        prevInventoryCurrency = 0;
        prevInventoryBaselineReady = false;
        prevLocalAbilities.clear();
        missionReachedLocations.clear();
        missionActivatedSwitches.clear();
        missionTriggerMissionId = "";

        WorldSnapshot initSnap = localSim.getSnapshot(localFrame++);
        stampSoloFields(initSnap);
        if (stateBuffer != null) {
            stateBuffer.update(initSnap);
            stateBuffer.markConnected();
        }
    }

    private void refreshSoloWorldRoomCache() {
        if (soloWorldGraph == null || chunkRenderer == null) return;
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
        if (visitedRooms.isEmpty()) {
            WorldGraph.RoomNode startRoom = soloWorldGraph.startRoom();
            visitedRooms.add(startRoom.gridX + "," + startRoom.gridY);
        }
    }

    private void restoreSoloRuntimeStateFromSave() {
        if (!soloMode || saveManager == null || !saveManager.hasSave()) return;
        com.indieniinja.client.game.SaveData save = saveManager.getSaveData();
        if (save == null) return;

        if (save.worldSeed != 0 && save.worldSeed != soloSeed) {
            log.info("[Save] restoring solo world seed: {} -> {}", soloSeed, save.worldSeed);
            initializeSoloSimulation(save.worldSeed, Boolean.getBoolean("ninja.record"));
            refreshSoloWorldRoomCache();
        }

        if (save.visitedRoomKeys != null && !save.visitedRoomKeys.isEmpty()) {
            visitedRooms.clear();
            for (String key : save.visitedRoomKeys) {
                if (key == null || key.isBlank()) continue;
                visitedRooms.add(key.trim());
            }
        }

        restoreSoloPlayerFromSave(save);
        restoreMissionReachProgressFromSave();

        WorldSnapshot snap = localSim.getSnapshot(localFrame++);
        stampSoloFields(snap);
        stateBuffer.update(snap);
    }

    private void restoreSoloPlayerFromSave(com.indieniinja.client.game.SaveData save) {
        if (localSim == null || save == null) return;
        SimPlayer sp = localSim.getPlayer(0);
        if (sp == null) return;

        // Restore inventory totals from save map.
        for (int i = 0; i < sp.inventory.slots.length; i++) {
            sp.inventory.slots[i] = null;
        }
        sp.inventory.currency = Math.max(0, Math.min(com.indieniinja.sim.SimInventory.MAX_CURRENCY, save.currency));
        sp.inventory.equippedWeapon = null;
        sp.inventory.equippedArmor = null;
        if (save.playerInventory != null) {
            java.util.List<String> itemIds = new java.util.ArrayList<>(save.playerInventory.keySet());
            itemIds.sort(String::compareTo);
            for (String itemId : itemIds) {
                Integer qty = save.playerInventory.get(itemId);
                if (itemId == null || itemId.isBlank() || qty == null || qty <= 0) continue;
                if (!sp.inventory.addItem(itemId, qty)) {
                    log.warn("[Save] failed to fully restore inventory item {} x{}", itemId, qty);
                }
            }
        }
        if (save.equippedWeapon != null && !save.equippedWeapon.isBlank()) {
            sp.inventory.equipItem(save.equippedWeapon);
        }
        if (save.equippedArmor != null && !save.equippedArmor.isBlank()) {
            sp.inventory.equipItem(save.equippedArmor);
        }

        sp.unlockedAbilities.clear();
        if (save.unlockedAbilities != null) {
            for (String ability : save.unlockedAbilities) {
                if (ability == null || ability.isBlank()) continue;
                sp.unlockedAbilities.add(ability);
            }
        }
        sp.weaponState = weaponStateFromEquippedItem(sp.inventory.equippedWeapon);

        boolean sameHub = save.currentHubId == null
            || save.currentHubId.isBlank()
            || localSim.hubId.equalsIgnoreCase(save.currentHubId);
        boolean hasSavedPosition = save.currentHubX != 0f || save.currentHubY != 0f;
        if (sameHub && hasSavedPosition) {
            float worldPxW = megamapW * PhysicsConstants.TILE_SIZE;
            float worldPxH = megamapH * PhysicsConstants.TILE_SIZE;
            float maxX = Math.max(0f, worldPxW - sp.physics.width);
            float maxY = Math.max(0f, worldPxH - sp.physics.height);
            sp.physics.x = clampFloat(save.currentHubX, 0f, maxX);
            sp.physics.y = clampFloat(save.currentHubY, 0f, maxY);
            sp.physics.vx = 0f;
            sp.physics.vy = 0f;
        }
    }

    private void restoreMissionReachProgressFromSave() {
        missionReachedLocations.clear();
        missionActivatedSwitches.clear();
        String activeMissionId = missionManager.getActiveMissionId();
        missionTriggerMissionId = activeMissionId == null ? "" : activeMissionId;
        if (activeMissionId == null || activeMissionId.isBlank()) return;
        MissionDefinition def = missionManager.getActiveDefinition();
        if (def == null) return;
        java.util.Map<String, Integer> progress = missionManager.getObjectiveProgressSnapshot();
        for (MissionObjective obj : def.objectives) {
            if (obj.type != ObjectiveType.REACH_LOCATION || obj.location == null || obj.location.isBlank()) continue;
            String loc = normalizeKey(obj.location);
            String key = "reach_location_" + loc;
            if (progress.getOrDefault(key, 0) > 0) {
                missionReachedLocations.add(loc);
            }
        }
        int requiredSwitches = requiredSwitchActivationCount(def);
        for (int i = 1; i <= requiredSwitches; i++) {
            String tag = normalizeKey(activeMissionId) + ":switch_" + i;
            String key = "activate_switches_" + tag;
            if (progress.getOrDefault(key, 0) > 0) {
                missionActivatedSwitches.add(tag);
            }
        }
    }

    private static String weaponStateFromEquippedItem(String equippedWeapon) {
        if (equippedWeapon == null || equippedWeapon.isBlank()) return "unarmed";
        String id = equippedWeapon.toLowerCase(java.util.Locale.ROOT);
        if (id.contains("pistol")) return "pistol";
        return "sword";
    }

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
     * Solo portal travel mirrors the server-side handlePortalTravel() flow: ability
     * gate check, player state snapshot, hub re-initialisation, state restore, zone
     * transition signal, and save mark — so the campaign experience is identical
     * whether played alone or with friends.
     */

    // ── Debug helpers ─────────────────────────────────────────────────────────

    private static final java.util.List<String> ALL_ABILITIES = java.util.List.of(
        "double_jump", "dash", "wall_jump", "shuriken", "teleport", "ninjutsu"
    );

    /** F9: cycles through all-abilities-on → all-abilities-off for fast playtest iteration. */
    private void toggleDebugAbilities() {
        if (localSim == null) return;
        com.indieniinja.sim.SimPlayer sp = localSim.getPlayer(0);
        if (sp == null) return;
        boolean allUnlocked = sp.unlockedAbilities.containsAll(ALL_ABILITIES);
        if (allUnlocked) {
            sp.unlockedAbilities.clear();
            prevLocalAbilities.clear();
            hudRenderer.notifyToast("[F9] All abilities removed");
            log.info("[Debug][F9] abilities cleared");
        } else {
            sp.unlockedAbilities.addAll(ALL_ABILITIES);
            prevLocalAbilities.addAll(ALL_ABILITIES);
            hudRenderer.notifyToast("[F9] All abilities granted");
            log.info("[Debug][F9] abilities granted: {}", ALL_ABILITIES);
        }
    }
    private static String normalizePortalTransitionType(String rawType) {
        if (PORTAL_TRANSITION_MISSION_RETURN.equals(rawType)) return PORTAL_TRANSITION_MISSION_RETURN;
        return PORTAL_TRANSITION_INTER_HUB;
    }

    private String soloSpawnRoomId(String hubId) {
        return hubId + ":" + soloCurrentGridX + ":" + soloCurrentGridY;
    }

    private void handleSoloPortalTravel(String destinationId) {
        handleSoloPortalTravel(destinationId, PORTAL_TRANSITION_INTER_HUB);
    }

    private void handleSoloPortalTravel(String destinationId, String transitionType) {
        if (localSim == null) return;
        com.indieniinja.sim.SimPlayer sp = localSim.getPlayer(0);
        if (sp == null) return;
        String normalizedTransitionType = normalizePortalTransitionType(transitionType);
        String originHubId = (soloCurrentHubId == null || soloCurrentHubId.isBlank())
            ? "unknown_hub"
            : soloCurrentHubId;

        com.indieniinja.world.HubRegistry.HubDef hubDef =
            com.indieniinja.world.HubRegistry.get(destinationId);

        // Ability gate — mirrors ServerProtocolHandler.handlePortalTravel() check.
        if (!hubDef.isAccessible(sp.unlockedAbilities)) {
            String req = hubDef.requiredAbility().replace('_', ' ').toUpperCase();
            if (hudRenderer != null) hudRenderer.notifyToast("PORTAL LOCKED: REQUIRES " + req);
            log.info(
                "[GameScreen][Playtest][Portal] solo portal denied type={} origin_hub_id={} destination_hub_id={} required_ability={}",
                normalizedTransitionType, originHubId, destinationId, hubDef.requiredAbility()
            );
            return;
        }

        // Snapshot player state before re-initialising the simulation.
        int   snapHealth         = sp.health;
        int   snapMaxHealth      = sp.maxHealth;
        int   snapLevel          = sp.level;
        int   snapXp             = sp.experience;
        int   snapCurrency       = sp.inventory.currency;
        String snapEquippedWeapon = sp.inventory.equippedWeapon;
        String snapEquippedArmor  = sp.inventory.equippedArmor;
        java.util.Set<String> snapAbilities = new java.util.LinkedHashSet<>(sp.unlockedAbilities);
        java.util.Map<String, Integer> snapItems = new java.util.LinkedHashMap<>();
        for (com.indieniinja.sim.SimInventory.Slot slot : sp.inventory.slots) {
            if (slot == null || slot.itemId() == null) continue;
            snapItems.merge(slot.itemId(), slot.quantity(), Integer::sum);
        }

        // Derive hub-specific seed and reinitialise the simulation for the destination hub.
        long hubSeed = com.indieniinja.world.HubRegistry.hubSeed(soloSeed, hubDef.id());
        WorldGraph.WorldShape shape = WorldGraph.WorldShape.valueOf(hubDef.graphShape());
        initializeSoloSimulation(hubSeed, false, hubDef.roomCount(), shape, hubDef.id());

        // Restore player state to the freshly created SimPlayer.
        com.indieniinja.sim.SimPlayer newSp = localSim.getPlayer(0);
        if (newSp != null) {
            newSp.health    = Math.min(snapHealth, snapMaxHealth);
            newSp.maxHealth = snapMaxHealth;
            newSp.level     = snapLevel;
            newSp.experience = snapXp;
            newSp.inventory.currency = snapCurrency;
            newSp.unlockedAbilities.clear();
            newSp.unlockedAbilities.addAll(snapAbilities);
            for (java.util.Map.Entry<String, Integer> e : snapItems.entrySet()) {
                if (!newSp.inventory.addItem(e.getKey(), e.getValue())) {
                    log.warn("[GameScreen] portal transit: failed to restore item {} x{}",
                        e.getKey(), e.getValue());
                }
            }
            if (snapEquippedWeapon != null) newSp.inventory.equipItem(snapEquippedWeapon);
            if (snapEquippedArmor  != null) newSp.inventory.equipItem(snapEquippedArmor);
            newSp.weaponState = weaponStateFromEquippedItem(newSp.inventory.equippedWeapon);
        }

        // Restore prevLocalAbilities before the zone transition so the render loop
        // does not re-fire ability-unlock toasts for abilities the player already had.
        prevLocalAbilities.clear();
        prevLocalAbilities.addAll(snapAbilities);

        // resetForZoneTransition signals the render loop to clear per-zone state and
        // then call refreshSoloWorldRoomCache() + camera.snapTo() for solo mode.
        if (stateBuffer != null) stateBuffer.resetForZoneTransition();
        String fromHubId = originHubId;
        soloCurrentHubId = hubDef.id();
        String destinationSpawnRoomId = soloSpawnRoomId(hubDef.id());
        if (saveManager != null) saveManager.markDirty();
        if (hudRenderer != null) hudRenderer.notifyToast("ENTERING: " + hubDef.displayName().toUpperCase());
        log.info(
            "[GameScreen][Playtest][Portal] solo portal travel type={} origin_hub_id={} destination_hub_id={} destination_spawn_room_id={} seed={}",
            normalizedTransitionType, fromHubId, hubDef.id(), destinationSpawnRoomId, hubSeed
        );
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
                            boolean lP = c > 0         && grid[r][c - 1] == WorldGenerator.PLATFORM;
                            boolean rP = c < LEVEL_COLS - 1 && grid[r][c + 1] == WorldGenerator.PLATFORM;
                            mega[offY + r][offX + c] = blobTileSet.getPlatformFrame(room.biomeIndex, lP, rP);
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
        log.info("[Dialogue] event='{}' arg='{}' count={}",
            key, arg, dialogueEventCounts.getOrDefault(key, 1));

        switch (key) {
            case "start_mission" -> {
                if (!arg.isBlank()) {
                    startMissionFlow(arg, "dialogue_event");
                }
            }
            case "open_shop"     -> { /* stub — shop UI not yet implemented */ }
            case "advance_act"   -> storyManager.advanceAct();
            case "siren_start_first_trial" -> {
                storyManager.setFlag("siren_intro_seen", "true");
                storyManager.setFlag("siren_onboarding_complete", "true");
                startMissionFlow("demo_coin_run", "siren_dialogue");
            }
            case "siren_open_mission_board" -> {
                storyManager.setFlag("siren_intro_seen", "true");
                storyManager.setFlag("siren_onboarding_complete", "true");
                openMissionSelectOverlay("siren_dialogue");
            }
            // Known authored narrative events from data/dialogues.json.
            // Preserve them as story flags even when they do not map to an immediate gameplay action.
            case "tutorial_completed",
                 "siren_intro_seen",
                 "siren_onboarding_complete",
                 "town_lore_learned",
                 "act2_elder_conversation_complete",
                 "act2_elder_patience_shown",
                 "act3_final_blessing_received",
                 "act3_elder_final_conversation" -> {
                storyManager.setFlag(key, "true");
            }
            case "open_mission_menu" -> {
                storyManager.setFlag(key, "true");
                openMissionSelectOverlay("dialogue_event");
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

    private void logLocalPlaytestState(WorldSnapshot snap) {
        if (snap == null || snap.players == null || snap.players.isEmpty()) return;
        PlayerState local = findPlayerBySlotOrFirst(snap.players, localSlot);
        if (local == null) return;

        if (lastLoggedStanceMode == null || !lastLoggedStanceMode.equals(local.stanceMode)) {
            log.info("[Playtest][Stance] local slot={} stance={} yin={} yang={} flow={} hub={} room=({}, {}) pos=({}, {})",
                local.slot, local.stanceMode,
                String.format(java.util.Locale.ROOT, "%.3f", local.yinValue),
                String.format(java.util.Locale.ROOT, "%.3f", local.yangValue),
                local.flowMode, snap.hubId, snap.roomGridX, snap.roomGridY,
                (int) local.posX, (int) local.posY);
            lastLoggedStanceMode = local.stanceMode;
        }

        if (lastLoggedFlowMode == null || lastLoggedFlowMode != local.flowMode) {
            log.info("[Playtest][Flow] local slot={} active={} stance={} yin={} yang={} hub={} room=({}, {}) pos=({}, {})",
                local.slot, local.flowMode, local.stanceMode,
                String.format(java.util.Locale.ROOT, "%.3f", local.yinValue),
                String.format(java.util.Locale.ROOT, "%.3f", local.yangValue),
                snap.hubId, snap.roomGridX, snap.roomGridY,
                (int) local.posX, (int) local.posY);
            lastLoggedFlowMode = local.flowMode;
        }

        int lanternBand = localLanternBand(local.lanternValue);
        if (lastLoggedLanternBand == Integer.MIN_VALUE || lanternBand != lastLoggedLanternBand) {
            log.info("[Playtest][Lantern] local slot={} band={} value={} hub={} room=({}, {}) pos=({}, {})",
                local.slot,
                localLanternBandLabel(lanternBand),
                String.format(java.util.Locale.ROOT, "%.3f", local.lanternValue),
                snap.hubId, snap.roomGridX, snap.roomGridY,
                (int) local.posX, (int) local.posY);
            lastLoggedLanternBand = lanternBand;
        }
    }

    private static int localLanternBand(float value) {
        if (value < 0.20f) return 0;
        if (value < 0.45f) return 1;
        if (value < 0.70f) return 2;
        return 3;
    }

    private static String localLanternBandLabel(int band) {
        return switch (band) {
            case 0 -> "critical";
            case 1 -> "low";
            case 2 -> "mid";
            default -> "high";
        };
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
        com.indieniinja.network.PlayerState localP = findPlayerBySlot(snap.players, localSlot);
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
            inventoryTotalsScratch.clear();
            for (var slot : localP.inventory.slots) {
                if (slot == null) continue;
                String itemId = slot.itemId();
                if (itemId == null || itemId.isBlank()) continue;
                inventoryTotalsScratch.merge(
                    itemId.toLowerCase(java.util.Locale.ROOT),
                    slot.quantity(),
                    Integer::sum);
            }

            int currentCurrency = Math.max(0, localP.inventory.currency);
            if (prevInventoryBaselineReady) {
                int currencyGained = currentCurrency - prevInventoryCurrency;
                if (currencyGained > 0) {
                    missionManager.onItemCollected("coin", currencyGained);
                    log.debug("[Mission] currency gain coin +{}", currencyGained);
                }

                for (var e : inventoryTotalsScratch.entrySet()) {
                    int prevQty = prevInventoryTotals.getOrDefault(e.getKey(), 0);
                    int gained = e.getValue() - prevQty;
                    if (gained > 0) {
                        missionManager.onItemCollected(e.getKey(), gained);
                        log.debug("[Mission] item gain {} +{}", e.getKey(), gained);
                    }
                }
            } else {
                prevInventoryBaselineReady = true;
            }

            prevInventoryTotals.clear();
            prevInventoryTotals.putAll(inventoryTotalsScratch);
            prevInventoryCurrency = currentCurrency;
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

        // World seed
        if (soloSeed != 0) live.worldSeed = soloSeed;
        else if (prevSnap != null && prevSnap.seed != 0) live.worldSeed = prevSnap.seed;

        // Fog-of-war: rooms visited this session
        live.visitedRoomKeys = new java.util.ArrayList<>(visitedRooms);

        // Player state from solo sim
        if (localSim != null) {
            com.indieniinja.sim.SimPlayer sp = localSim.getPlayer(0);
            if (sp != null) {
                live.currentHubId     = localSim.hubId;
                live.currentHubX      = sp.physics.x;
                live.currentHubY      = sp.physics.y;
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
        } else if (prevSnap != null) {
            PlayerState local = findPlayerBySlot(prevSnap.players, localSlot);
            if (local != null) {
                live.currentHubId = prevSnap.hubId;
                live.currentHubX  = local.posX;
                live.currentHubY  = local.posY;
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
    @Override public void resume() {
        paused = false;
        Gdx.input.setInputProcessor(null);
        syncDevConsoleInputFocus();
    }
    @Override public void hide() {
        if (saveManager != null) { syncSaveState(); saveManager.save(); }
        if (Gdx.input.getInputProcessor() == devConsoleInputAdapter) {
            Gdx.input.setInputProcessor(null);
        }
        flushSoloReplay();
    }

    @Override
    public void dispose() {
        if (saveManager    != null) { syncSaveState(); saveManager.save(); }
        flushSoloReplay();
        if (audioManager   != null) audioManager.dispose();
        if (musicManager   != null) musicManager.dispose();
        if (networkClient  != null) networkClient.shutdown();
        if (batch          != null) batch.dispose();
        if (anims          != null) anims.dispose();
        if (blobTileSet    != null) blobTileSet.dispose();
        if (chunkRenderer    != null) chunkRenderer.dispose();
        if (parallaxRenderer != null) parallaxRenderer.dispose();
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
        devConsole.dispose();
    }

    /**
     * Give keyboard text focus to the dev console only while it is visible.
     * Other game controls remain poll-based and should not install an input processor.
     */
    private void syncDevConsoleInputFocus() {
        if (paused) return;
        InputProcessor current = Gdx.input.getInputProcessor();
        if (devConsole.isVisible()) {
            if (current != devConsoleInputAdapter) {
                Gdx.input.setInputProcessor(devConsoleInputAdapter);
            }
        } else if (current == devConsoleInputAdapter) {
            Gdx.input.setInputProcessor(null);
        }
    }

    private void latchRealtimeInput(InputCommand sampled) {
        if (sampled == null) return;
        latchedRealtimeInput.frame = sampled.frame;

        // Held state mirrors latest sampled keyboard state.
        latchedRealtimeInput.up = sampled.up;
        latchedRealtimeInput.down = sampled.down;
        latchedRealtimeInput.left = sampled.left;
        latchedRealtimeInput.right = sampled.right;
        latchedRealtimeInput.jump = sampled.jump;
        latchedRealtimeInput.dash = sampled.dash;
        latchedRealtimeInput.crouch = sampled.crouch;
        latchedRealtimeInput.attack = sampled.attack;
        latchedRealtimeInput.throwShuriken = sampled.throwShuriken;
        latchedRealtimeInput.teleport = sampled.teleport;
        latchedRealtimeInput.ninjutsu = sampled.ninjutsu;
        latchedRealtimeInput.block = sampled.block;
        latchedRealtimeInput.fullmap = sampled.fullmap;
        latchedRealtimeInput.slowWalk = sampled.slowWalk;

        // One-shot actions are OR-latched until the next sim tick consumes them.
        latchedRealtimeInput.toggleProc |= sampled.toggleProc;
        latchedRealtimeInput.cycleCamera |= sampled.cycleCamera;
        latchedRealtimeInput.interact |= sampled.interact;
        latchedRealtimeInput.inventory |= sampled.inventory;
        latchedRealtimeInput.consumable |= sampled.consumable;
        latchedRealtimeInput.minimap |= sampled.minimap;
        latchedRealtimeInput.controlsOverlay |= sampled.controlsOverlay;
        latchedRealtimeInput.debugOverlay |= sampled.debugOverlay;
        latchedRealtimeInput.menuConfirm |= sampled.menuConfirm;
        latchedRealtimeInput.menuBack |= sampled.menuBack;
        latchedRealtimeInput.stanceSwitch |= sampled.stanceSwitch;
        latchedRealtimeInput.selectWeapon1 |= sampled.selectWeapon1;
        latchedRealtimeInput.selectWeapon2 |= sampled.selectWeapon2;
    }

    private InputCommand consumeLatchedRealtimeInput() {
        InputCommand out = copyInputCommand(latchedRealtimeInput);
        clearLatchedOneShotFlags();
        return out;
    }

    private void clearLatchedOneShotFlags() {
        latchedRealtimeInput.toggleProc = false;
        latchedRealtimeInput.cycleCamera = false;
        latchedRealtimeInput.interact = false;
        latchedRealtimeInput.inventory = false;
        latchedRealtimeInput.consumable = false;
        latchedRealtimeInput.minimap = false;
        latchedRealtimeInput.controlsOverlay = false;
        latchedRealtimeInput.debugOverlay = false;
        latchedRealtimeInput.menuConfirm = false;
        latchedRealtimeInput.menuBack = false;
        latchedRealtimeInput.stanceSwitch = false;
        latchedRealtimeInput.selectWeapon1 = false;
        latchedRealtimeInput.selectWeapon2 = false;
    }

    private void clearLatchedRealtimeInput() {
        latchedRealtimeInput.frame = 0;
        latchedRealtimeInput.up = false;
        latchedRealtimeInput.down = false;
        latchedRealtimeInput.left = false;
        latchedRealtimeInput.right = false;
        latchedRealtimeInput.jump = false;
        latchedRealtimeInput.dash = false;
        latchedRealtimeInput.crouch = false;
        latchedRealtimeInput.toggleProc = false;
        latchedRealtimeInput.cycleCamera = false;
        latchedRealtimeInput.attack = false;
        latchedRealtimeInput.throwShuriken = false;
        latchedRealtimeInput.teleport = false;
        latchedRealtimeInput.ninjutsu = false;
        latchedRealtimeInput.block = false;
        latchedRealtimeInput.interact = false;
        latchedRealtimeInput.inventory = false;
        latchedRealtimeInput.consumable = false;
        latchedRealtimeInput.minimap = false;
        latchedRealtimeInput.fullmap = false;
        latchedRealtimeInput.controlsOverlay = false;
        latchedRealtimeInput.debugOverlay = false;
        latchedRealtimeInput.slowWalk = false;
        latchedRealtimeInput.menuConfirm = false;
        latchedRealtimeInput.menuBack = false;
        latchedRealtimeInput.stanceSwitch = false;
        latchedRealtimeInput.selectWeapon1 = false;
        latchedRealtimeInput.selectWeapon2 = false;
    }

    private InputCommand inputForReplayTick(long frame) {
        java.util.Map<Integer, InputCommand> replayInputs = soloReplay.inputsForTick(frame);
        InputCommand cmd = replayInputs.get(0);
        return cmd != null ? cmd : new InputCommand();
    }

    private static PlayerState findPlayerBySlot(java.util.List<PlayerState> players, int slot) {
        if (players == null || players.isEmpty()) return null;
        for (PlayerState p : players) {
            if (p.slot == slot) return p;
        }
        return null;
    }

    private static PlayerState findPlayerBySlotOrFirst(java.util.List<PlayerState> players, int slot) {
        PlayerState found = findPlayerBySlot(players, slot);
        if (found != null) return found;
        return (players == null || players.isEmpty()) ? null : players.get(0);
    }

    private static InputCommand copyInputCommand(InputCommand src) {
        InputCommand dst = new InputCommand(src.frame);
        dst.up = src.up;
        dst.down = src.down;
        dst.left = src.left;
        dst.right = src.right;
        dst.jump = src.jump;
        dst.dash = src.dash;
        dst.crouch = src.crouch;
        dst.toggleProc = src.toggleProc;
        dst.cycleCamera = src.cycleCamera;
        dst.attack = src.attack;
        dst.throwShuriken = src.throwShuriken;
        dst.teleport = src.teleport;
        dst.ninjutsu = src.ninjutsu;
        dst.block = src.block;
        dst.interact = src.interact;
        dst.inventory = src.inventory;
        dst.consumable = src.consumable;
        dst.minimap = src.minimap;
        dst.fullmap = src.fullmap;
        dst.controlsOverlay = src.controlsOverlay;
        dst.debugOverlay = src.debugOverlay;
        dst.slowWalk = src.slowWalk;
        dst.menuConfirm = src.menuConfirm;
        dst.menuBack = src.menuBack;
        dst.stanceSwitch = src.stanceSwitch;
        dst.selectWeapon1 = src.selectWeapon1;
        dst.selectWeapon2 = src.selectWeapon2;
        return dst;
    }

    // ── S3 — Parallax helpers ─────────────────────────────────────────────────

    // Maps biome index (0-11) to the parallax set name in parallax.json.
    private static final String[] BIOME_PARALLAX = {
        "earth", "forest", "snow", "ruins", "dungeon",  // 0-4 primary
        "earth", "forest", "snow", "ruins",              // 5-8 alt variants
        "spirit", "hub", "hub"                           // 9-11
    };

    private static String parallaxSetFor(int biomeIndex) {
        int b = Math.max(0, Math.min(BIOME_PARALLAX.length - 1, biomeIndex));
        return BIOME_PARALLAX[b];
    }

    // Maps biome index (0-11) to deco rule set name in deco_rules.json.
    private static final String[] BIOME_DECO = {
        "earth", "forest", "snow", "ruins", "dungeon",  // 0-4 primary
        "earth", "forest", "snow", "ruins",              // 5-8 alt variants
        "spirit", "hub", "hub"                           // 9-11
    };

    private static String decoSetFor(int biomeIndex) {
        int b = Math.max(0, Math.min(BIOME_DECO.length - 1, biomeIndex));
        return BIOME_DECO[b];
    }

    private static DecorationGenerator.DecoRuleSet loadDecoRuleSet(String setName) {
        com.badlogic.gdx.files.FileHandle fh =
            com.badlogic.gdx.Gdx.files.internal("assets/visual/deco_rules.json");
        if (!fh.exists()) return DecorationGenerator.DecoRuleSet.defaultRules();
        try {
            com.badlogic.gdx.utils.JsonValue sets =
                new com.badlogic.gdx.utils.JsonReader().parse(fh).get("sets");
            com.badlogic.gdx.utils.JsonValue node = sets != null ? sets.get(setName) : null;
            return node != null
                ? DecorationGenerator.DecoRuleSet.fromJson(node)
                : DecorationGenerator.DecoRuleSet.defaultRules();
        } catch (Exception e) {
            return DecorationGenerator.DecoRuleSet.defaultRules();
        }
    }

    // ── S0 — Visual dev commands ──────────────────────────────────────────────

    private void registerVisualDevCommands() {
        if (!DevConsole.ENABLED) return;

        devConsole.register("reload_visual",
            "Reload visual config JSONs (biomes, parallax, deco_rules)",
            (args, log) -> {
                com.badlogic.gdx.utils.JsonReader reader = new com.badlogic.gdx.utils.JsonReader();
                int biomeCount = 0, parallaxCount = 0, decoCount = 0;
                try {
                    com.badlogic.gdx.files.FileHandle biomeFh =
                        com.badlogic.gdx.Gdx.files.local("assets/visual/biomes.json");
                    if (biomeFh.exists()) biomeCount = reader.parse(biomeFh).get("biomes").size;
                    com.badlogic.gdx.files.FileHandle parallaxFh =
                        com.badlogic.gdx.Gdx.files.local("assets/visual/parallax.json");
                    if (parallaxFh.exists()) parallaxCount = reader.parse(parallaxFh).get("sets").size;
                    com.badlogic.gdx.files.FileHandle decoFh =
                        com.badlogic.gdx.Gdx.files.local("assets/visual/deco_rules.json");
                    if (decoFh.exists()) decoCount = reader.parse(decoFh).get("sets").size;
                    log.accept("[INFO] reload_visual: " + biomeCount + " biomes, "
                        + parallaxCount + " parallax sets, " + decoCount + " deco rule sets");
                } catch (Exception e) {
                    log.accept("[ERR] reload_visual: " + e.getMessage());
                }
            });

        devConsole.register("set_biome",
            "Force room biome: set_biome <earth|grass|snow|sand|stone|spirit|hub|0-11>",
            (args, log) -> {
                if (args.length < 1) { log.accept("[ERR] Usage: set_biome <name|index>"); return; }
                if (blobTileSet == null)    { log.accept("[ERR] blobTileSet not loaded"); return; }
                if (currentTileGrid == null) { log.accept("[ERR] no room grid loaded yet"); return; }
                int idx;
                try {
                    idx = switch (args[0].toLowerCase()) {
                        case "earth"            -> BlobTileSet.BIOME_EARTH;
                        case "grass", "forest"  -> BlobTileSet.BIOME_GRASS;
                        case "snow", "ice"      -> BlobTileSet.BIOME_SNOW;
                        case "sand", "ruins"    -> BlobTileSet.BIOME_SAND;
                        case "stone", "dungeon" -> BlobTileSet.BIOME_STONE;
                        case "spirit"           -> 6;
                        case "hub"              -> 8;
                        default                 -> Integer.parseInt(args[0]);
                    };
                } catch (NumberFormatException e) {
                    log.accept("[ERR] unknown biome: " + args[0]); return;
                }
                currentBiomeIndex = idx;
                chunkRenderer.loadBlobTiles(blobTileSet, currentBiomeIndex,
                    currentTileGrid, LEVEL_COLS, LEVEL_ROWS);
                parallaxRenderer.loadBiome(parallaxSetFor(currentBiomeIndex),
                    com.badlogic.gdx.Gdx.files.internal("assets"));
                DecorationGenerator.DecoRuleSet rules = loadDecoRuleSet(decoSetFor(currentBiomeIndex));
                byte[][] decoGrid = DecorationGenerator.generate(
                    currentTileGrid, loadedSeed, currentBiomeIndex, rules, LEVEL_COLS, LEVEL_ROWS);
                chunkRenderer.loadDecoMap(decoGrid, blobTileSet, currentBiomeIndex);
                log.accept("[INFO] set_biome=" + args[0] + " (index=" + idx + ") — terrain+parallax+deco rebuilt");
            });

        devConsole.register("regen_room",
            "Rebuild room visual layer from current biome: regen_room",
            (args, log) -> {
                if (currentTileGrid == null) { log.accept("[ERR] no room grid loaded yet"); return; }
                if (blobTileSet == null)     { log.accept("[ERR] blobTileSet not loaded"); return; }
                chunkRenderer.loadBlobTiles(blobTileSet, currentBiomeIndex,
                    currentTileGrid, LEVEL_COLS, LEVEL_ROWS);
                DecorationGenerator.DecoRuleSet rules = loadDecoRuleSet(decoSetFor(currentBiomeIndex));
                byte[][] decoGrid = DecorationGenerator.generate(
                    currentTileGrid, loadedSeed, currentBiomeIndex, rules, LEVEL_COLS, LEVEL_ROWS);
                chunkRenderer.loadDecoMap(decoGrid, blobTileSet, currentBiomeIndex);
                log.accept("[INFO] regen_room: terrain+deco rebuilt (biome=" + currentBiomeIndex + ")");
            });
    }

    private static ContentRegistry loadClientContentRegistry() {
        java.nio.file.Path dataRoot = java.nio.file.Paths.get("data");
        if (!java.nio.file.Files.isDirectory(dataRoot)) return new ContentRegistry();
        try {
            return new ContentLoader(dataRoot).loadAll();
        } catch (ContentLoadException e) {
            com.badlogic.gdx.Gdx.app.error("GameScreen", "Content load failed (using empty registry): " + e.getMessage());
            return new ContentRegistry();
        }
    }
}
