package com.indieniinja.client.ui;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.Input;
import com.badlogic.gdx.Screen;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.GL20;
import com.badlogic.gdx.graphics.g2d.BitmapFont;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.indieniinja.client.GameScreen;
import com.indieniinja.client.NinjaGameClient;

/**
 * Mode selection screen — shown after main menu, before GameScreen.
 *
 * Three modes:
 *   ARCADE   — infinite procedural dungeon, score + depth tracking
 *   CAMPAIGN — story-driven missions, hub worlds, ability gates
 *   SANDBOX  — all abilities, 500g starter currency, no story pressure
 *
 * Port of Python ui/mode_selection_menu.py GameModeSelectionMenu.
 *
 * Controls: LEFT/RIGHT or A/D to cycle modes, ENTER or SPACE to confirm.
 * Mouse click on a card also selects + confirms.
 */
public final class ModeSelectScreen implements Screen {

    private static final String[] MODE_IDS    = {"arcade", "campaign", "solo", "sandbox"};
    private static final String[] MODE_NAMES  = {"ARCADE", "CAMPAIGN", "SOLO", "SANDBOX"};
    private static final String[] MODE_DESC   = {
        "Endless procedural dungeons.\nScore points, go deeper.\nNo story — pure action.",
        "Story-driven progression.\nMissions, hub worlds,\nability gates & lore.",
        "Play offline — no server.\nLocal simulation, full game.\nPerfect for development.",
        "Freeform play.\nAll abilities unlocked.\n500g starter currency."
    };
    private static final Color[] MODE_COLORS = {
        new Color(0.20f, 0.75f, 0.45f, 1f),  // arcade    = green
        new Color(0.35f, 0.55f, 1.00f, 1f),  // campaign  = blue
        new Color(0.80f, 0.35f, 0.90f, 1f),  // solo      = purple
        new Color(0.95f, 0.70f, 0.20f, 1f),  // sandbox   = gold
    };

    // Card layout
    private static final float CARD_W  = 230f;
    private static final float CARD_H  = 220f;
    private static final float CARD_GAP = 20f;

    private final NinjaGameClient game;
    private final String          host;
    private final int             port;

    private int selectedIndex = 0;  // 0=arcade, 1=campaign, 2=sandbox

    private final SpriteBatch    batch;
    private final ShapeRenderer  shapes;
    private final BitmapFont     fontLarge;
    private final BitmapFont     fontSmall;

    public ModeSelectScreen(NinjaGameClient game, String host, int port) {
        this.game = game;
        this.host = host;
        this.port = port;

        batch     = new SpriteBatch();
        shapes    = new ShapeRenderer();
        fontLarge = new BitmapFont();
        fontLarge.getData().setScale(1.8f);
        fontSmall = new BitmapFont();
        fontSmall.getData().setScale(0.9f);
    }

    // ── Screen lifecycle ──────────────────────────────────────────────────────

    @Override
    public void show() {
        Gdx.input.setInputProcessor(null);  // manual input polling
    }

    @Override
    public void render(float delta) {
        handleInput();

        int sw = Gdx.graphics.getWidth();
        int sh = Gdx.graphics.getHeight();

        Gdx.gl.glClearColor(UiStyle.BG.r, UiStyle.BG.g, UiStyle.BG.b, 1f);
        Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT);

        // Total width for 4 cards
        float totalW = CARD_W * 4 + CARD_GAP * 3;
        float startX = (sw - totalW) * 0.5f;
        float cardY  = sh * 0.5f - CARD_H * 0.5f - 20f;

        // ── Draw cards (shapes pass) ──────────────────────────────────────────
        shapes.getProjectionMatrix().setToOrtho2D(0, 0, sw, sh);
        shapes.begin(ShapeRenderer.ShapeType.Filled);

        for (int i = 0; i < 4; i++) {
            float x = startX + i * (CARD_W + CARD_GAP);
            boolean sel = (i == selectedIndex);

            // Card background
            Color bg = sel
                ? new Color(MODE_COLORS[i].r * 0.25f, MODE_COLORS[i].g * 0.25f, MODE_COLORS[i].b * 0.25f, 1f)
                : new Color(0.10f, 0.10f, 0.14f, 1f);
            shapes.setColor(bg);
            shapes.rect(x, cardY, CARD_W, CARD_H);

            // Selected highlight strip at top
            if (sel) {
                shapes.setColor(MODE_COLORS[i]);
                shapes.rect(x, cardY + CARD_H - 5f, CARD_W, 5f);
            }
        }
        shapes.end();

