package com.indieniinja.client.rendering;

import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.Pixmap;
import com.badlogic.gdx.graphics.Texture;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.g2d.TextureRegion;

/**
 * Lightweight pooled 2D particle system.
 *
 * Equivalent of Python's rendering/particles.py ParticleSystem.
 *
 * All particles share a single 2×2 white pixel TextureRegion so rendering
 * stays within the active SpriteBatch — no extra draw-call overhead.
 *
 * Usage:
 *   ParticleSystem ps = new ParticleSystem();
 *
 *   // Each frame:
 *   ps.update(delta);
 *   // inside an active batch:
 *   ps.render(batch);
 *
 *   // Emit preset effects:
 *   ps.emitJumpPuff(x, y);
 *   ps.emitLandPuff(x, y);
 *   ps.emitRunDust(x, y, facing);
 *   ps.emitHitSpark(x, y);
 *   ps.emitTeleportBurst(x, y);
 */
public final class ParticleSystem {

    private static final int   MAX_PARTICLES = 512;
    private static final float GRAVITY       = 0.08f; // px/tick² — gentle downward pull

    // ── Particle data (struct-of-arrays style avoids object allocation per emit) ──
    private final float[] px   = new float[MAX_PARTICLES];
    private final float[] py   = new float[MAX_PARTICLES];
    private final float[] pvx  = new float[MAX_PARTICLES];
    private final float[] pvy  = new float[MAX_PARTICLES];
    private final float[] pr   = new float[MAX_PARTICLES];
    private final float[] pg   = new float[MAX_PARTICLES];
    private final float[] pb   = new float[MAX_PARTICLES];
    private final float[] pa   = new float[MAX_PARTICLES];
    private final float[] life = new float[MAX_PARTICLES];
    private final float[] maxL = new float[MAX_PARTICLES];
    private final float[] size = new float[MAX_PARTICLES];
    private final boolean[] alive = new boolean[MAX_PARTICLES];

    private final TextureRegion dot;
    private final java.util.Random rng = new java.util.Random();

    public ParticleSystem() {
        Pixmap px2 = new Pixmap(2, 2, Pixmap.Format.RGBA8888);
        px2.setColor(Color.WHITE);
        px2.fill();
        dot = new TextureRegion(new Texture(px2));
        px2.dispose();
    }

    // ── Core emit ─────────────────────────────────────────────────────────────

    /**
     * Emit a single particle. Silently skips if the pool is full.
     */
    public void emit(float x, float y, float vx, float vy,
                     float r, float g, float b, float a,
                     float life, float size) {
        for (int i = 0; i < MAX_PARTICLES; i++) {
            if (!alive[i]) {
                this.px[i]   = x;
                this.py[i]   = y;
                this.pvx[i]  = vx;
                this.pvy[i]  = vy;
                this.pr[i]   = r;
                this.pg[i]   = g;
                this.pb[i]   = b;
                this.pa[i]   = a;
                this.life[i] = life;
                this.maxL[i] = life;
                this.size[i] = size;
                this.alive[i] = true;
                return;
            }
        }
    }

    // ── Update ────────────────────────────────────────────────────────────────

    /** Advance all live particles by {@code dt} seconds. */
    public void update(float dt) {
        for (int i = 0; i < MAX_PARTICLES; i++) {
            if (!alive[i]) continue;
            px[i]   += pvx[i];
            py[i]   += pvy[i];
            pvy[i]  += GRAVITY;     // gravity pulls particles downward
            life[i] -= dt;
            if (life[i] <= 0f) alive[i] = false;
        }
    }

    // ── Render ────────────────────────────────────────────────────────────────

    /**
     * Draw all live particles. SpriteBatch must be active.
     * Alpha fades linearly from full → 0 over the particle's lifetime.
     */
    public void render(SpriteBatch batch) {
        for (int i = 0; i < MAX_PARTICLES; i++) {
            if (!alive[i]) continue;
            float ratio = life[i] / maxL[i];
            float sz    = size[i] * ratio;         // shrink toward death
            float alpha = pa[i]  * ratio;
            if (sz < 0.5f || alpha < 0.01f) continue;
            batch.setColor(pr[i], pg[i], pb[i], alpha);
            batch.draw(dot, px[i] - sz * 0.5f, py[i] - sz * 0.5f, sz, sz);
        }
        batch.setColor(Color.WHITE);
    }

