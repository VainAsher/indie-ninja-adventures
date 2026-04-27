package com.indieniinja.client.rendering;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * S3 — Verifies the parallax scroll offset formula.
 * The formula applied in ParallaxRenderer.render():
 *   offsetX = -(camX * scrollX) % screenW
 *
 * Tests run without a Gdx runtime — only the arithmetic is exercised.
 */
class ParallaxLayerScrollTest {

    private static float scrollOffset(float camX, float scrollFactor, float screenW) {
        return -(camX * scrollFactor) % screenW;
    }

    @Test
    void atCameraOriginOffsetIsZero() {
        assertEquals(0f, scrollOffset(0f, 0.10f, 800f), 0.001f);
        assertEquals(0f, scrollOffset(0f, 0.25f, 800f), 0.001f);
        assertEquals(0f, scrollOffset(0f, 0.50f, 800f), 0.001f);
    }

    @Test
    void farLayerScrollsSlowerThanNearLayer() {
        float camX   = 400f;
        float screenW = 800f;
        float far  = Math.abs(scrollOffset(camX, 0.10f, screenW));
        float near = Math.abs(scrollOffset(camX, 0.50f, screenW));
        assertTrue(far < near,
            "far layer (" + far + ") should move less than near layer (" + near + ")");
    }

    @Test
    void scrollOffsetIsProportionalToScrollFactor() {
        float camX    = 200f;
        float screenW = 800f;
        float s1 = Math.abs(scrollOffset(camX, 0.10f, screenW));
        float s2 = Math.abs(scrollOffset(camX, 0.20f, screenW));
        assertEquals(s1 * 2f, s2, 0.01f,
            "doubling the scroll factor should double the offset (before wrap)");
    }

    @Test
    void offsetWrapsWithinScreenWidth() {
        float screenW = 800f;
        // Very large camera position — offset must stay in (-screenW, 0]
        for (float camX : new float[]{ 800f, 1600f, 10000f, 99999f }) {
            float off = scrollOffset(camX, 0.25f, screenW);
            assertTrue(Math.abs(off) < screenW,
                "offset " + off + " exceeds screenW at camX=" + camX);
        }
    }

    @Test
    void threeLayerScrollFactorsProduceDistinctOffsets() {
        float camX    = 300f;
        float screenW = 800f;
        float far  = scrollOffset(camX, 0.10f, screenW);
        float mid  = scrollOffset(camX, 0.25f, screenW);
        float near = scrollOffset(camX, 0.50f, screenW);
        assertNotEquals(far,  mid,  0.001f, "far and mid should differ");
        assertNotEquals(mid,  near, 0.001f, "mid and near should differ");
        assertNotEquals(far,  near, 0.001f, "far and near should differ");
    }
}