        shapes.begin(ShapeRenderer.ShapeType.Line);
        for (int i = 0; i < 4; i++) {
            float x = startX + i * (CARD_W + CARD_GAP);
            boolean sel = (i == selectedIndex);
            shapes.setColor(sel ? MODE_COLORS[i] : new Color(0.3f, 0.3f, 0.4f, 1f));
            shapes.rect(x, cardY, CARD_W, CARD_H);
        }
        shapes.end();

        // ── Text pass ─────────────────────────────────────────────────────────
        batch.getProjectionMatrix().setToOrtho2D(0, 0, sw, sh);
        batch.begin();

        // Screen title
        fontLarge.setColor(Color.WHITE);
        fontLarge.draw(batch, "SELECT  GAME  MODE",
            sw * 0.5f - 140f, sh * 0.5f + CARD_H * 0.5f + 60f);

        for (int i = 0; i < 4; i++) {
            float x = startX + i * (CARD_W + CARD_GAP);
            boolean sel = (i == selectedIndex);

            // Mode name
            fontLarge.setColor(sel ? MODE_COLORS[i] : new Color(0.7f, 0.7f, 0.7f, 1f));
            fontLarge.draw(batch, MODE_NAMES[i], x + 14f, cardY + CARD_H - 20f);

            // Description (split by \n)
            fontSmall.setColor(sel ? Color.WHITE : new Color(0.55f, 0.55f, 0.60f, 1f));
            String[] lines = MODE_DESC[i].split("\n");
            float lineY = cardY + CARD_H - 55f;
            for (String line : lines) {
                fontSmall.draw(batch, line, x + 14f, lineY);
                lineY -= 18f;
            }

            // "► SELECT" prompt on selected card
            if (sel) {
                fontSmall.setColor(MODE_COLORS[i]);
                fontSmall.draw(batch, "► ENTER to play", x + 14f, cardY + 20f);
            }
        }

        // Bottom hint
        fontSmall.setColor(new Color(0.45f, 0.45f, 0.50f, 1f));
        fontSmall.draw(batch, "[ ← → ] navigate    [ ENTER ] confirm    [ ESC ] back",
            sw * 0.5f - 210f, cardY - 20f);

        fontSmall.setColor(Color.WHITE);
        batch.end();

        // ── Mouse hover detection ─────────────────────────────────────────────
        float mx = Gdx.input.getX();
        float my = sh - Gdx.input.getY();  // flip Y (libGDX Y-up)
        for (int i = 0; i < 4; i++) {
            float cx = startX + i * (CARD_W + CARD_GAP);
            if (mx >= cx && mx <= cx + CARD_W && my >= cardY && my <= cardY + CARD_H) {
                if (Gdx.input.justTouched()) {
                    if (selectedIndex == i) confirmMode();
                    else selectedIndex = i;
                } else {
                    selectedIndex = i;
                }
                break;
            }
        }
    }

    @Override public void resize(int w, int h) {}
    @Override public void pause()  {}
    @Override public void resume() {}
    @Override public void hide()   {}

    @Override
    public void dispose() {
        batch.dispose();
        shapes.dispose();
        fontLarge.dispose();
        fontSmall.dispose();
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private void handleInput() {
        if (Gdx.input.isKeyJustPressed(Input.Keys.LEFT)  || Gdx.input.isKeyJustPressed(Input.Keys.A))
            selectedIndex = (selectedIndex + 3) % 4;
        if (Gdx.input.isKeyJustPressed(Input.Keys.RIGHT) || Gdx.input.isKeyJustPressed(Input.Keys.D))
            selectedIndex = (selectedIndex + 1) % 4;
        if (Gdx.input.isKeyJustPressed(Input.Keys.ENTER) || Gdx.input.isKeyJustPressed(Input.Keys.SPACE))
            confirmMode();
        if (Gdx.input.isKeyJustPressed(Input.Keys.ESCAPE))
            game.setScreen(new MainMenuScreen(game, host, port));
    }

    private void confirmMode() {
        game.setScreen(new GameScreen(game, host, port, MODE_IDS[selectedIndex]));
    }
}
