package com.indieniinja.client.rendering;

import com.badlogic.gdx.files.FileHandle;
import com.badlogic.gdx.graphics.OrthographicCamera;
import com.badlogic.gdx.graphics.Pixmap;
import com.badlogic.gdx.graphics.Texture;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.g2d.TextureRegion;
import com.badlogic.gdx.math.Matrix4;
import com.badlogic.gdx.utils.JsonReader;
import com.badlogic.gdx.utils.JsonValue;
import com.indieniinja.client.GameCamera;

/**
 * Three-layer parallax background renderer.
 *
 * Each layer is a tiling horizontal strip drawn behind all gameplay content.
 * The strip scrolls at a fraction of the camera X position, creating depth.
 * Layer definitions are read from assets/visual/parallax.json.
 *
 * Render order (call before terrain pass):
 *   parallaxRenderer.render(batch, camera);
 *
 * Texture paths in parallax.json are relative to assets/. If a texture file
 * is absent the layer degrades gracefully to a solid colour strip derived from
 * the tint values in the JSON.
 */
public final class ParallaxRenderer {

    private static final String[] LAYER_NAMES = { "far", "mid", "near" };

    private final Layer[]             layers    = new Layer[3];
    private final OrthographicCamera  screenCam = new OrthographicCamera();
    private final Matrix4             savedProj = new Matrix4();

    // ── Internal layer state ──────────────────────────────────────────────────

    private static final class Layer {
        TextureRegion tex;
        float scrollX;
        float scrollY;
        boolean owned;  // true if we created the Texture (must dispose)

        void dispose() {
            if (owned && tex != null) {
                tex.getTexture().dispose();
            }
        }
    }

    // ── Public API ────────────────────────────────────────────────────────────

    /**
     * Load parallax layers for a biome set.
     *
     * @param parallaxSetId biome set name matching a key in parallax.json
     *                      (e.g. "earth", "forest", "dungeon")
     * @param assetRoot     FileHandle pointing to the repo assets/ directory;
     *                      texture paths in the JSON are resolved relative to it
     */
    public void loadBiome(String parallaxSetId, FileHandle assetRoot) {
        dispose();

        FileHandle jsonFh = assetRoot.child("visual/parallax.json");
        if (!jsonFh.exists()) {
            loadFallbackLayers();
            return;
        }

        JsonValue root = new JsonReader().parse(jsonFh);
        JsonValue sets = root.get("sets");
        JsonValue set  = sets != null ? sets.get(parallaxSetId) : null;
        if (set == null) {
            loadFallbackLayers();
            return;
        }

        for (int i = 0; i < LAYER_NAMES.length; i++) {
            JsonValue layerDef = set.get(LAYER_NAMES[i]);
            if (layerDef == null) {
                layers[i] = buildColourLayer(0.1f, 0.1f, 0.1f, 0.05f, 0.03f);
                continue;
            }

            float scrollX = layerDef.getFloat("scrollX", 0.25f);
            float scrollY = layerDef.getFloat("scrollY", 0.10f);
            float tintR   = layerDef.getFloat("tintR",   0.10f);
            float tintG   = layerDef.getFloat("tintG",   0.10f);
            float tintB   = layerDef.getFloat("tintB",   0.10f);

            String texPath = layerDef.getString("texturePath", null);
            FileHandle texFh = texPath != null ? assetRoot.child(texPath) : null;

            if (texFh != null && texFh.exists()) {
                Texture t = new Texture(texFh);
                t.setWrap(Texture.TextureWrap.Repeat, Texture.TextureWrap.ClampToEdge);
                Layer layer  = new Layer();
                layer.tex     = new TextureRegion(t);
                layer.scrollX = scrollX;
                layer.scrollY = scrollY;
                layer.owned   = true;
                layers[i]     = layer;
            } else {
                layers[i] = buildColourLayer(tintR, tintG, tintB, scrollX, scrollY);
            }
        }
    }

    /**
     * Draw all three parallax layers behind the world.
     *
     * Manages its own screen-space projection: saves the batch projection on
     * entry, renders layers in screen-space (0,0)–(screenW,screenH), then
     * restores the caller's projection so the terrain pass is unaffected.
     *
     * Must be called with {@code batch} NOT begun — this method wraps begin/end.
     *
     * @param batch  SpriteBatch (must not be begun)
     * @param camera current game camera for scroll offset sampling
     */
    public void render(SpriteBatch batch, GameCamera camera) {
        float screenW = camera.cam.viewportWidth;
        float screenH = camera.cam.viewportHeight;
        float camX    = camera.cam.position.x;
        float camY    = camera.cam.position.y;

        // Build a screen-space projection matching the viewport dimensions.
        screenCam.setToOrtho(false, screenW, screenH);
        screenCam.update();

        savedProj.set(batch.getProjectionMatrix());
        batch.setProjectionMatrix(screenCam.combined);
        batch.begin();

        for (Layer layer : layers) {
            if (layer == null || layer.tex == null) continue;

            float offsetX = -(camX * layer.scrollX) % screenW;
            float offsetY = -(camY * layer.scrollY) % screenH;

            int texW = layer.tex.getRegionWidth();
            int texH = layer.tex.getRegionHeight();
            if (texW <= 0 || texH <= 0) continue;

            float startX = offsetX - texW;
            int   tilesX = (int) Math.ceil((screenW + texW) / (float) texW) + 1;

            for (int t = 0; t < tilesX; t++) {
                batch.draw(layer.tex, startX + t * texW, offsetY, texW, screenH);
            }
        }

        batch.end();
        batch.setProjectionMatrix(savedProj);
    }

    public void dispose() {
        for (int i = 0; i < layers.length; i++) {
            if (layers[i] != null) {
                layers[i].dispose();
                layers[i] = null;
            }
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static Layer buildColourLayer(float r, float g, float b,
                                          float scrollX, float scrollY) {
        Pixmap px = new Pixmap(2, 2, Pixmap.Format.RGB888);
        px.setColor(r, g, b, 1f);
        px.fill();
        Texture t = new Texture(px);
        px.dispose();
        t.setWrap(Texture.TextureWrap.Repeat, Texture.TextureWrap.ClampToEdge);
        Layer layer    = new Layer();
        layer.tex      = new TextureRegion(t);
        layer.scrollX  = scrollX;
        layer.scrollY  = scrollY;
        layer.owned    = true;
        return layer;
    }

    private void loadFallbackLayers() {
        float[] scrollFactors = { 0.10f, 0.25f, 0.50f };
        float[] brightness    = { 0.06f, 0.09f, 0.12f };
        for (int i = 0; i < LAYER_NAMES.length; i++) {
            float v = brightness[i];
            layers[i] = buildColourLayer(v, v, v, scrollFactors[i], scrollFactors[i] * 0.4f);
        }
    }
}
