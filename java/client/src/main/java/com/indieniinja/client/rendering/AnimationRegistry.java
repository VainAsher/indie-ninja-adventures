package com.indieniinja.client.rendering;

import com.badlogic.gdx.files.FileHandle;
import com.badlogic.gdx.graphics.Pixmap;
import com.badlogic.gdx.graphics.Texture;
import com.badlogic.gdx.graphics.g2d.TextureAtlas;
import com.badlogic.gdx.graphics.g2d.TextureRegion;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Loads animation frames from either a TextureAtlas or individual spritesheet PNGs,
 * and provides O(1) frame lookup.
 *
 * Direct equivalent of Python's rendering/animation_system.py AnimationRegistry.
 *
 * Spritesheet convention: uniform horizontal frames, top-left origin.
 * Atlas convention: regions named "<entity>_<state>" with an index suffix.
 *
 * Fallback: if no assets are present, a 1×1 magenta placeholder is used so the
 * client can run during development without the full asset pack.
 */
public final class AnimationRegistry {

    /** Frames keyed by "<entity>_<state>" → TextureRegion[frameIndex] */
    private final Map<String, TextureRegion[]> frames = new HashMap<>();

    /** Textures owned by this registry (loaded from spritesheets). */
    private final List<Texture>    ownedTextures = new ArrayList<>();

    /** Cache: filename → Texture, so shared sheets (idle/dash) are loaded once. */
    private final Map<String, Texture> textureCache  = new HashMap<>();

    /** Fallback region used when an animation key is not found. */
    private TextureRegion fallback;

    // ── Atlas loading ─────────────────────────────────────────────────────────

    /**
     * Load all animations from a TextureAtlas.
     * Regions named "<entity>_<state>" are grouped by that key.
     */
    public void loadAtlas(TextureAtlas atlas) {
        Map<String, Integer> maxIndex = new HashMap<>();

        for (TextureAtlas.AtlasRegion r : atlas.getRegions()) {
            maxIndex.merge(r.name, r.index, Math::max);
        }

        for (TextureAtlas.AtlasRegion r : atlas.getRegions()) {
            String key = r.name;
            int max = maxIndex.get(key);
            TextureRegion[] arr = frames.computeIfAbsent(key, k -> new TextureRegion[max + 1]);
            if (r.index >= 0 && r.index < arr.length) arr[r.index] = r;
        }

        // Replace any nulls with the first non-null frame in each strip
        for (TextureRegion[] arr : frames.values()) {
            TextureRegion first = null;
            for (TextureRegion f : arr) { if (f != null) { first = f; break; } }
            if (first != null)
                for (int i = 0; i < arr.length; i++)
                    if (arr[i] == null) arr[i] = first;
        }
    }

    // ── Spritesheet loading ───────────────────────────────────────────────────

    /**
     * Load player animations from individual spritesheet PNGs in baseDir.
     *
     * Expected files (matches assets/sprites/player/):
     *   idle_spritesheet.png         2 frames  → player_idle, player_crouch
     *   walk_spritesheet.png         4 frames  → player_walk
     *   run_spritesheet.png          6 frames  → player_run, player_dash
     *   jumpfall_spritesheet.png     2 frames  → player_jump (f0), player_fall (f1)
     *   attack-sword_spritesheet.png 6 frames  → player_attack
     *   death_spritesheet.png        5 frames  → player_death
     *   hurt_spritesheet.png         3 frames  → player_hurt
     *
     * Any missing files are silently skipped; the placeholder is used as fallback.
     */
    public void loadSpriteSheets(FileHandle baseDir) {
        // Idle sheet doubles as crouch animation
        sliceAndRegister(baseDir, "player_idle",   "idle_spritesheet.png",         2);
        sliceAndRegister(baseDir, "player_crouch", "idle_spritesheet.png",         2);

        // Walk and run
        sliceAndRegister(baseDir, "player_walk",   "walk_spritesheet.png",         4);
        sliceAndRegister(baseDir, "player_run",    "run_spritesheet.png",          6);
        sliceAndRegister(baseDir, "player_dash",   "run_spritesheet.png",          6);

        // Jump and fall are frames 0 and 1 of the same sheet
        registerJumpFall(baseDir, "jumpfall_spritesheet.png");

        // Combat
        sliceAndRegister(baseDir, "player_attack", "attack-sword_spritesheet.png", 6);
        sliceAndRegister(baseDir, "player_death",  "death_spritesheet.png",        5);
        sliceAndRegister(baseDir, "player_hurt",   "hurt_spritesheet.png",         3);
    }

    // ── Placeholder ───────────────────────────────────────────────────────────

    /**
     * Create a 1×1 magenta placeholder.  Called automatically when a key is
     * missing, so explicit calls are only needed for pre-warming.
     */
    public void loadPlaceholder() {
        if (fallback != null) return;
        Pixmap pix = new Pixmap(1, 1, Pixmap.Format.RGBA8888);
        pix.setColor(1f, 0f, 1f, 1f);
        pix.fill();
        fallback = new TextureRegion(new Texture(pix));
        pix.dispose();
    }

    // ── Query ─────────────────────────────────────────────────────────────────

    /**
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

    /** True if the animation key has been registered. */
    public boolean has(String key) {
        return frames.containsKey(key);
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    /**
     * Load (or reuse a cached) texture from baseDir/filename, slice into numFrames
     * equal horizontal strips, and register under animKey.
     */
    private void sliceAndRegister(FileHandle baseDir, String animKey,
                                   String filename, int numFrames) {
        Texture tex = loadCached(baseDir, filename);
        if (tex == null) return;
        frames.put(animKey, sliceSheet(tex, numFrames));
    }

    /**
     * Load the jump/fall sheet (2 frames); register each frame as its own 1-frame
     * animation so the state time loops correctly.
     */
    private void registerJumpFall(FileHandle baseDir, String filename) {
        Texture tex = loadCached(baseDir, filename);
        if (tex == null) return;
        TextureRegion[] both = sliceSheet(tex, 2);
        frames.put("player_jump", new TextureRegion[]{ both[0] });
        frames.put("player_fall", new TextureRegion[]{ both[1] });
    }

    /** Slice a texture into numFrames equal-width horizontal frames. */
    private static TextureRegion[] sliceSheet(Texture tex, int numFrames) {
        int fw = tex.getWidth() / numFrames;
        int fh = tex.getHeight();
        TextureRegion[] regions = new TextureRegion[numFrames];
        for (int i = 0; i < numFrames; i++) {
            regions[i] = new TextureRegion(tex, i * fw, 0, fw, fh);
        }
        return regions;
    }

    /**
     * Load a texture from baseDir/filename, caching it so shared sheets
     * (e.g. run/dash, idle/crouch) are only loaded once.
     */
    private Texture loadCached(FileHandle baseDir, String filename) {
        if (textureCache.containsKey(filename)) {
            return textureCache.get(filename);  // may be null if file absent
        }
        FileHandle fh = baseDir.child(filename);
        Texture tex = null;
        if (fh.exists()) {
            tex = new Texture(fh);
            ownedTextures.add(tex);
        }
        textureCache.put(filename, tex);
        return tex;
    }

    private TextureRegion getFallback() {
        loadPlaceholder();
        return fallback;
    }

    // ── Dispose ───────────────────────────────────────────────────────────────

    public void dispose() {
        for (Texture t : ownedTextures) t.dispose();
        ownedTextures.clear();
        textureCache.clear();
        if (fallback != null) {
            fallback.getTexture().dispose();
            fallback = null;
        }
    }
}
