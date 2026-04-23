package com.indieniinja.client.ui;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.graphics.GL20;
import com.badlogic.gdx.scenes.scene2d.Actor;
import com.badlogic.gdx.scenes.scene2d.Stage;
import com.badlogic.gdx.scenes.scene2d.ui.Label;
import com.badlogic.gdx.scenes.scene2d.ui.Skin;
import com.badlogic.gdx.scenes.scene2d.ui.Table;
import com.badlogic.gdx.scenes.scene2d.ui.TextButton;
import com.badlogic.gdx.scenes.scene2d.utils.ChangeListener;
import com.badlogic.gdx.utils.viewport.ScreenViewport;
import com.indieniinja.client.NinjaGameClient;

/**
 * Pause overlay — rendered on top of the game world by GameScreen.
 *
 * Not a Screen implementation; it's a lightweight Stage wrapper that
 * GameScreen renders when ESC is pressed. The game world continues to
 * render underneath (network stays live).
 */
public final class PauseScreen {

    private final NinjaGameClient game;
    private final Stage           stage;
    private final Skin            skin;

    /** Called by GameScreen to dismiss the overlay and resume play. */
    public interface ResumeCallback { void onResume(); }

    public PauseScreen(NinjaGameClient game, ResumeCallback onResume) {
        this.game = game;
        if (Gdx.app != null) {
            stage = new Stage(new ScreenViewport());
            skin  = UiStyle.build();
            buildUi(onResume);
        } else {
            stage = null;
            skin = null;
        }
    }

    private void buildUi(ResumeCallback onResume) {
        // Semi-transparent dim background
        Table dim = new Table();
        dim.setFillParent(true);
        dim.setBackground(skin.getDrawable("dim-bg"));
        stage.addActor(dim);

        // Centred card
        Table card = new Table();
        card.setFillParent(true);

        card.add(new Label("PAUSED", skin, "large")).padBottom(32).row();

        TextButton resumeBtn = new TextButton("  RESUME  ", skin);
        resumeBtn.addListener(new ChangeListener() {
            @Override public void changed(ChangeEvent event, Actor actor) {
                onResume.onResume();
            }
        });
        card.add(resumeBtn).width(220).height(48).padBottom(12).row();

        TextButton menuBtn = new TextButton("  MAIN MENU  ", skin);
        menuBtn.addListener(new ChangeListener() {
            @Override public void changed(ChangeEvent event, Actor actor) {
                game.setScreen(new MainMenuScreen(game,
                    game.getHost(), game.getPort()));
            }
        });
        card.add(menuBtn).width(220).height(48).padBottom(12).row();

        TextButton quitBtn = new TextButton("  QUIT  ", skin);
        quitBtn.addListener(new ChangeListener() {
            @Override public void changed(ChangeEvent event, Actor actor) {
                Gdx.app.exit();
            }
        });
        card.add(quitBtn).width(220).height(48).row();

        stage.addActor(card);
    }

    /** Hand input to this overlay — call when transitioning to paused state. */
    public void activate() {
        if (stage != null && Gdx.input != null) {
            Gdx.input.setInputProcessor(stage);
        }
    }

    /** Render the dim overlay + pause menu (call after game world is drawn). */
    public void render(float delta) {
        if (stage == null) return;
        stage.act(delta);
        stage.draw();
    }

    public void resize(int w, int h) {
        if (stage == null) return;
        stage.getViewport().update(w, h, true);
    }

    public void dispose() {
        if (stage != null) stage.dispose();
        if (skin != null) skin.dispose();
    }
}
