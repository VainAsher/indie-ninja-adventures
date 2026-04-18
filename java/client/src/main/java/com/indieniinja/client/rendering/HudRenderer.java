package com.indieniinja.client.rendering;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.OrthographicCamera;
import com.badlogic.gdx.graphics.g2d.BitmapFont;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.indieniinja.client.KeyBindings;
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
    // ── Yin/Yang stance circle — right of lantern bar ────────────────────────
    private static final float YY_CX = LAN_X + LAN_W + 30f;  // 120
    private static final float YY_CY = LAN_Y + 10f;           // 100
    private static final float YY_R  = 20f;

    private final ShapeRenderer shapes;
    private final SpriteBatch   hudBatch;
    private final BitmapFont    font;

    private final OrthographicCamera screenCam;

    // ── Ability unlock toasts ─────────────────────────────────────────────────
    private static final float TOAST_TTL  = 3.0f;
    private static final float TOAST_FADE = 0.8f;   // start fading in final 0.8s
    private static final Color TRACKER_LOCKED_COLOR   = new Color(1f, 0.78f, 0.30f, 1f);
    private static final Color TRACKER_UNLOCKED_COLOR = new Color(0.45f, 1f, 0.45f, 1f);
    private static final Color TRACKER_META_COLOR     = new Color(0.80f, 0.86f, 0.94f, 0.95f);
    private static final Color TRACKER_DONE_COLOR     = new Color(0.55f, 1f, 0.55f, 0.95f);
    private final java.util.List<String> toastTexts = new java.util.ArrayList<>();
    private final java.util.List<Float>  toastTtls  = new java.util.ArrayList<>();
    // Active mission tracker (fed by GameScreen each frame).
    private String missionTrackerTitle = "";
    private final java.util.List<String> missionTrackerLines = new java.util.ArrayList<>();
    private boolean missionTrackerExitLocked = false;
    private float missionTrackerTimerSec = 0f;
    // Scripted-loss splash continue button bounds (screen-space, y-up).
    private float scriptedLossBtnX = 0f;
    private float scriptedLossBtnY = 0f;
    private float scriptedLossBtnW = 0f;
    private float scriptedLossBtnH = 0f;

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

        // ── YY stance circle — filled pass (local player only) ───────────────
        if (snap != null) {
            for (PlayerState p : snap.players) {
                if (p.slot != localSlot) continue;
                float delta = Math.max(-1f, Math.min(1f, p.yinValue - p.yangValue));
                float t = (delta + 1f) * 0.5f;  // 0=full yang, 1=full yin
                float cr = 0.38f + t * 0.62f;
                float cg = 0.58f + t * 0.38f;
                float cb = 0.92f - t * 0.10f;
                if (p.flowMode) {
                    shapes.setColor(0.88f, 1f, 0.65f, 0.30f);
                    shapes.circle(YY_CX, YY_CY, YY_R + 6f, 24);
                    shapes.setColor(0.88f, 1f, 0.65f, 0.14f);
                    shapes.circle(YY_CX, YY_CY, YY_R + 11f, 24);
                }
                shapes.setColor(cr * 0.40f, cg * 0.40f, cb * 0.40f, 0.85f);
                shapes.circle(YY_CX, YY_CY, YY_R, 24);
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

        // Mission tracker panel background (text rendered in SpriteBatch pass).
        if (!missionTrackerTitle.isBlank()) {
            float panelW = Math.min(390f, sw * 0.42f);
            float panelH = Math.min(200f, 46f + missionTrackerLines.size() * 17f);
            float panelX = sw - panelW - 12f;
            float panelY = sh - panelH - 70f;
            shapes.setColor(0f, 0f, 0f, 0.52f);
            shapes.rect(panelX, panelY, panelW, panelH);
            shapes.setColor(missionTrackerExitLocked ? 0.95f : 0.35f,
                missionTrackerExitLocked ? 0.50f : 0.95f,
                0.20f, 0.86f);
            shapes.rect(panelX, panelY + panelH - 3f, panelW, 3f);
        }

        shapes.end();

        // ── YY stance circle outline + needle ────────────────────────────────
        if (snap != null) {
            shapes.begin(ShapeRenderer.ShapeType.Line);
            for (PlayerState p : snap.players) {
                if (p.slot != localSlot) continue;
                float delta = Math.max(-1f, Math.min(1f, p.yinValue - p.yangValue));
                float t = (delta + 1f) * 0.5f;
                float cr = 0.38f + t * 0.62f;
                float cg = 0.58f + t * 0.38f;
                float cb = 0.92f - t * 0.10f;
                if (p.flowMode) {
                    shapes.setColor(0.88f, 1f, 0.65f, 0.85f);
                    shapes.circle(YY_CX, YY_CY, YY_R, 24);
                }
                shapes.setColor(cr, cg, cb, 1f);
                shapes.circle(YY_CX, YY_CY, YY_R, 24);
                // Needle: balanced=up (90°), yin tilts left, yang tilts right
                float angleRad = (float)(Math.PI * 0.5 + delta * Math.PI * 75.0 / 180.0);
                float nx = YY_CX + (float)Math.cos(angleRad) * YY_R * 0.80f;
                float ny = YY_CY + (float)Math.sin(angleRad) * YY_R * 0.80f;
                shapes.setColor(1f, 1f, 1f, 0.95f);
                shapes.line(YY_CX, YY_CY, nx, ny);
                shapes.circle(YY_CX, YY_CY, 2.5f, 8);
                break;
            }
            shapes.end();
        }

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
                font.setColor(0.70f, 0.86f, 1f, 0.95f);
                font.draw(hudBatch, weaponLabel(p), YY_CX + YY_R + 6f, YY_CY + 5f);
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

        if (!missionTrackerTitle.isBlank()) {
            float panelW = Math.min(390f, sw * 0.42f);
            float panelH = Math.min(200f, 46f + missionTrackerLines.size() * 17f);
            float panelX = sw - panelW - 12f;
            float panelY = sh - panelH - 70f;

            font.getData().setScale(0.86f);
            font.setColor(0.90f, 0.95f, 1f, 1f);
            font.draw(hudBatch, "MISSION: " + missionTrackerTitle, panelX + 10f, panelY + panelH - 10f);
            font.setColor(missionTrackerExitLocked ? TRACKER_LOCKED_COLOR : TRACKER_UNLOCKED_COLOR);
            font.draw(hudBatch,
                missionTrackerExitLocked ? "Exit Locked" : "Exit Unlocked",
                panelX + panelW - 100f, panelY + panelH - 10f);

            font.setColor(TRACKER_META_COLOR);
            font.draw(hudBatch, "Time " + formatClock(missionTrackerTimerSec), panelX + 10f, panelY + panelH - 27f);
            float y = panelY + panelH - 45f;
            for (String line : missionTrackerLines) {
                if (line == null || line.isBlank()) continue;
                font.setColor(line.startsWith("[x]") ? TRACKER_DONE_COLOR : Color.WHITE);
                font.draw(hudBatch, line, panelX + 10f, y);
                y -= 16f;
                if (y < panelY + 10f) break;
            }
            font.getData().setScale(1f);
            font.setColor(Color.WHITE);
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
                    font.draw(hudBatch, "[E]interact [O]missions [TAB]map [I]inventory", 10f, 60f);
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
        notifyToast("ABILITY UNLOCKED: " + display.toUpperCase());
    }

    /** Queue a generic toast line for onboarding/system guidance. */
    public void notifyToast(String text) {
        if (text == null || text.isBlank()) return;
        toastTexts.add(text);
        toastTtls.add(TOAST_TTL);
    }

    /** Update active mission tracker data (empty title hides the panel). */
    public void setMissionTracker(String title, java.util.List<String> lines,
                                  boolean exitLocked, float timerSec) {
        missionTrackerTitle = title == null ? "" : title;
        missionTrackerLines.clear();
        if (lines != null) missionTrackerLines.addAll(lines);
        missionTrackerExitLocked = exitLocked;
        missionTrackerTimerSec = Math.max(0f, timerSec);
    }

    public void clearMissionTracker() {
        missionTrackerTitle = "";
        missionTrackerLines.clear();
        missionTrackerExitLocked = false;
        missionTrackerTimerSec = 0f;
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

    private static String formatClock(float seconds) {
        int total = Math.max(0, (int) seconds);
        int mins = total / 60;
        int secs = total % 60;
        return String.format(java.util.Locale.ROOT, "%02d:%02d", mins, secs);
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

    public void renderScriptedLossOverlay() {
        int sw = Gdx.graphics.getWidth();
        int sh = Gdx.graphics.getHeight();
        screenCam.setToOrtho(false, sw, sh);
        screenCam.update();

        float panelW = Math.min(sw * 0.72f, 760f);
        float panelH = Math.min(sh * 0.58f, 420f);
        float panelX = (sw - panelW) * 0.5f;
        float panelY = (sh - panelH) * 0.5f;
        scriptedLossBtnW = 210f;
        scriptedLossBtnH = 46f;
        scriptedLossBtnX = panelX + (panelW - scriptedLossBtnW) * 0.5f;
        scriptedLossBtnY = panelY + 30f;

        Gdx.gl.glEnable(com.badlogic.gdx.graphics.GL20.GL_BLEND);
        Gdx.gl.glBlendFunc(com.badlogic.gdx.graphics.GL20.GL_SRC_ALPHA,
            com.badlogic.gdx.graphics.GL20.GL_ONE_MINUS_SRC_ALPHA);
        shapes.setProjectionMatrix(screenCam.combined);
        shapes.begin(ShapeRenderer.ShapeType.Filled);
        shapes.setColor(0f, 0f, 0f, 0.70f);
        shapes.rect(0f, 0f, sw, sh);
        shapes.setColor(0.10f, 0.08f, 0.16f, 0.92f);
        shapes.rect(panelX, panelY, panelW, panelH);
        shapes.setColor(0.95f, 0.85f, 0.25f, 0.95f);
        shapes.rect(panelX, panelY + panelH - 6f, panelW, 6f);
        shapes.setColor(0.16f, 0.22f, 0.34f, 1f);
        shapes.rect(scriptedLossBtnX, scriptedLossBtnY, scriptedLossBtnW, scriptedLossBtnH);
        shapes.end();

        hudBatch.setProjectionMatrix(screenCam.combined);
        hudBatch.begin();
        float cx = sw * 0.5f;
        font.getData().setScale(1.9f);
        font.setColor(0.98f, 0.91f, 0.30f, 1f);
        com.badlogic.gdx.graphics.g2d.GlyphLayout title =
            new com.badlogic.gdx.graphics.g2d.GlyphLayout(font, "FRACTURED BALANCE");
        font.draw(hudBatch, title, cx - title.width * 0.5f, panelY + panelH - 34f);

        font.getData().setScale(1f);
        font.setColor(0.90f, 0.90f, 0.95f, 1f);
        String[] lines = {
            "The Siren's assault tears your Yin and Yang apart.",
            "Your stance collapses and the room fades into silence.",
            "You awaken at the edge of the ascent, forced to rebuild."
        };
        float textY = panelY + panelH - 92f;
        for (String line : lines) {
            com.badlogic.gdx.graphics.g2d.GlyphLayout gl =
                new com.badlogic.gdx.graphics.g2d.GlyphLayout(font, line);
            font.draw(hudBatch, gl, cx - gl.width * 0.5f, textY);
            textY -= 32f;
        }

        font.getData().setScale(1.1f);
        font.setColor(0.96f, 0.97f, 1f, 1f);
        com.badlogic.gdx.graphics.g2d.GlyphLayout cta =
            new com.badlogic.gdx.graphics.g2d.GlyphLayout(font, "CONTINUE");
        font.draw(hudBatch, cta,
            scriptedLossBtnX + (scriptedLossBtnW - cta.width) * 0.5f,
            scriptedLossBtnY + scriptedLossBtnH * 0.64f);
        font.getData().setScale(1f);
        font.setColor(Color.WHITE);
        hudBatch.end();
    }

    public boolean scriptedLossButtonHit(int screenX, int screenY) {
        int sh = Gdx.graphics.getHeight();
        float yUp = sh - screenY;
        return screenX >= scriptedLossBtnX
            && screenX <= scriptedLossBtnX + scriptedLossBtnW
            && yUp >= scriptedLossBtnY
            && yUp <= scriptedLossBtnY + scriptedLossBtnH;
    }

    /**
     * Render a launcher-friendly controls reference panel.
     * Intended for first-time users with no external documentation.
     */
    public void renderControlsOverlay(KeyBindings keys) {
        int sw = Gdx.graphics.getWidth();
        int sh = Gdx.graphics.getHeight();
        screenCam.setToOrtho(false, sw, sh);
        screenCam.update();

        float panelW = Math.min(sw * 0.78f, 900f);
        float panelH = Math.min(sh * 0.72f, 560f);
        float panelX = (sw - panelW) * 0.5f;
        float panelY = (sh - panelH) * 0.5f;

        Gdx.gl.glEnable(com.badlogic.gdx.graphics.GL20.GL_BLEND);
        Gdx.gl.glBlendFunc(com.badlogic.gdx.graphics.GL20.GL_SRC_ALPHA,
            com.badlogic.gdx.graphics.GL20.GL_ONE_MINUS_SRC_ALPHA);
        shapes.setProjectionMatrix(screenCam.combined);
        shapes.begin(ShapeRenderer.ShapeType.Filled);
        shapes.setColor(0f, 0f, 0f, 0.62f);
        shapes.rect(0f, 0f, sw, sh);
        shapes.setColor(0.08f, 0.12f, 0.18f, 0.94f);
        shapes.rect(panelX, panelY, panelW, panelH);
        shapes.setColor(0.28f, 0.78f, 0.98f, 0.95f);
        shapes.rect(panelX, panelY + panelH - 5f, panelW, 5f);
        shapes.end();

        hudBatch.setProjectionMatrix(screenCam.combined);
        hudBatch.begin();

        font.getData().setScale(1.5f);
        font.setColor(0.90f, 0.96f, 1f, 1f);
        font.draw(hudBatch, "CONTROLS (F1 TO CLOSE)", panelX + 22f, panelY + panelH - 20f);

        font.getData().setScale(1f);
        font.setColor(0.88f, 0.92f, 0.98f, 1f);
        String[] lines = {
            "Movement: " + bind(keys, "left") + "/" + bind(keys, "right")
                + "  Jump: " + bind(keys, "jump")
                + "  Dash: " + bind(keys, "dash")
                + "  Run: " + bind(keys, "slow_walk"),
            "Core Actions: " + bind(keys, "attack") + " Melee  |  "
                + bind(keys, "stance_switch") + " Switch Yin/Yang  |  "
                + bind(keys, "block") + " Guard/Parry  |  "
                + bind(keys, "teleport") + " Traversal Art",
            "Posture Select: " + bind(keys, "select_weapon_1") + " Unarmed  |  "
                + bind(keys, "select_weapon_2") + " Armed (Yang preference)",
            "Arts & Utility: " + bind(keys, "throw") + " Thrown Tool  |  "
                + bind(keys, "ninjutsu") + " Echo Art  |  "
                + bind(keys, "interact") + " Interact",
            "Mission: " + bind(keys, "mission_menu")
                + " opens mission board  |  Top-right tracker shows active objectives",
            "Map: " + bind(keys, "minimap") + " tap = quick map  |  "
                + bind(keys, "fullmap") + " hold = full map  |  "
                + bind(keys, "menu_back") + " = pause/menu",
            "Debug/Dev: " + bind(keys, "toggle_hitboxes") + " hitboxes  |  "
                + bind(keys, "controls_overlay") + " controls  |  "
                + bind(keys, "debug_overlay") + " telemetry",
            "",
            "Launcher Tips:",
            "- Start Server + Play for localhost multiplayer in one click.",
            "- Logs are written to user_data/logs/client.log and user_data/logs/server.log.",
            "- Include log snippets and screenshot when reporting bugs."
        };
        float y = panelY + panelH - 56f;
        for (String line : lines) {
            font.draw(hudBatch, line, panelX + 22f, y);
            y -= line.isEmpty() ? 14f : 26f;
        }

        font.setColor(Color.WHITE);
        font.getData().setScale(1f);
        hudBatch.end();
    }

    /**
     * Render debugging telemetry panel for playtest sessions.
     */
    public void renderDebugOverlay(
        WorldSnapshot snap, int localSlot, boolean connected, String gameMode
    ) {
        int sw = Gdx.graphics.getWidth();
        int sh = Gdx.graphics.getHeight();
        screenCam.setToOrtho(false, sw, sh);
        screenCam.update();

        float panelW = Math.min(sw * 0.46f, 560f);
        float panelH = Math.min(sh * 0.72f, 520f);
        float panelX = sw - panelW - 14f;
        float panelY = sh - panelH - 14f;

        PlayerState local = null;
        if (snap != null) {
            for (PlayerState p : snap.players) {
                if (p.slot == localSlot) {
                    local = p;
                    break;
                }
            }
        }

        Gdx.gl.glEnable(com.badlogic.gdx.graphics.GL20.GL_BLEND);
        Gdx.gl.glBlendFunc(com.badlogic.gdx.graphics.GL20.GL_SRC_ALPHA,
            com.badlogic.gdx.graphics.GL20.GL_ONE_MINUS_SRC_ALPHA);
        shapes.setProjectionMatrix(screenCam.combined);
        shapes.begin(ShapeRenderer.ShapeType.Filled);
        shapes.setColor(0f, 0f, 0f, 0.55f);
        shapes.rect(panelX, panelY, panelW, panelH);
        shapes.setColor(0.80f, 0.35f, 0.95f, 0.90f);
        shapes.rect(panelX, panelY + panelH - 4f, panelW, 4f);
        shapes.end();

        hudBatch.setProjectionMatrix(screenCam.combined);
        hudBatch.begin();
        font.getData().setScale(1f);
        font.setColor(0.95f, 0.92f, 0.98f, 1f);

        float y = panelY + panelH - 14f;
        font.draw(hudBatch, "DEBUG OVERLAY (F3 TO CLOSE)", panelX + 12f, y);
        y -= 24f;

        float balanceDelta = local != null ? Math.abs(local.yinValue - local.yangValue) : -1f;
        String[] lines = {
            "net.connected: " + connected,
            "mode: " + (gameMode == null ? "?" : gameMode),
            "fps: " + Gdx.graphics.getFramesPerSecond(),
            "snapshot.frame: " + (snap != null ? snap.frame : -1),
            "snapshot.hub: " + (snap != null ? snap.hubId : "?"),
            "snapshot.room: " + (snap != null ? (snap.roomGridX + "," + snap.roomGridY) : "?"),
            "snapshot.seed: " + (snap != null ? snap.seed : 0L),
            "local.slot: " + localSlot,
            "local.player_id: " + (local != null ? local.playerId : "?"),
            "local.pos: " + (local != null ? ((int) local.posX + "," + (int) local.posY) : "?"),
            "local.vel: " + (local != null ? ((int) local.velX + "," + (int) local.velY) : "?"),
            "local.hp: " + (local != null ? local.health : -1),
            "local.stamina: " + (local != null ? local.stamina : -1),
            "local.mana: " + (local != null ? local.mana : -1),
            "local.flow: " + (local != null && local.flowMode),
            "local.stance: " + (local != null ? stanceLabel(local) : "?"),
            "local.yin: " + (local != null ? String.format(java.util.Locale.ROOT, "%.2f", local.yinValue) : "?"),
            "local.yang: " + (local != null ? String.format(java.util.Locale.ROOT, "%.2f", local.yangValue) : "?"),
            "local.balance_delta: " + (local != null ? String.format(java.util.Locale.ROOT, "%.2f", balanceDelta) : "?")
        };
        for (String line : lines) {
            font.draw(hudBatch, line, panelX + 12f, y);
            y -= 21f;
        }

        font.setColor(Color.WHITE);
        hudBatch.end();
    }

    public void dispose() {
        shapes.dispose();
        hudBatch.dispose();
        font.dispose();
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static String bind(KeyBindings keys, String action) {
        if (keys == null) return "UNBOUND";
        String value = keys.describe(action);
        return (value == null || value.isBlank()) ? "UNBOUND" : value;
    }

    private static Color healthColor(float ratio) {
        if (ratio > 0.6f) return Color.GREEN;
        if (ratio > 0.3f) return Color.YELLOW;
        return Color.RED;
    }

    private static String stanceLabel(PlayerState p) {
        if (p == null) return "UNKNOWN";
        String mode = p.stanceMode == null ? "" : p.stanceMode.trim().toLowerCase(java.util.Locale.ROOT);
        if ("yin".equals(mode)) return p.flowMode ? "YIN-FLOW" : "YIN";
        if ("yang".equals(mode)) return p.flowMode ? "YANG-FLOW" : "YANG";
        if (p.flowMode) return "FLOW";
        float delta = p.yinValue - p.yangValue;
        if (Math.abs(delta) <= 0.03f) return "BALANCED";
        return delta > 0f ? "YIN" : "YANG";
    }

    private static String weaponLabel(PlayerState p) {
        if (p == null || p.weaponState == null) return "UNARMED";
        String mode = p.weaponState.trim().toLowerCase(java.util.Locale.ROOT);
        return switch (mode) {
            case "sword" -> "ARMED(SWORD)";
            case "pistol" -> "ARMED(PISTOL)";
            default -> "UNARMED";
        };
    }
}
