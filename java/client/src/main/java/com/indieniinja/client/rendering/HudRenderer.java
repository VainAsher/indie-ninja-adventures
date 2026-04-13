package com.indieniinja.client.rendering;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.OrthographicCamera;
import com.badlogic.gdx.graphics.g2d.BitmapFont;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.indieniinja.network.PlayerState;
import com.indieniinja.network.WorldSnapshot;

/**
 * Renders the in-game HUD using ShapeRenderer (health bars) + BitmapFont (text).
 *
 * Equivalent of Python's rendering/hud_renderer.py.
 *
 * Drawn in screen space — the SpriteBatch projection must be set to the screen
 * (identity or screen-space camera) before calling render(). NinjaGameClient
 * resets the projection after world rendering.
 *
 * Layout (top-left origin, Y up):
 *   [10, screenH - 10]  Slot 0 health bar
 *   [10, screenH - 35]  Slot 1 health bar (if second player connected)
 *   …
 *   [screenW - 80, 10]  Connection indicator
 *   [screenW - 80, 25]  FPS counter (debug)
 */
public final class HudRenderer {

    // ── Per-player bar dimensions ─────────────────────────────────────────────
    private static final float BAR_W      = 120f;  // health bar width
    private static final float BAR_H      = 10f;   // health bar height
    private static final float BAR_GAP    = 26f;   // vertical spacing between players
    private static final int   MAX_HP     = 5;
    private static final float STAM_W     = 100f;  // merged stamina bar (general + wall-slide)
    private static final float STAM_H     = 5f;
    private static final float MAX_STAMINA = 3.0f;
    private static final float MANA_W     = 100f;
    private static final float MANA_H     = 5f;
    private static final float XP_W       = 100f;
    private static final float XP_H       = 3f;
    // Row offsets below the health bar (all local-player rows)
    private static final float STAM_OFF   = BAR_H + 4f;   // 14 px below health top
    private static final float MANA_OFF   = STAM_OFF + STAM_H + 3f;
    private static final float XP_OFF     = MANA_OFF + MANA_H + 2f;

    // ── Lantern indicator — bottom-left ───────────────────────────────────────
    private static final float LAN_W      = 80f;
    private static final float LAN_H      = 7f;
    private static final float LAN_X      = 10f;
    private static final float LAN_Y      = 90f;  // above currency row

    private final ShapeRenderer shapes;
    private final SpriteBatch   hudBatch;
    private final BitmapFont    font;

    private final OrthographicCamera screenCam;

    // ── Ability unlock toasts ─────────────────────────────────────────────────
    private static final float TOAST_TTL  = 3.0f;
    private static final float TOAST_FADE = 0.8f;   // start fading in final 0.8s
    private final java.util.List<String> toastTexts = new java.util.ArrayList<>();
    private final java.util.List<Float>  toastTtls  = new java.util.ArrayList<>();

    public HudRenderer() {
        shapes    = new ShapeRenderer();
        hudBatch  = new SpriteBatch();
        font      = new BitmapFont();   // built-in libGDX 15px font
        font.setColor(Color.WHITE);

        screenCam = new OrthographicCamera();
        screenCam.setToOrtho(false, Gdx.graphics.getWidth(), Gdx.graphics.getHeight());
    }

