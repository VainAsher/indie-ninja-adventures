package com.indieniinja.client.ui;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.Input;
import com.badlogic.gdx.Screen;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.GL20;
import com.badlogic.gdx.graphics.g2d.BitmapFont;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.indieniinja.client.NinjaGameClient;
import com.indieniinja.client.game.SaveManager;

/**
 * Save-slot selection screen — shown after main menu, before mode select.
 *
 * Displays up to SaveManager.MAX_SLOTS cards. Each card shows slot info (save
 * date + playtime) or "NEW GAME" if the slot is empty. Selecting a slot
 * transitions to ModeSelectScreen with the chosen slot index.
 *
 * Controls: LEFT/RIGHT or A/D to cycle, ENTER/SPACE to confirm, ESC to go back.
 */
public final class SlotSelectScreen implements Screen {

    private static final float CARD_W   = 230f;
    private static final float CARD_H   = 200f;
    private static final float CARD_GAP = 20f;

    private static final Color COL_EMPTY    = new Color(0.25f, 0.55f, 0.35f, 1f);
    private static final Color COL_OCCUPIED = new Color(0.35f, 0.55f, 1.00f, 1f);
    private static final Color COL_CORRUPT  = new Color(0.75f, 0.25f, 0.20f, 1f);

    private final NinjaGameClient       game;
    private final String                host;
    private final int                   port;
    private final SaveManager.SlotInfo[] slots;

    private int selectedIndex = 0;

    private final SpriteBatch   batch;
    private final ShapeRenderer shapes;
    private final BitmapFont    fontLarge;
    private final BitmapFont    fontSmall;

    public SlotSelectScreen(NinjaGameClient game, String host, int port) {
        this.game  = game;
        this.host  = host;
        this.port  = port;
        this.slots = SaveManager.listSlots();

        batch     = new SpriteBatch();
        shapes    = new ShapeRenderer();
        fontLarge = new BitmapFont();
        fontLarge.getData().setScale(1.8f);
        fontSmall = new BitmapFont();
        fontSmall.getData().setScale(0.9f);
    }

    @Override public void show() { Gdx.input.setInputProcessor(null); }

    @Override
    public void render(float delta) {
        handleInput();

        int sw = Gdx.graphics.getWidth();
        int sh = Gdx.graphics.getHeight();

        Gdx.gl.glClearColor(UiStyle.BG.r, UiStyle.BG.g, UiStyle.BG.b, 1f);
        Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT);

        int count    = SaveManager.MAX_SLOTS;
        float totalW = CARD_W * count + CARD_GAP * (count - 1);
        float startX = (sw - totalW) * 0.5f;
        float cardY  = sh * 0.5f - CARD_H * 0.5f - 20f;

        shapes.getProjectionMatrix().setToOrtho2D(0, 0, sw, sh);
        shapes.begin(ShapeRenderer.ShapeType.Filled);
        for (int i = 0; i < count; i++) {
            float x    = startX + i * (CARD_W + CARD_GAP);
            Color col  = cardColor(slots[i]);
            boolean sel = (i == selectedIndex);
            Color bg = sel
                ? new Color(col.r * 0.25f, col.g * 0.25f, col.b * 0.25f, 1f)
                : new Color(0.10f, 0.10f, 0.14f, 1f);
            shapes.setColor(bg);
            shapes.rect(x, cardY, CARD_W, CARD_H);
            if (sel) { shapes.setColor(col); shapes.rect(x, cardY + CARD_H - 5f, CARD_W, 5f); }
        }
        shapes.end();

        shapes.begin(ShapeRenderer.ShapeType.Line);
        for (int i = 0; i < count; i++) {
            float x   = startX + i * (CARD_W + CARD_GAP);
            Color col = cardColor(slots[i]);
            shapes.setColor(i == selectedIndex ? col : new Color(0.3f, 0.3f, 0.4f, 1f));
            shapes.rect(x, cardY, CARD_W, CARD_H);
        }
        shapes.end();

        batch.getProjectionMatrix().setToOrtho2D(0, 0, sw, sh);
        batch.begin();

        fontLarge.setColor(Color.WHITE);
        fontLarge.draw(batch, "SELECT  SAVE  SLOT",
            sw * 0.5f - 140f, sh * 0.5f + CARD_H * 0.5f + 60f);

        for (int i = 0; i < count; i++) {
            float  x    = startX + i * (CARD_W + CARD_GAP);
            boolean sel  = (i == selectedIndex);
            Color  col  = cardColor(slots[i]);
            SaveManager.SlotInfo info = slots[i];

            fontLarge.setColor(sel ? col : new Color(0.7f, 0.7f, 0.7f, 1f));
            fontLarge.draw(batch, "SLOT " + info.slot(), x + 14f, cardY + CARD_H - 20f);

            fontSmall.setColor(sel ? Color.WHITE : new Color(0.55f, 0.55f, 0.60f, 1f));
            if (info.isEmpty()) {
                fontSmall.draw(batch, "New Game", x + 14f, cardY + CARD_H - 60f);
            } else if ("[corrupt]".equals(info.saveDate())) {
                fontSmall.draw(batch, "CORRUPT", x + 14f, cardY + CARD_H - 60f);
                fontSmall.draw(batch, "(select to reset)", x + 14f, cardY + CARD_H - 85f);
            } else {
                fontSmall.draw(batch, info.saveDate(), x + 14f, cardY + CARD_H - 60f);
                int mins = (int)(info.totalPlaytime() / 60f);
                fontSmall.draw(batch, "Playtime: " + mins + " min", x + 14f, cardY + CARD_H - 85f);
                if (info.currentLevel() != null) {
                    fontSmall.draw(batch, info.currentLevel(), x + 14f, cardY + CARD_H - 110f);
                }
            }
        }

        // Footer hint
        fontSmall.setColor(new Color(0.4f, 0.4f, 0.5f, 1f));
        fontSmall.draw(batch, "LEFT/RIGHT — select    ENTER — confirm    ESC — back",
            sw * 0.5f - 210f, 30f);

        batch.end();
    }

    private static Color cardColor(SaveManager.SlotInfo info) {
        if (info == null || info.isEmpty()) return COL_EMPTY;
        if ("[corrupt]".equals(info.saveDate())) return COL_CORRUPT;
        return COL_OCCUPIED;
    }

    private void handleInput() {
        int count = SaveManager.MAX_SLOTS;

        if (Gdx.input.isKeyJustPressed(Input.Keys.LEFT)  || Gdx.input.isKeyJustPressed(Input.Keys.A))
            selectedIndex = (selectedIndex - 1 + count) % count;
        if (Gdx.input.isKeyJustPressed(Input.Keys.RIGHT) || Gdx.input.isKeyJustPressed(Input.Keys.D))
            selectedIndex = (selectedIndex + 1) % count;

        if (Gdx.input.isKeyJustPressed(Input.Keys.ENTER) || Gdx.input.isKeyJustPressed(Input.Keys.SPACE)) {
            int slot = selectedIndex + 1;  // slots are 1-indexed
            game.setScreen(new ModeSelectScreen(game, host, port, slot));
        }

        if (Gdx.input.isKeyJustPressed(Input.Keys.ESCAPE)) {
            game.setScreen(new MainMenuScreen(game, host, port));
        }
    }

    @Override public void resize(int w, int h) {}
    @Override public void pause()  {}
    @Override public void resume() {}

    @Override
    public void hide() {}

    @Override
    public void dispose() {
        batch.dispose();
        shapes.dispose();
        fontLarge.dispose();
        fontSmall.dispose();
    }
}
