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

    // ── Core subsystems ───────────────────────────────────────────────────────
    private SpriteBatch         batch;
    /** Reusable matrix for translating entity draws by the current room world-space offset. */
    private final com.badlogic.gdx.math.Matrix4 entityTransform = new com.badlogic.gdx.math.Matrix4();
    private GameCamera          camera;
    private GameStateBuffer     stateBuffer;
    private InputPoller         inputPoller;
    private NetworkClientThread networkClient;

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
    private MinimapRenderer  minimapRenderer;
    /** Latest shop states from full snapshot — keyed by npc_id. */
    private final java.util.Map<String, ShopState> latestShopStates = new java.util.LinkedHashMap<>();
    /** Cached world room list from the most recent full snapshot (empty on delta frames). */
    private java.util.List<WorldRoomDescriptor> cachedWorldRooms = java.util.List.of();
    /** Cached portal list from the most recent full snapshot. */
    private java.util.List<com.indieniinja.network.PortalState> cachedPortals = java.util.List.of();

    // ── Audio ─────────────────────────────────────────────────────────────────
    private AudioManager audioManager;
    /** Previous animState per player slot — for state-transition SFX detection. */
    private final java.util.Map<Integer,String>  prevAnimState = new java.util.HashMap<>();
    /** Previous health per player slot — for hurt/death SFX detection. */
    private final java.util.Map<Integer,Integer> prevHealth    = new java.util.HashMap<>();

    /** Most recently received snapshot — retained between frames for overlay input. */
    private WorldSnapshot prevSnap = null;

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

    // ── Megamap state ─────────────────────────────────────────────────────────
    /** Number of rooms in the built megamap (0 = not built yet). */
    private int   megamapRoomCount = 0;
    /** Grid coordinate of the top-left room in the megamap. */
    private int   megamapMinGridX  = 0;
    private int   megamapMinGridY  = 0;
    /** Full megamap size in tiles (for camera clamping). */
    private int   megamapW         = LEVEL_COLS;
    private int   megamapH         = LEVEL_ROWS;
    /**
     * World-space pixel offset of the current room's origin within the megamap.
     * Entity positions are room-local; adding this offset converts to world-space
     * for the camera projection.  0,0 when megamap is not yet built.
     */
    private float roomWorldOffX    = 0f;
    private float roomWorldOffY    = 0f;

    public GameScreen(NinjaGameClient game, String host, int port) {
        this(game, host, port, "arcade");
    }

    public GameScreen(NinjaGameClient game, String host, int port, String gameMode) {
        this.game     = game;
        this.host     = host;
        this.port     = port;
        this.gameMode = gameMode;
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

        networkClient = new NetworkClientThread(host, port, stateBuffer);
        networkClient.setGameMode(gameMode);
        networkClient.start();

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
        minimapRenderer  = new MinimapRenderer();
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

        // ── Overlay input priority: shop > inventory > dialogue > game ────────
        // Use prevSnap (last frame's snapshot) since this frame's snap hasn't been polled yet.
        boolean shopConsumed = false;
        if (prevSnap != null) {
            PlayerState localSnap = prevSnap.players.stream()
                .filter(p -> p.slot == localSlot).findFirst().orElse(null);
            shopConsumed = shopOverlay.handleInput(localSnap);
        }
        boolean invConsumed = !shopConsumed && inventoryOverlay.handleInput();

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
        boolean anyOverlay = shopConsumed || invConsumed || dialogueConsumed;
        if (!anyOverlay && Gdx.input.isKeyJustPressed(Input.Keys.ESCAPE)) {
            if (paused) resume(); else pause();
        }

        if (!paused && !dialogueConsumed) {
            accumulator += delta;
            while (accumulator >= PHYSICS_DT) {
                InputCommand cmd = inputPoller.poll();
                networkClient.sendInput(cmd);
                accumulator -= PHYSICS_DT;
            }
        }

        // ── Zone transition: reset world state so next full snapshot re-inits tiles ──
        if (stateBuffer.pollZoneTransition()) {
            megamapRoomCount  = 0;
            megamapMinGridX   = 0;
            megamapMinGridY   = 0;
            megamapW          = LEVEL_COLS;
            megamapH          = LEVEL_ROWS;
            loadedSeed        = Long.MIN_VALUE;
            loadedNeighborDirs = java.util.List.of();
            cachedWorldRooms  = java.util.List.of();
            cachedPortals     = java.util.List.of();
            latestShopStates.clear();
            prevSnap          = null;
            chunkRenderer.loadPlaceholderLayout(LEVEL_COLS, LEVEL_ROWS);
        }

        WorldSnapshot snap = stateBuffer.poll();

        // ── Mission timer + auto-save ─────────────────────────────────────────
        missionManager.tick(delta);
        saveManager.tick(delta);

        // ── Audio: state-transition SFX ──────────────────────────────────────
        if (snap != null) tickAudio(snap);

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
                            // Open shop overlay
                            inventoryOverlay.hide();
                            shopOverlay.open(latestShopStates.get(npc.npcId));
                        } else {
                            // Open dialogue
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
            if (!snap.worldRooms.isEmpty() && snap.worldRooms.size() != megamapRoomCount) {
                buildMegamap(snap.worldRooms);
                // Snap camera to player's world-space position immediately —
                // without this the spring-lerp slowly pans from single-room coords
                // (e.g. x=2048) to the actual megamap position (e.g. x=10240).
                if (!snap.players.isEmpty()) {
                    PlayerState snapLocal = snap.players.stream()
                        .filter(p -> p.slot == localSlot).findFirst()
                        .orElse(snap.players.get(0));
                    int tile = PhysicsConstants.TILE_SIZE;
                    camera.snapTo(
                        (snap.roomGridX - megamapMinGridX) * LEVEL_COLS * tile + snapLocal.posX,
                        (snap.roomGridY - megamapMinGridY) * LEVEL_ROWS * tile + snapLocal.posY
                    );
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

            // ── Room world-space offset (entity rendering needs this) ─────────
            if (megamapRoomCount > 0) {
                int tile = PhysicsConstants.TILE_SIZE;
                roomWorldOffX = (snap.roomGridX - megamapMinGridX) * LEVEL_COLS * tile;
                roomWorldOffY = (snap.roomGridY - megamapMinGridY) * LEVEL_ROWS * tile;
            } else {
                roomWorldOffX = 0f;
                roomWorldOffY = 0f;
            }

            // ── Camera follow ─────────────────────────────────────────────────
            if (!snap.players.isEmpty()) {
                PlayerState local = snap.players.stream()
                    .filter(p -> p.slot == localSlot)
                    .findFirst()
                    .orElse(snap.players.get(0));
                camera.follow(roomWorldOffX + local.posX, roomWorldOffY + local.posY);
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

        // Pass 2 — entities: room-local coords → translate by current room world offset.
        // Without this, entities render at room-local (0–4096) while the camera is at
        // world-space (e.g. 4096 + 2048), putting them thousands of pixels off-screen.
        entityTransform.setToTranslation(roomWorldOffX, roomWorldOffY, 0);
        batch.setTransformMatrix(entityTransform);
        batch.begin();
            entityRenderer.render(batch, snap, delta);
            particleSystem.render(batch);
        batch.end();
        batch.setTransformMatrix(entityTransform.idt());  // push identity into batch so overlays/text render at screen coords

        entityRenderer.pruneEntities(snap);

        hudRenderer.render(snap, stateBuffer.isConnected(),
            Gdx.graphics.getFramesPerSecond(), localSlot);

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
            float lpx     = localForMap != null ? localForMap.posX : 0f;
            float lpy     = localForMap != null ? localForMap.posY : 0f;
            int   gridX   = snapForMap != null ? snapForMap.roomGridX : 0;
            int   gridY   = snapForMap != null ? snapForMap.roomGridY : 0;
            float roomPx  = PhysicsConstants.ROOM_WIDTH_TILES  * PhysicsConstants.TILE_SIZE;
            float roomPy  = PhysicsConstants.ROOM_HEIGHT_TILES * PhysicsConstants.TILE_SIZE;
            batch.setProjectionMatrix(hudRenderer.screenProjection());
            // MinimapRenderer manages its own batch.begin/end; do NOT open batch here.
            minimapRenderer.render(batch, cachedWorldRooms, gridX, gridY, lpx, lpy, roomPx, roomPy);
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

        com.badlogic.gdx.graphics.g2d.TextureRegion solidTex    = chunkRenderer.placeholderSolid();
        com.badlogic.gdx.graphics.g2d.TextureRegion platformTex = chunkRenderer.placeholderPlatform();

        for (WorldRoomDescriptor room : rooms) {
            byte[][] grid = WorldGenerator.generate(
                room.seed, LEVEL_COLS, LEVEL_ROWS, room.neighborDirs, room.roomType);

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
                        }
                    }
                }
            } else {
                for (int r = 0; r < LEVEL_ROWS; r++) {
                    for (int c = 0; c < LEVEL_COLS; c++) {
                        byte tile = grid[r][c];
                        if      (tile == WorldGenerator.SOLID)    mega[offY + r][offX + c] = solidTex;
                        else if (tile == WorldGenerator.PLATFORM) mega[offY + r][offX + c] = platformTex;
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
        if (minimapRenderer  != null) minimapRenderer.dispose();
    }
}