    /**
     * Render the full HUD for this frame.
     *
     * @param snap        latest world snapshot (may be null before first server message)
     * @param connected   whether the network client has an active connection
     * @param fps         current frames per second (for debug overlay)
     * @param localSlot   which player slot belongs to this client (for highlighting)
     */
    public void render(WorldSnapshot snap, boolean connected, int fps, int localSlot) {
        int sw = Gdx.graphics.getWidth();
        int sh = Gdx.graphics.getHeight();

        screenCam.setToOrtho(false, sw, sh);
        screenCam.update();

        // ── Health bars (ShapeRenderer pass) ──────────────────────────────────
        shapes.setProjectionMatrix(screenCam.combined);
        shapes.begin(ShapeRenderer.ShapeType.Filled);

        if (snap != null) {
            for (int i = 0; i < snap.players.size(); i++) {
                PlayerState p = snap.players.get(i);
                float barX = 10f;
                float barY = sh - 14f - i * BAR_GAP;

                // ── Health bar ────────────────────────────────────────────────
                shapes.setColor(0.15f, 0.1f, 0.1f, 0.85f);
                shapes.rect(barX, barY, BAR_W, BAR_H);
                float hpRatio = Math.max(0f, Math.min(1f, (float) p.health / MAX_HP));
                shapes.setColor(healthColor(hpRatio));
                shapes.rect(barX, barY, BAR_W * hpRatio, BAR_H);
                // Local player border
                if (p.slot == localSlot) {
                    shapes.setColor(1f, 1f, 1f, 0.25f);
                    shapes.rect(barX - 1, barY - 1, BAR_W + 2, BAR_H + 2);
                }

                // ── Merged stamina bar (wall-slide overrides general) ─────────
                float stamY = barY - STAM_OFF;
                shapes.setColor(0.1f, 0.1f, 0.15f, 0.8f);
                shapes.rect(barX, stamY, STAM_W, STAM_H);
                if (p.isWallSliding) {
                    // Wall-slide: cyan, shows remaining wall-slide stamina
                    float sr = Math.max(0f, Math.min(1f, p.wallSlideStamina / MAX_STAMINA));
                    shapes.setColor(0.1f, 0.85f, 0.9f, 1f);
                    if (sr > 0f) shapes.rect(barX, stamY, STAM_W * sr, STAM_H);
                    shapes.setColor(0f, 1f, 1f, 0.3f);
                    shapes.rect(barX - 1, stamY - 1, STAM_W + 2, STAM_H + 2);
                } else {
                    // General stamina: green → yellow
                    float gr = Math.max(0f, Math.min(1f, p.stamina / Math.max(1, p.maxStamina)));
                    shapes.setColor(gr * 0.6f, 0.5f + gr * 0.5f, 0.1f, 1f);
                    if (gr > 0f) shapes.rect(barX, stamY, STAM_W * gr, STAM_H);
                }

                // ── Mana bar ──────────────────────────────────────────────────
                float manaY = barY - MANA_OFF;
                float manaR = Math.max(0f, Math.min(1f, p.mana / Math.max(1, p.maxMana)));
                shapes.setColor(0.08f, 0.08f, 0.22f, 0.8f);
                shapes.rect(barX, manaY, MANA_W, MANA_H);
                shapes.setColor(0.25f + manaR * 0.25f, 0.4f + manaR * 0.35f, 1f, 1f);
                if (manaR > 0f) shapes.rect(barX, manaY, MANA_W * manaR, MANA_H);
                if (p.ninjutsuCasting) {
                    shapes.setColor(0.6f, 0.3f, 1f, 0.45f);
                    shapes.rect(barX - 1, manaY - 1, MANA_W + 2, MANA_H + 2);
                }

                // ── XP bar — local player only, very thin gold strip ──────────
                if (p.slot == localSlot) {
                    float xpY = barY - XP_OFF;
                    int xpNeeded = p.level * 50;
                    float xpR = xpNeeded > 0
                        ? Math.max(0f, Math.min(1f, (float) p.experience / xpNeeded)) : 0f;
                    shapes.setColor(0.12f, 0.10f, 0.04f, 0.8f);
                    shapes.rect(barX, xpY, XP_W, XP_H);
                    if (xpR > 0f) {
                        shapes.setColor(0.95f, 0.8f * xpR, 0.1f, 1f);
                        shapes.rect(barX, xpY, XP_W * xpR, XP_H);
                    }
                }
            }

            // ── Lantern indicator — bottom-left (local player only) ───────────
            for (PlayerState p : snap.players) {
                if (p.slot != localSlot) continue;
                float lanR = Math.max(0f, Math.min(1f, p.lanternValue));
                // Background
                shapes.setColor(0.05f, 0.04f, 0.02f, 0.88f);
                shapes.rect(LAN_X, LAN_Y, LAN_W, LAN_H);
                // Fill: dim amber → bright gold
                shapes.setColor(0.45f + lanR * 0.55f, lanR * 0.68f, 0.04f, 1f);
                if (lanR > 0f) shapes.rect(LAN_X, LAN_Y, LAN_W * lanR, LAN_H);
                // Glow when bright
                if (p.lanternValue > 0.65f) {
                    shapes.setColor(1f, 0.88f, 0.35f, 0.28f);
                    shapes.rect(LAN_X - 1, LAN_Y - 1, LAN_W + 2, LAN_H + 2);
                }
                break;
            }
        }

        // ── Boss HP bar (top-centre, prominent) ──────────────────────────────
        if (snap != null && !snap.bosses.isEmpty()) {
            com.indieniinja.network.BossState boss = snap.bosses.get(0);
            if (boss.alive) {
                float bBarW  = Math.min(sw * 0.5f, 400f);
                float bBarH  = 16f;
                float bBarX  = (sw - bBarW) * 0.5f;
                float bBarY  = sh - 40f;
                float bRatio = boss.maxHp > 0 ? (float) boss.hp / boss.maxHp : 0f;

                // Background
                shapes.setColor(0.1f, 0.05f, 0.05f, 0.9f);
                shapes.rect(bBarX - 2, bBarY - 2, bBarW + 4, bBarH + 4);

                // Filled — colour by phase
                Color bCol = switch (boss.phase) {
                    case 2  -> new Color(0.9f, 0.8f, 0.1f, 1f);
                    case 3  -> new Color(0.9f, 0.45f, 0.1f, 1f);
                    case 4  -> new Color(0.85f, 0.1f, 0.1f, 1f);
                    default -> new Color(0.6f, 0.2f, 0.7f, 1f);
                };
                shapes.setColor(bCol);
                shapes.rect(bBarX, bBarY, bBarW * Math.max(0, bRatio), bBarH);

                // Phase divider lines at 75/50/25%
                shapes.setColor(0f, 0f, 0f, 0.6f);
                for (float pct : new float[]{0.75f, 0.50f, 0.25f}) {
                    shapes.rect(bBarX + bBarW * pct - 1f, bBarY, 2f, bBarH);
                }
            }
        }

        // Connection indicator dot
        shapes.setColor(connected ? Color.GREEN : Color.RED);
        shapes.circle(sw - 12f, 12f, 6f);

        shapes.end();

        // ── Text pass (SpriteBatch) ───────────────────────────────────────────
        hudBatch.setProjectionMatrix(screenCam.combined);
        hudBatch.begin();

        // ── Player stat labels ────────────────────────────────────────────────
        if (snap != null) {
            for (int i = 0; i < snap.players.size(); i++) {
                PlayerState p = snap.players.get(i);
                float labelX = 10f + BAR_W + 5f;
                float labelY = sh - 4f - i * BAR_GAP;
                String name  = p.slot == localSlot ? "You" : "P" + (p.slot + 1);
                font.draw(hudBatch, name + " Lv" + p.level + "  " + p.health + "/" + MAX_HP,
                    labelX, labelY);

                if (p.slot == localSlot) {
                    // Stamina label — "WALL" when sliding, otherwise blank (bar speaks for itself)
                    if (p.isWallSliding) {
                        font.setColor(0.1f, 0.95f, 1f, 1f);
                        font.draw(hudBatch, "WALL", labelX, labelY - STAM_OFF + STAM_H);
                        font.setColor(Color.WHITE);
                    }
                    // Mana %
                    int manaPct = (int)(p.mana / Math.max(1, p.maxMana) * 100);
                    font.setColor(0.5f, 0.7f, 1f, 0.9f);
                    font.draw(hudBatch, "MP " + manaPct + "%", labelX, labelY - MANA_OFF + MANA_H);
                    font.setColor(Color.WHITE);
                    // XP
                    int xpNeeded = p.level * 50;
                    font.setColor(0.9f, 0.75f, 0.2f, 0.9f);
                    font.draw(hudBatch, "XP " + p.experience + "/" + xpNeeded,
                        labelX, labelY - XP_OFF + XP_H);
                    font.setColor(Color.WHITE);
                }
            }

            // ── Lantern label — bottom-left ───────────────────────────────────
            for (PlayerState p : snap.players) {
                if (p.slot != localSlot) continue;
                int lanPct = (int)(p.lanternValue * 100);
                float lanLabelAlpha = 0.6f + p.lanternValue * 0.4f;
                font.setColor(0.95f, 0.7f * p.lanternValue + 0.1f, 0.05f, lanLabelAlpha);
                font.draw(hudBatch, "\u25ca " + lanPct + "%", LAN_X + LAN_W + 5f, LAN_Y + LAN_H);
                // Flow Mode indicator near the lantern
                if (p.flowMode) {
                    font.setColor(0.9f, 1f, 0.7f, 0.9f);
                    font.draw(hudBatch, "FLOW", LAN_X + LAN_W + 45f, LAN_Y + LAN_H);
                }
                font.setColor(Color.WHITE);
                break;
            }
        }

        // Connection status
        String connText = connected ? "Online" : "Offline";
        font.draw(hudBatch, connText, sw - 65f, 25f);

        // FPS counter
        font.draw(hudBatch, fps + " fps", sw - 60f, 40f);

        // Mode overlay (top-centre)
        if (snap != null) {
            switch (snap.gameMode != null ? snap.gameMode : "arcade") {
                case "arcade" -> {
                    font.setColor(0.20f, 0.85f, 0.45f, 1f);
                    font.draw(hudBatch, "SCORE  " + snap.arcadeScore
                        + "     DEPTH  " + snap.arcadeDepth,
                        sw * 0.5f - 90f, sh - 6f);
                    font.setColor(Color.WHITE);
                }
                case "sandbox" -> {
                    font.setColor(0.95f, 0.70f, 0.20f, 1f);
                    font.draw(hudBatch, "SANDBOX  MODE", sw * 0.5f - 60f, sh - 6f);
                    font.setColor(Color.WHITE);
                }
                case "campaign" -> { /* mission HUD handled by DialogueOverlay */ }
            }
        }

        // Frame number (debug)
        if (snap != null) {
            font.draw(hudBatch, "f:" + snap.frame, sw - 60f, 55f);
        }

        // Currency (local player) — shown bottom-left above bars area
        if (snap != null) {
            for (PlayerState p : snap.players) {
                if (p.slot == localSlot && p.inventory != null) {
                    font.setColor(1f, 0.85f, 0.2f, 1f);
                    font.draw(hudBatch, "\u25c6 " + p.inventory.currency + "g",
                        10f, 75f);
                    font.setColor(Color.WHITE);
                    // Controls hint
                    font.setColor(0.5f, 0.5f, 0.5f, 1f);
                    font.draw(hudBatch, "[I]inv [M]map", 10f, 60f);
                    font.setColor(Color.WHITE);
                    break;
                }
            }
        }

        hudBatch.end();

        // ── Death overlay ─────────────────────────────────────────────────────
        if (snap != null) {
            boolean localDead = snap.players.stream()
                .anyMatch(p -> p.slot == localSlot && p.isDead);
            if (localDead) {
                // Dark translucent vignette
                shapes.setProjectionMatrix(screenCam.combined);
                shapes.begin(ShapeRenderer.ShapeType.Filled);
                shapes.setColor(0f, 0f, 0f, 0.55f);
                shapes.rect(0, 0, sw, sh);
                shapes.end();

                hudBatch.setProjectionMatrix(screenCam.combined);
                hudBatch.begin();
                font.getData().setScale(3f);
                font.setColor(0.9f, 0.15f, 0.15f, 1f);
                font.draw(hudBatch, "YOU DIED", sw / 2f - 70f, sh / 2f + 20f);
                font.getData().setScale(1.2f);
                font.setColor(0.8f, 0.8f, 0.8f, 1f);
                font.draw(hudBatch, "Waiting for respawn...", sw / 2f - 80f, sh / 2f - 15f);
                font.getData().setScale(1f);
                font.setColor(Color.WHITE);
                hudBatch.end();
            }
        }
    }

