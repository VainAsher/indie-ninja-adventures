package com.indieniinja.procgen.rules;

import com.indieniinja.procgen.intent.RoomIntent;
import com.indieniinja.procgen.model.Biome;
import com.indieniinja.procgen.model.FillVariant;
import com.indieniinja.procgen.model.ZoneBase;
import com.indieniinja.procgen.model.ZoneCell;
import com.indieniinja.procgen.model.ZoneSurface;

/** Legal when: biome is CAVE and surface is FLOOR. */
public final class StalagmiteRule implements FillVariantRule {

    @Override
    public boolean valid(ZoneCell[][] zones, int x, int y, RoomIntent intent) {
        if (intent.biome != Biome.CAVE)                       return false;
        if (zones[x][y].base != ZoneBase.SOLID_FILL)         return false;
        if (zones[x][y].surface != ZoneSurface.FLOOR)        return false;
        if (RuleHelper.nearDoor(zones, x, y))                 return false;
        return true;
    }

    @Override
    public FillVariant variant() { return FillVariant.CAVE_STALAGMITE; }

    @Override
    public int weight(RoomIntent intent) { return 4; }
}
