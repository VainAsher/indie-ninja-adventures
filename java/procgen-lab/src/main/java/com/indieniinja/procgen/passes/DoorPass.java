package com.indieniinja.procgen.passes;

import com.indieniinja.procgen.model.Direction;
import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.model.ZoneBase;
import com.indieniinja.procgen.model.ZoneCell;

import java.util.Set;

/**
 * Pass 3 — Places door zones on the room perimeter for each connection
 * direction and carves the required air clearance inward.
 *
 * Door centre positions (in zone coordinates):
 *   LEFT  → x=0,        y=midY
 *   RIGHT → x=W-1,      y=midY
 *   UP    → x=midX,     y=0
 *   DOWN  → x=midX,     y=H-1
 *
 * Clearance: 3 zones wide × 2 zones deep from the perimeter edge.
 */
public final class DoorPass {

    private static final int W    = GenConfig.ZONE_W;
    private static final int H    = GenConfig.ZONE_H;
    private static final int HALF = 1; // half-span around centre — door is 3 zones wide

    public void apply(ZoneCell[][] zones, Set<Direction> connections) {
        int midX = W / 2;
        int midY = H / 2;

        if (connections.contains(Direction.LEFT)) {
            placeHorizontalDoor(zones, 0, midY);
        }
        if (connections.contains(Direction.RIGHT)) {
            placeHorizontalDoor(zones, W - 1, midY);
        }
        if (connections.contains(Direction.UP)) {
            placeVerticalDoor(zones, midX, 0);
        }
        if (connections.contains(Direction.DOWN)) {
            placeVerticalDoor(zones, midX, H - 1);
        }
    }

    // -------------------------------------------------------------------------

    /** Door on left (x=0) or right (x=W-1) wall. Clears inward for depth=2. */
    private void placeHorizontalDoor(ZoneCell[][] zones, int wallX, int centreY) {
        int depth = wallX == 0 ? 1 : -1; // inward direction

        for (int dy = -HALF; dy <= HALF; dy++) {
            int y = centreY + dy;
            if (y < 0 || y >= H) continue;
            door(zones, wallX, y);
            // Air clearance two zones deep
            for (int d = 1; d <= 2; d++) {
                air(zones, wallX + depth * d, y);
            }
        }
    }

    /** Door on top (y=0) or bottom (y=H-1) wall. Clears inward for depth=2. */
    private void placeVerticalDoor(ZoneCell[][] zones, int centreX, int wallY) {
        int depth = wallY == 0 ? 1 : -1;

        for (int dx = -HALF; dx <= HALF; dx++) {
            int x = centreX + dx;
            if (x < 0 || x >= W) continue;
            door(zones, x, wallY);
            for (int d = 1; d <= 2; d++) {
                air(zones, x, wallY + depth * d);
            }
        }
    }

    private static void door(ZoneCell[][] zones, int x, int y) {
        if (x < 0 || x >= W || y < 0 || y >= H) return;
        zones[x][y].base = ZoneBase.DOOR;
    }

    private static void air(ZoneCell[][] zones, int x, int y) {
        if (x < 0 || x >= W || y < 0 || y >= H) return;
        if (zones[x][y].base == ZoneBase.DOOR) return; // preserve door zones
        zones[x][y].base = ZoneBase.AIR;
    }
}