    /**
     * Queue an ability-unlock toast.  Called from GameScreen when a new ability
     * appears on the local player's state.
     */
    public void notifyAbilityUnlock(String abilityName) {
        String display = switch (abilityName) {
            case "double_jump" -> "Double Jump";
            case "dash"        -> "Dash";
            case "wall_jump"   -> "Wall Jump";
            case "shuriken"    -> "Shuriken Throw";
            case "teleport"    -> "Teleport";
            case "ninjutsu"    -> "Ninjutsu";
            default            -> abilityName.replace('_', ' ');
        };
        toastTexts.add("ABILITY UNLOCKED: " + display.toUpperCase());
        toastTtls .add(TOAST_TTL);
    }

    /**
     * Tick and render all active toasts.
     * Must be called inside a hudBatch.begin() / end() block on the screen projection.
     */
    public void renderToasts(float delta) {
        if (toastTexts.isEmpty()) return;

        int sw = Gdx.graphics.getWidth();
        int sh = Gdx.graphics.getHeight();

        hudBatch.setProjectionMatrix(screenCam.combined);
        hudBatch.begin();

        for (int i = toastTtls.size() - 1; i >= 0; i--) {
            float ttl = toastTtls.get(i) - delta;
            if (ttl <= 0f) { toastTexts.remove(i); toastTtls.remove(i); continue; }
            toastTtls.set(i, ttl);

            float alpha = ttl < TOAST_FADE ? ttl / TOAST_FADE : 1f;
            font.getData().setScale(1.4f);
            font.setColor(0.3f, 1f, 0.5f, alpha);
            String text = toastTexts.get(i);
            // Approximate centre — default font is about 8px per char at scale 1
            float textW = text.length() * 8.4f * 1.4f;
            float y = sh * 0.65f - i * 22f;
            font.draw(hudBatch, text, (sw - textW) * 0.5f, y);
        }

        font.getData().setScale(1f);
        font.setColor(Color.WHITE);
        hudBatch.end();
    }

