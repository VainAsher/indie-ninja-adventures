package com.indieniinja.procgen.passes;

import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.model.ZoneBase;
import com.indieniinja.procgen.model.ZoneCell;
import com.indieniinja.procgen.model.ZoneSurface;

/**
 * Pass 4 — Classifies every solid zone by its structural surface role.
 *
 * Rules (checked in priority order):
 *   solid with air above    → FLOOR    (player can stand on top)
 *   solid with air below    → CEILING  (player can hang or jump under)
 *   solid with air to right → LEFT_WALL
 *   solid with air to left  → RIGHT_WALL
 *   solid fully enclosed    → ENCLOSED
 *
 * Air and DOOR zones receive NONE.
 */
public final class SurfaceClassificationPass {

    private static final int W = GenConfig.ZONE_W;
    private static final int H = GenConfig.ZONE_H;

    public void apply(ZoneCell[][] zones) {
        for (int x = 0; x < W; x++) {
            for (int y = 0; y < H; y++) {
                zones[x][y].surface = classify(zones, x, y);
            }
        }
    }

    private static ZoneSurface classify(ZoneCell[][] zones, int x, int y) {
        if (zones[x][y].base != ZoneBase.SOLID_FILL) return ZoneSurface.NONE;

        boolean airAbove = isOpen(zones, x, y - 1);
        boolean airBelow = isOpen(zones, x, y + 1);
        boolean airRight = isOpen(zones, x + 1, y);
        boolean airLeft  = isOpen(zones, x - 1, y);

        int openCount = (airAbove ? 1 : 0) + (airBelow ? 1 : 0)
                      + (airRight ? 1 : 0) + (airLeft  ? 1 : 0);

        if (openCount == 0) return ZoneSurface.ENCLOSED;

        // Priority: floor > ceiling > walls
        if (airAbove)  return ZoneSurface.FLOOR;
        if (airBelow)  return ZoneSurface.CEILING;
        if (airRight)  return ZoneSurface.LEFT_WALL;
        if (airLeft)   return ZoneSurface.RIGHT_WALL;

        return ZoneSurface.NONE;
    }

    /** Returns true when the neighbour is out-of-bounds, AIR, or DOOR. */
    private static boolean isOpen(ZoneCell[][] zones, int x, int y) {
        if (x < 0 || x >= W || y < 0 || y >= H) return true;
        ZoneBase b = zones[x][y].base;
        return b == ZoneBase.AIR || b == ZoneBase.DOOR;
    }
}
