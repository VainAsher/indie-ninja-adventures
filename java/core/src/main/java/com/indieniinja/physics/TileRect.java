package com.indieniinja.physics;

/**
 * Axis-aligned bounding box for a tile, used during collision resolution.
 * Immutable value object — shared safely across threads (read-only after world load).
 */
public record TileRect(float x, float y, float w, float h, boolean isPlatform) {

    /** Returns true if this rect overlaps the given AABB (non-inclusive edges). */
    public boolean overlaps(float ox, float oy, float ow, float oh) {
        return ox < x + w && ox + ow > x
            && oy < y + h && oy + oh > y;
    }

    /** Right edge of this tile. */
    public float right()  { return x + w; }
    /** Bottom edge of this tile. */
    public float bottom() { return y + h; }
}
