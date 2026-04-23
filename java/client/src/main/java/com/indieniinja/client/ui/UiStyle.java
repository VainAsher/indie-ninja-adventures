package com.indieniinja.client.ui;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.Pixmap;
import com.badlogic.gdx.graphics.Texture;
import com.badlogic.gdx.graphics.g2d.BitmapFont;
import com.badlogic.gdx.graphics.g2d.NinePatch;
import com.badlogic.gdx.scenes.scene2d.ui.Label;
import com.badlogic.gdx.scenes.scene2d.ui.Skin;
import com.badlogic.gdx.scenes.scene2d.ui.TextButton;
import com.badlogic.gdx.scenes.scene2d.utils.Drawable;
import com.badlogic.gdx.scenes.scene2d.utils.NinePatchDrawable;

/**
 * Programmatic Scene2D skin — no external skin-file dependency.
 * Used by MainMenuScreen and PauseScreen so the client runs without assets.
 *
 * Note: skin.add(name, drawable) stores by the concrete class (NinePatchDrawable),
 * but skin.getDrawable(name) searches for Drawable.class. To make getDrawable work,
 * drawables must be registered with skin.add(name, drawable, Drawable.class).
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
        if (Gdx.app == null) return new Skin();
        Skin skin = new Skin();

        // ── Fonts ─────────────────────────────────────────────────────────────
        BitmapFont font = new BitmapFont();          // built-in 15-px Arial
        BitmapFont fontLarge = new BitmapFont();
        fontLarge.getData().setScale(2f);
        skin.add("default-font", font);
        skin.add("font-large",   fontLarge);

        // ── Drawables — must register as Drawable.class for getDrawable() ─────
        NinePatchDrawable btnUp   = solidDrawable(BTN_UP);
        NinePatchDrawable btnOver = solidDrawable(BTN_OVER);
        NinePatchDrawable btnDown = solidDrawable(BTN_DOWN);
        NinePatchDrawable dimBg   = solidDrawable(new Color(0f, 0f, 0f, 0.65f));
        skin.add("btn-up",   btnUp,   Drawable.class);
        skin.add("btn-over", btnOver, Drawable.class);
        skin.add("btn-down", btnDown, Drawable.class);
        skin.add("dim-bg",   dimBg,   Drawable.class);

        // ── Label styles ──────────────────────────────────────────────────────
        skin.add("default", new Label.LabelStyle(font,      TEXT),     Label.LabelStyle.class);
        skin.add("large",   new Label.LabelStyle(fontLarge, TEXT),     Label.LabelStyle.class);
        skin.add("dim",     new Label.LabelStyle(font,      TEXT_DIM), Label.LabelStyle.class);
        skin.add("accent",  new Label.LabelStyle(font,      ACCENT),   Label.LabelStyle.class);

        // ── TextButton style — assign drawables directly (no getDrawable call) ─
        TextButton.TextButtonStyle btnStyle = new TextButton.TextButtonStyle();
        btnStyle.font      = font;
        btnStyle.fontColor = TEXT;
        btnStyle.up        = btnUp;
        btnStyle.over      = btnOver;
        btnStyle.down      = btnDown;
        skin.add("default", btnStyle, TextButton.TextButtonStyle.class);

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
