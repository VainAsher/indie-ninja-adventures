package com.indieniinja.client.rendering;

import com.badlogic.gdx.graphics.Pixmap;
import com.badlogic.gdx.graphics.Texture;
import com.badlogic.gdx.graphics.g2d.TextureAtlas;
import com.badlogic.gdx.graphics.g2d.TextureRegion;

import java.util.HashMap;
import java.util.Map;

/**
 * Loads animation frames from a TextureAtlas and provides O(1) frame lookup.
 * Direct equivalent of Python's rendering/animation_system.py AnimationRegistry.
 *
 * Expected atlas regions follow the naming convention:
 *   "<entity>_<state>_<index>"  e.g. "player_idle_0", "player_run_1", "enemy_ninja_chase_0"
 *
 * Fallback: if the atlas file is absent, a 1×1 coloured placeholder is used so
 * the client can run (and test network/sim code) without the full asset pack.
 */
public final class AnimationRegistry {

    /** Frames keyed by "<entity>_<state>" → TextureRegion[frameIndex] */
    private final Map<String, TextureRegion[]> frames = new HashMap<>();

    /** Fallback region used when an animation key is not found in the atlas. */
    private TextureRegion fallback;

    // ── Load ─────────────────────────────────────────────────────────────────

    /**
     * Load all animations from the given atlas.
     * Regions named "<entity>_<state>_<N>" are grouped by "<entity>_<state>".
     */
    public void loadAtlas(TextureAtlas atlas) {
        Map<String, Integer> maxIndex = new HashMap<>();

        // First pass: find max frame index per key
        for (TextureAtlas.AtlasRegion r : atlas.getRegions()) {
            // AtlasRegion.index is the numeric suffix (e.g. 0, 1, 2…)
            String key = r.name;   // e.g. "player_idle"
            maxIndex.merge(key, r.index, Math::max);
        }

        // Second pass: allocate arrays and populate
        for (TextureAtlas.AtlasRegion r : atlas.getRegions()) {
            String key = r.name;
            int max = maxIndex.get(key);
            TextureRegion[] arr = frames.computeIfAbsent(key, k -> new TextureRegion[max + 1]);
            if (r.index >= 0 && r.index < arr.length) arr[r.index] = r;
        }

        // Replace any nulls with the first non-null frame in that strip
        for (Map.Entry<String, TextureRegion[]> e : frames.entrySet()) {
            TextureRegion[] arr = e.getValue();
            TextureRegion first = null;
            for (TextureRegion f : arr) { if (f != null) { first = f; break; } }
            if (first != null)
                for (int i = 0; i < arr.length; i++)
                    if (arr[i] == null) arr[i] = first;
        }
    }

    /**
     * Create a 1×1 coloured placeholder used when no atlas is available.
     * Call this when running without assets.
     */
    public void loadPlaceholder() {
        Pixmap pix = new Pixmap(1, 1, Pixmap.Format.RGBA8888);
        pix.setColor(1f, 0f, 1f, 1f);  // magenta — clearly "missing"
        pix.fill();
        fallback = new TextureRegion(new Texture(pix));
        pix.dispose();
    }

    // ── Query ─────────────────────────────────────────────────────────────────

    /**
     * Return the correct frame for the given animation key and elapsed state time.
     *
     * @param key       "<entity>_<state>"  e.g. "player_idle"
     * @param stateTime seconds since this animation state started
     * @param fps       animation playback speed (frames per second)
     * @return          the TextureRegion to render, never null
     */
    public TextureRegion getFrame(String key, float stateTime, float fps) {
        TextureRegion[] strip = frames.get(key);
        if (strip == null || strip.length == 0) return getFallback();
        int idx = (int) (stateTime * fps) % strip.length;
        TextureRegion r = strip[idx];
        return r != null ? r : getFallback();
    }

    /** True if the animation key exists in the registry. */
    public boolean has(String key) {
        return frames.containsKey(key);
    }

    private TextureRegion getFallback() {
        if (fallback == null) loadPlaceholder();
        return fallback;
    }

    public void dispose() {
        if (fallback != null) fallback.getTexture().dispose();
    }
}
