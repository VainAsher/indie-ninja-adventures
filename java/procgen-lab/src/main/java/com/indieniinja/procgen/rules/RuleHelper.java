package com.indieniinja.procgen.rules;

import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.model.ZoneBase;
import com.indieniinja.procgen.model.ZoneCell;

/** Shared guard checks used by multiple rules. */
final class RuleHelper {

    static boolean isDoor(ZoneCell[][] zones, int x, int y) {
        int W = GenConfig.ZONE_W, H = GenConfig.ZONE_H;
        if (x < 0 || x >= W || y < 0 || y >= H) return false;
        return zones[x][y].base == ZoneBase.DOOR;
    }

    /** True if zone (x,y) or any of its 4-neighbours is a DOOR zone. */
    static boolean nearDoor(ZoneCell[][] zones, int x, int y) {
        return isDoor(zones, x, y)
            || isDoor(zones, x - 1, y)
            || isDoor(zones, x + 1, y)
            || isDoor(zones, x, y - 1)
            || isDoor(zones, x, y + 1);
    }

    private RuleHelper() {}
}
