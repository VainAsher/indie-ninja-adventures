package com.indieniinja.procgen.rules;

import com.indieniinja.procgen.intent.RoomIntent;
import com.indieniinja.procgen.model.FillVariant;
import com.indieniinja.procgen.model.ZoneBase;
import com.indieniinja.procgen.model.ZoneCell;
import com.indieniinja.procgen.model.ZoneSurface;

/**
 * Legal when: zone is ENCLOSED, not near a door, not on the critical path,
 * and has at least two solid neighbours.
 */
public final class HollowBoxRule implements FillVariantRule {

    @Override
    public boolean valid(ZoneCell[][] zones, int x, int y, RoomIntent intent) {
        ZoneCell cell = zones[x][y];
        if (cell.base != ZoneBase.SOLID_FILL)       return false;
        if (cell.surface != ZoneSurface.ENCLOSED)   return false;
        if (cell.criticalPath)                       return false;
        if (RuleHelper.nearDoor(zones, x, y))        return false;
        return true;
    }

    @Override
    public FillVariant variant() { return FillVariant.HOLLOW_BOX_8X8; }

    @Override
    public int weight(RoomIntent intent) { return 3; }
}
