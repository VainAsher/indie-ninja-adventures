package com.indieniinja.client;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.Input;
import com.badlogic.gdx.Screen;
import com.badlogic.gdx.files.FileHandle;
import com.badlogic.gdx.graphics.GL20;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.g2d.TextureAtlas;
import com.indieniinja.client.network.NetworkClientThread;
import com.indieniinja.client.rendering.AnimationRegistry;
import com.indieniinja.client.rendering.BlobTileSet;
import com.indieniinja.client.rendering.ChunkRenderer;
import com.indieniinja.client.rendering.EntityRenderer;
import com.indieniinja.client.rendering.HudRenderer;
import com.indieniinja.client.rendering.ParticleSystem;
import com.indieniinja.client.ui.PauseScreen;
import com.indieniinja.network.InputCommand;
import com.indieniinja.network.PlayerState;
import com.indieniinja.network.WorldSnapshot;
import com.indieniinja.physics.PhysicsConstants;
import com.indieniinja.world.WorldGenerator;

/**
 * In-game screen — contains the full render + simulation loop.
 *
 * Extracted from NinjaGameClient (which now extends Game and manages screens).
 * ESC toggles a PauseScreen overlay; the network thread keeps running while
 * paused so the server stays in sync.
 */
public final class GameScreen implements Screen {

    private static final float PHYSICS_DT     = PhysicsConstants.FIXED_DT;
    private static final float MAX_FRAME_TIME = PhysicsConstants.MAX_FRAME_TIME;
    private static final int   LEVEL_COLS     = PhysicsConstants.ROOM_WIDTH_TILES;   // 128
    private static final int   LEVEL_ROWS     = PhysicsConstants.ROOM_HEIGHT_TILES;  // 128

    private final NinjaGameClient game;
    private final String          host;
    private final int             port;

    // ── Core subsystems ───────────────────────────────────────────────────────
    private SpriteBatch         batch;
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

    // ── Fixed-timestep state ──────────────────────────────────────────────────
    private float accumulator     = 0f;
    private int   localSlot       = 0;
    private long  loadedSeed      = Long.MIN_VALUE;   // tracks which seed we've generated tiles for
    private java.util.List<String> loadedNeighborDirs = java.util.List.of();

    public GameScreen(NinjaGameClient game, String host, int port) {
        this.game = game;
        this.host = host;
        this.port = port;
    }

    // ── Screen lifecycle ──────────────────────────────────────────────────────

    @Override
    public void show() {
        batch       = new SpriteBatch();
        camera      = new GameCamera(Gdx.graphics.getWidth(), Gdx.graphics.getHeight());
        // Snap to spawn area. Floor top = row (LEVEL_ROWS-4) = row 124 → y=3968.
        // Camera Y just above the floor so the player is visible before the first snapshot.
        camera.snapTo(
            LEVEL_COLS * PhysicsConstants.TILE_SIZE / 2f,   // centre horizontally
            (LEVEL_ROWS - 6) * PhysicsConstants.TILE_SIZE   // just above the floor (Y-DOWN)
        );
        stateBuffer = new GameStateBuffer();
        inputPoller = new InputPoller();

        anims = new AnimationRegistry();
        FileHandle atlasFile   = Gdx.files.internal("assets/characters.atlas");
        FileHandle playerDir   = Gdx.files.internal("assets/sprites/player");
        if (atlasFile.exists()) {
            anims.loadAtlas(new TextureAtlas(atlasFile));
        } else if (playerDir.exists()) {
            anims.loadSpriteSheets(playerDir);
        } else {
            anims.loadPlaceholder();
        }

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
        networkClient.start();

        Gdx.input.setInputProcessor(null);  // InputPoller polls directly; ESC handled in render
    }

    @Override
    public void render(float delta) {
        delta = Math.min(delta, MAX_FRAME_TIME);

        // ── ESC toggles pause ─────────────────────────────────────────────────
        if (Gdx.input.isKeyJustPressed(Input.Keys.ESCAPE)) {
            if (paused) resume(); else pause();
        }

        if (!paused) {
            accumulator += delta;
            while (accumulator >= PHYSICS_DT) {
                InputCommand cmd = inputPoller.poll();
                networkClient.sendInput(cmd);
                accumulator -= PHYSICS_DT;
            }
        }

        WorldSnapshot snap = stateBuffer.poll();

        if (snap != null) {
            // Generate and load procedural tile layout on first snapshot (or seed/room change)
            boolean seedChanged = snap.seed != 0 && snap.seed != loadedSeed;
            boolean dirsChanged = !snap.neighborDirs.equals(loadedNeighborDirs);
            if (seedChanged || dirsChanged) {
                loadedSeed         = snap.seed;
                loadedNeighborDirs = snap.neighborDirs;
                byte[][] grid2d = WorldGenerator.generate(
                    snap.seed, LEVEL_COLS, LEVEL_ROWS, snap.neighborDirs);
                if (blobTileSet != null) {
                    // Full autotiled rendering using the mk_nature spritesheet
                    int biomeIdx = BlobTileSet.biomeFromSeed(snap.seed);
                    chunkRenderer.loadBlobTiles(blobTileSet, biomeIdx, grid2d, LEVEL_COLS, LEVEL_ROWS);
                } else {
                    // Fallback: placeholder coloured tiles (grid2d already has door openings)
                    byte[] flat = new byte[LEVEL_ROWS * LEVEL_COLS];
                    for (int r = 0; r < LEVEL_ROWS; r++)
                        System.arraycopy(grid2d[r], 0, flat, r * LEVEL_COLS, LEVEL_COLS);
                    chunkRenderer.loadProceduralTiles(flat, LEVEL_COLS, LEVEL_ROWS);
                }
            }

            if (!snap.players.isEmpty()) {
                PlayerState local = snap.players.stream()
                    .filter(p -> p.slot == localSlot)
                    .findFirst()
                    .orElse(snap.players.get(0));
                camera.follow(local.posX, local.posY);
                camera.clampToBounds(
                    LEVEL_COLS * PhysicsConstants.TILE_SIZE,
                    LEVEL_ROWS * PhysicsConstants.TILE_SIZE
                );
            }
        }

        // ── Render world ──────────────────────────────────────────────────────
        Gdx.gl.glClearColor(0.08f, 0.08f, 0.12f, 1f);
        Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT);

        particleSystem.update(delta);

        batch.setProjectionMatrix(camera.cam.combined);
        batch.begin();
            chunkRenderer.render(batch, camera);
            entityRenderer.render(batch, snap, delta);
            particleSystem.render(batch);
        batch.end();

        entityRenderer.pruneEntities(snap);

        hudRenderer.render(snap, stateBuffer.isConnected(),
            Gdx.graphics.getFramesPerSecond(), localSlot);

        // ── Pause overlay (rendered on top) ───────────────────────────────────
        if (paused) {
            pauseScreen.render(delta);
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
        if (networkClient  != null) networkClient.shutdown();
        if (batch          != null) batch.dispose();
        if (anims          != null) anims.dispose();
        if (blobTileSet    != null) blobTileSet.dispose();
        if (chunkRenderer  != null) chunkRenderer.dispose();
        if (particleSystem != null) particleSystem.dispose();
        if (hudRenderer    != null) hudRenderer.dispose();
        if (pauseScreen    != null) pauseScreen.dispose();
    }
}
