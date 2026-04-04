package com.indieniinja.client;

import com.badlogic.gdx.ApplicationAdapter;
import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.files.FileHandle;
import com.badlogic.gdx.graphics.GL20;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.g2d.TextureAtlas;
import com.indieniinja.client.network.NetworkClientThread;
import com.indieniinja.client.rendering.AnimationRegistry;
import com.indieniinja.client.rendering.ChunkRenderer;
import com.indieniinja.client.rendering.EntityRenderer;
import com.indieniinja.client.rendering.HudRenderer;
import com.indieniinja.network.InputCommand;
import com.indieniinja.network.PlayerState;
import com.indieniinja.network.WorldSnapshot;
import com.indieniinja.physics.PhysicsConstants;

/**
 * Top-level libGDX ApplicationAdapter for the Java game client.
 * Direct equivalent of the Pygame game loop in demo_game.py.
 *
 * Fixed-timestep pattern (Glenn Fiedler) — matches Python's core/clock.py:
 *   accumulator += min(delta, MAX_FRAME_TIME)
 *   while accumulator >= PHYSICS_DT: tick(); accumulator -= PHYSICS_DT
 *   alpha = accumulator / PHYSICS_DT  (unused on client — server-authoritative)
 *
 * Thread model:
 *   - libGDX render thread: input polling, rendering, camera, HUD
 *   - NetworkClientThread: TCP recv/send with Java server
 *
 * Asset strategy:
 *   - Looks for assets/characters.atlas in the working directory.
 *   - Falls back to coloured placeholder sprites if absent.
 */
public final class NinjaGameClient extends ApplicationAdapter {

    // Fixed timestep — must match server PHYSICS_DT
    private static final float PHYSICS_DT     = PhysicsConstants.PHYSICS_DT;  // 1/60 s
    private static final float MAX_FRAME_TIME = 0.25f;  // cap spiral of death

    // Level world size in tiles (matches LevelLayout.buildTestLayout)
    private static final int LEVEL_COLS = 50;
    private static final int LEVEL_ROWS = 28;

    private final String host;
    private final int    port;

    // ── Core subsystems ───────────────────────────────────────────────────────
    private SpriteBatch        batch;
    private GameCamera         camera;
    private GameStateBuffer    stateBuffer;
    private InputPoller        inputPoller;
    private NetworkClientThread networkClient;

    // ── Rendering subsystems ──────────────────────────────────────────────────
    private AnimationRegistry  anims;
    private ChunkRenderer      chunkRenderer;
    private EntityRenderer     entityRenderer;
    private HudRenderer        hudRenderer;

    // ── Fixed-timestep state ──────────────────────────────────────────────────
    private float accumulator = 0f;
    private float stateTime   = 0f;  // global animation clock

    // ── Player tracking ───────────────────────────────────────────────────────
    /** Slot assigned by the server (updated from first player entry matching our UUID). */
    private int localSlot = 0;

    public NinjaGameClient(String host, int port) {
        this.host = host;
        this.port = port;
    }

    // ── Lifecycle ─────────────────────────────────────────────────────────────

    @Override
    public void create() {
        batch       = new SpriteBatch();
        camera      = new GameCamera(Gdx.graphics.getWidth(), Gdx.graphics.getHeight());
        stateBuffer = new GameStateBuffer();
        inputPoller = new InputPoller();

        // ── Animations ────────────────────────────────────────────────────────
        anims = new AnimationRegistry();
        FileHandle atlasFile = Gdx.files.internal("assets/characters.atlas");
        if (atlasFile.exists()) {
            anims.loadAtlas(new TextureAtlas(atlasFile));
        } else {
            anims.loadPlaceholder();
        }

        // ── Tile world ────────────────────────────────────────────────────────
        chunkRenderer = new ChunkRenderer();
        FileHandle tileAtlasFile = Gdx.files.internal("assets/tiles.atlas");
        if (tileAtlasFile.exists()) {
            // Full tile atlas — ChunkRenderer would load layout from server seed
            chunkRenderer.loadPlaceholderLayout(LEVEL_COLS, LEVEL_ROWS);
        } else {
            chunkRenderer.loadPlaceholderLayout(LEVEL_COLS, LEVEL_ROWS);
        }

        // ── Entity + HUD renderers ────────────────────────────────────────────
        entityRenderer = new EntityRenderer(anims);
        hudRenderer    = new HudRenderer();

        // ── Network ───────────────────────────────────────────────────────────
        networkClient = new NetworkClientThread(host, port, stateBuffer);
        networkClient.start();
    }

    @Override
    public void render() {
        float delta = Math.min(Gdx.graphics.getDeltaTime(), MAX_FRAME_TIME);
        accumulator += delta;
        stateTime   += delta;

        // ── Fixed-step ticks (animation + client-side prediction hooks) ───────
        while (accumulator >= PHYSICS_DT) {
            // Poll input and send to server this tick
            InputCommand cmd = inputPoller.poll();
            networkClient.sendInput(cmd);
            accumulator -= PHYSICS_DT;
        }

        // ── Get latest server state ───────────────────────────────────────────
        WorldSnapshot snap = stateBuffer.poll();

        // Follow local player position
        if (snap != null && !snap.players.isEmpty()) {
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

        // ── Render world (camera space) ───────────────────────────────────────
        Gdx.gl.glClearColor(0.08f, 0.08f, 0.12f, 1f);
        Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT);

        batch.setProjectionMatrix(camera.cam.combined);
        batch.begin();
            chunkRenderer.render(batch, camera);
            entityRenderer.render(batch, snap, delta);
        batch.end();

        // Prune stale entity animation state (not in latest snap)
        entityRenderer.pruneEntities(snap);

        // ── HUD (screen space) ────────────────────────────────────────────────
        hudRenderer.render(snap, stateBuffer.isConnected(),
            Gdx.graphics.getFramesPerSecond(), localSlot);
    }

    @Override
    public void resize(int width, int height) {
        camera.resize(width, height);
        hudRenderer.resize(width, height);
        batch.setProjectionMatrix(camera.cam.combined);
    }

    @Override
    public void pause() {
        // Nothing to do — server runs headlessly, network keeps ticking
    }

    @Override
    public void dispose() {
        if (networkClient != null) networkClient.shutdown();
        if (batch          != null) batch.dispose();
        if (anims          != null) anims.dispose();
        if (chunkRenderer  != null) chunkRenderer.dispose();
        if (hudRenderer    != null) hudRenderer.dispose();
    }
}
