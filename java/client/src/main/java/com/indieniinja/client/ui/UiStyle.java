package com.indieniinja.client.ui;

import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.Pixmap;
import com.badlogic.gdx.graphics.Texture;
import com.badlogic.gdx.graphics.g2d.BitmapFont;
import com.badlogic.gdx.graphics.g2d.NinePatch;
import com.badlogic.gdx.scenes.scene2d.ui.Label;
import com.badlogic.gdx.scenes.scene2d.ui.Skin;
import com.badlogic.gdx.scenes.scene2d.ui.TextButton;
import com.badlogic.gdx.scenes.scene2d.utils.NinePatchDrawable;

/**
 * Programmatic Scene2D skin — no external skin-file dependency.
 * Used by MainMenuScreen and PauseScreen so the client runs without assets.
 */
public final class UiStyle {

    // Brand colours matching the launcher palette
    public static final Color BG       = new Color(0.08f, 0.08f, 0.12f, 1f);
    public static final Color ACCENT   = new Color(0.20f, 0.75f, 0.45f, 1f);  // green
    public static final Color TEXT     = Color.WHITE;
    public static final Color TEXT_DIM = new Color(0.55f, 0.55f, 0.60f, 1f);
    public static final Color BTN_UP   = new Color(0.16f, 0.18f, 0.22f, 1f);
    public static final Color BTN_OVER = new Color(0.22f, 0.25f, 0.30f, 1f);
    public static final Color BTN_DOWN = new Color(0.10f, 0.12f, 0.15f, 1f);

    private UiStyle() {}

    /** Build and return a programmatic Skin. Caller must dispose() it when done. */
    public static Skin build() {
        Skin skin = new Skin();

        // ── Fonts ─────────────────────────────────────────────────────────────
        BitmapFont font = new BitmapFont();          // built-in 15-px Arial
        BitmapFont fontLarge = new BitmapFont();
        fontLarge.getData().setScale(2f);
        skin.add("default-font", font);
        skin.add("font-large",   fontLarge);

        // ── Drawables ─────────────────────────────────────────────────────────
        skin.add("btn-up",   solidDrawable(BTN_UP));
        skin.add("btn-over", solidDrawable(BTN_OVER));
        skin.add("btn-down", solidDrawable(BTN_DOWN));
        skin.add("dim-bg",   solidDrawable(new Color(0f, 0f, 0f, 0.65f)));

        // ── Label styles ──────────────────────────────────────────────────────
        Label.LabelStyle lblDefault = new Label.LabelStyle(font, TEXT);
        Label.LabelStyle lblLarge   = new Label.LabelStyle(fontLarge, TEXT);
        Label.LabelStyle lblDim     = new Label.LabelStyle(font, TEXT_DIM);
        Label.LabelStyle lblAccent  = new Label.LabelStyle(font, ACCENT);
        skin.add("default", lblDefault);
        skin.add("large",   lblLarge);
        skin.add("dim",     lblDim);
        skin.add("accent",  lblAccent);

        // ── TextButton style ──────────────────────────────────────────────────
        TextButton.TextButtonStyle btnStyle = new TextButton.TextButtonStyle();
        btnStyle.font      = font;
        btnStyle.fontColor = TEXT;
        btnStyle.up        = skin.getDrawable("btn-up");
        btnStyle.over      = skin.getDrawable("btn-over");
        btnStyle.down      = skin.getDrawable("btn-down");
        skin.add("default", btnStyle);

        return skin;
    }

    private static NinePatchDrawable solidDrawable(Color color) {
        Pixmap pix = new Pixmap(1, 1, Pixmap.Format.RGBA8888);
        pix.setColor(color);
        pix.fill();
        NinePatchDrawable d = new NinePatchDrawable(new NinePatch(new Texture(pix)));
        pix.dispose();
        return d;
    }
}
