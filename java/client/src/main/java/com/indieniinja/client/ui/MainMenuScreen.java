package com.indieniinja.client.ui;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.Screen;
import com.badlogic.gdx.graphics.GL20;
import com.badlogic.gdx.scenes.scene2d.Actor;
import com.badlogic.gdx.scenes.scene2d.Stage;
import com.badlogic.gdx.scenes.scene2d.ui.Label;
import com.badlogic.gdx.scenes.scene2d.ui.Skin;
import com.badlogic.gdx.scenes.scene2d.ui.Table;
import com.badlogic.gdx.scenes.scene2d.ui.TextButton;
import com.badlogic.gdx.scenes.scene2d.utils.ChangeListener;
import com.badlogic.gdx.utils.viewport.ScreenViewport;
import com.indieniinja.client.GameScreen;
import com.indieniinja.client.NinjaGameClient;

/**
 * Title / connection screen shown on startup.
 *
 * Built with Scene2D — no external skin asset required (programmatic skin).
 * Transitions to GameScreen when the player clicks CONNECT.
 */
public final class MainMenuScreen implements Screen {

    private final NinjaGameClient game;
    private final String          host;
    private final int             port;

    private final Stage stage;
    private final Skin  skin;

    public MainMenuScreen(NinjaGameClient game, String host, int port) {
        this.game = game;
        this.host = host;
        this.port = port;

        stage = new Stage(new ScreenViewport());
        skin  = UiStyle.build();
        buildUi();
    }

    // ── UI layout ─────────────────────────────────────────────────────────────

    private void buildUi() {
        Table root = new Table();
        root.setFillParent(true);

        // Title
        root.add(new Label("INDIE NINJA ADVENTURES", skin, "large")).padBottom(4).row();
        root.add(new Label("Java Client  ·  libGDX", skin, "dim")).padBottom(48).row();

        // Server address
        root.add(new Label("Server: " + host + ":" + port, skin, "accent")).padBottom(32).row();

        // CONNECT button
        TextButton connectBtn = new TextButton("  CONNECT  ", skin);
        connectBtn.addListener(new ChangeListener() {
            @Override public void changed(ChangeEvent event, Actor actor) {
                game.setScreen(new GameScreen(game, host, port));
            }
        });
        root.add(connectBtn).width(220).height(48).padBottom(12).row();

        // QUIT button
        TextButton quitBtn = new TextButton("  QUIT  ", skin);
        quitBtn.addListener(new ChangeListener() {
            @Override public void changed(ChangeEvent event, Actor actor) {
                Gdx.app.exit();
            }
        });
        root.add(quitBtn).width(220).height(48).row();

        // Version note
        root.add(new Label("v" + com.indieniinja.network.MessageType.PROTOCOL_VERSION
            + "  ·  " + host + ":" + port, skin, "dim"))
            .padTop(48).row();

        stage.addActor(root);
    }

    // ── Screen lifecycle ──────────────────────────────────────────────────────

    @Override
    public void show() {
        Gdx.input.setInputProcessor(stage);
    }

    @Override
    public void render(float delta) {
        Gdx.gl.glClearColor(UiStyle.BG.r, UiStyle.BG.g, UiStyle.BG.b, 1f);
        Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT);
        stage.act(delta);
        stage.draw();
    }

    @Override
    public void resize(int w, int h) {
        stage.getViewport().update(w, h, true);
    }

    @Override public void pause()  {}
    @Override public void resume() {}
    @Override public void hide()   {}

    @Override
    public void dispose() {
        stage.dispose();
        skin.dispose();
    }
}