    public void resize(int w, int h) {
        screenCam.setToOrtho(false, w, h);
        screenCam.update();
    }

    /** Screen-space projection matrix — use for overlays rendered over the HUD. */
    public com.badlogic.gdx.math.Matrix4 screenProjection() {
        return screenCam.combined;
    }

    /**
     * Expose the HUD ShapeRenderer so other renderers (e.g. ChunkRenderer vignette)
     * can reuse it without allocating a second one.
     * Caller must ensure it is used outside any active begin/end block.
     */
    public ShapeRenderer shapeRenderer() {
        shapes.setProjectionMatrix(screenCam.combined);
        return shapes;
    }

    /**
     * Render the full-screen death / respawn overlay.
     *
     * Shows a dark-red vignette, a large "YOU DIED" heading, and a countdown
     * to respawn.  Call this after all world and HUD passes but before the
     * pause screen (so pause still renders on top).
     *
     * @param respawnTimer seconds remaining; ≤ 0 means just respawned (overlay hidden)
     */
    public void renderDeathOverlay(float respawnTimer) {
        int sw = Gdx.graphics.getWidth();
        int sh = Gdx.graphics.getHeight();
        screenCam.setToOrtho(false, sw, sh);
        screenCam.update();

        // Semi-transparent dark-red background
        Gdx.gl.glEnable(com.badlogic.gdx.graphics.GL20.GL_BLEND);
        Gdx.gl.glBlendFunc(com.badlogic.gdx.graphics.GL20.GL_SRC_ALPHA,
                           com.badlogic.gdx.graphics.GL20.GL_ONE_MINUS_SRC_ALPHA);
        shapes.setProjectionMatrix(screenCam.combined);
        shapes.begin(ShapeRenderer.ShapeType.Filled);
        shapes.setColor(0.25f, 0f, 0f, 0.72f);
        shapes.rect(0, 0, sw, sh);
        shapes.end();

        // Text pass
        hudBatch.setProjectionMatrix(screenCam.combined);
        hudBatch.begin();

        float cx = sw * 0.5f;
        float cy = sh * 0.5f;

        // "YOU DIED" — large centred
        font.getData().setScale(2.8f);
        font.setColor(1f, 0.12f, 0.12f, 1f);
        com.badlogic.gdx.graphics.g2d.GlyphLayout layout =
            new com.badlogic.gdx.graphics.g2d.GlyphLayout(font, "YOU DIED");
        font.draw(hudBatch, layout, cx - layout.width * 0.5f, cy + 30f);

        // Countdown
        if (respawnTimer > 0f) {
            font.getData().setScale(1.1f);
            font.setColor(1f, 0.72f, 0.72f, 1f);
            String msg = String.format("Respawning in %.1f...", respawnTimer);
            com.badlogic.gdx.graphics.g2d.GlyphLayout sub =
                new com.badlogic.gdx.graphics.g2d.GlyphLayout(font, msg);
            font.draw(hudBatch, sub, cx - sub.width * 0.5f, cy - 20f);
        }

        font.getData().setScale(1f);
        font.setColor(Color.WHITE);
        hudBatch.end();
    }

    public void dispose() {
        shapes.dispose();
        hudBatch.dispose();
        font.dispose();
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static Color healthColor(float ratio) {
        if (ratio > 0.6f) return Color.GREEN;
        if (ratio > 0.3f) return Color.YELLOW;
        return Color.RED;
    }
}