    // ── Preset effects ────────────────────────────────────────────────────────

    /**
     * Jump puff — white/grey burst at player feet when leaving the ground.
     * 8 particles radiate outward and slightly downward.
     */
    public void emitJumpPuff(float x, float y) {
        for (int i = 0; i < 8; i++) {
            float angle = (float) Math.PI + (rng.nextFloat() - 0.5f) * (float) Math.PI;
            float speed = 1.5f + rng.nextFloat() * 3f;
            float vx    = (float) Math.cos(angle) * speed;
            float vy    = (float) Math.sin(angle) * speed - 1f;
            float shade = 0.8f + rng.nextFloat() * 0.15f;
            emit(x, y, vx, vy, shade, shade, shade + 0.05f, 0.85f,
                 0.25f + rng.nextFloat() * 0.2f, 4f + rng.nextFloat() * 4f);
        }
    }

    /**
     * Landing puff — wider horizontal burst when player touches down.
     * 10 particles shoot sideways at low height.
     */
    public void emitLandPuff(float x, float y) {
        for (int i = 0; i < 10; i++) {
            float side  = (i % 2 == 0) ? 1f : -1f;
            float vx    = side * (1f + rng.nextFloat() * 3.5f);
            float vy    = -(rng.nextFloat() * 1.5f);
            float shade = 0.75f + rng.nextFloat() * 0.2f;
            emit(x, y, vx, vy, shade, shade, shade, 0.8f,
                 0.2f + rng.nextFloat() * 0.15f, 3f + rng.nextFloat() * 3f);
        }
    }

    /**
     * Run dust — brownish puff kicked backward while sprinting.
     * 3 particles per call; call every ~0.08 s while running.
     *
     * @param facing 1=right, -1=left
     */
    public void emitRunDust(float x, float y, int facing) {
        for (int i = 0; i < 3; i++) {
            float vx = facing * -(1f + rng.nextFloat() * 2.5f);
            float vy = -(rng.nextFloat() * 0.8f);
            emit(x, y, vx, vy, 0.72f, 0.60f, 0.44f, 0.65f,
                 0.18f + rng.nextFloat() * 0.12f, 2f + rng.nextFloat() * 2.5f);
        }
    }

    /**
     * Hit spark — orange/yellow burst at the impact point when an enemy is struck.
     * 8 particles radiate in all directions.
     */
    public void emitHitSpark(float x, float y) {
        for (int i = 0; i < 8; i++) {
            float angle = rng.nextFloat() * 2f * (float) Math.PI;
            float speed = 2.5f + rng.nextFloat() * 4f;
            float vx    = (float) Math.cos(angle) * speed;
            float vy    = (float) Math.sin(angle) * speed;
            float green = 0.45f + rng.nextFloat() * 0.45f;
            emit(x, y, vx, vy, 1f, green, 0f, 1f,
                 0.2f + rng.nextFloat() * 0.15f, 3f + rng.nextFloat() * 3f);
        }
    }

    /**
     * Teleport burst — cyan flash at the warp origin/destination.
     * 12 fast-moving particles scatter outward.
     */
    public void emitTeleportBurst(float x, float y) {
        for (int i = 0; i < 12; i++) {
            float angle = (float)(i * 2 * Math.PI / 12) + rng.nextFloat() * 0.4f;
            float speed = 3f + rng.nextFloat() * 5f;
            float vx    = (float) Math.cos(angle) * speed;
            float vy    = (float) Math.sin(angle) * speed;
            emit(x, y, vx, vy, 0.3f, 0.85f, 1f, 0.9f,
                 0.3f + rng.nextFloat() * 0.2f, 4f + rng.nextFloat() * 4f);
        }
    }

    // ── Dispose ───────────────────────────────────────────────────────────────

    public void dispose() {
        dot.getTexture().dispose();
    }
}
