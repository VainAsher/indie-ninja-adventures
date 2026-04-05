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
import com.indieniinja.client.rendering.ChunkRenderer;
import com.indieniinja.client.rendering.EntityRenderer;
import com.indieniinja.client.rendering.HudRenderer;
import com.indieniinja.client.ui.PauseScreen;
import com.indieniinja.network.InputCommand;
import com.indieniinja.network.PlayerState;
import com.indieniinja.network.WorldSnapshot;
import com.indieniinja.physics.PhysicsConstants;

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
    private static final int   LEVEL_COLS     = 50;
    private static final int   LEVEL_ROWS     = 28;

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
    private ChunkRenderer     chunkRenderer;
    private EntityRenderer    entityRenderer;
    private HudRenderer       hudRenderer;

    // ── Pause overlay ─────────────────────────────────────────────────────────
    private PauseScreen pauseScreen;
    private boolean     paused = false;

    // ── Fixed-timestep state ──────────────────────────────────────────────────
    private float accumulator = 0f;
    private int   localSlot   = 0;

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
        stateBuffer = new GameStateBuffer();
        inputPoller = new InputPoller();

        anims = new AnimationRegistry();
        FileHandle atlasFile = Gdx.files.internal("assets/characters.atlas");
        if (atlasFile.exists()) {
            anims.loadAtlas(new TextureAtlas(atlasFile));
        } else {
            anims.loadPlaceholder();
        }

        chunkRenderer = new ChunkRenderer();
        chunkRenderer.loadPlaceholderLayout(LEVEL_COLS, LEVEL_ROWS);

        entityRenderer = new EntityRenderer(anims);
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

        // ── Render world ──────────────────────────────────────────────────────
        Gdx.gl.glClearColor(0.08f, 0.08f, 0.12f, 1f);
        Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT);

        batch.setProjectionMatrix(camera.cam.combined);
        batch.begin();
            chunkRenderer.render(batch, camera);
            entityRenderer.render(batch, snap, delta);
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
        if (networkClient != null) networkClient.shutdown();
        if (batch          != null) batch.dispose();
        if (anims          != null) anims.dispose();
        if (chunkRenderer  != null) chunkRenderer.dispose();
        if (hudRenderer    != null) hudRenderer.dispose();
        if (pauseScreen    != null) pauseScreen.dispose();
    }
}
