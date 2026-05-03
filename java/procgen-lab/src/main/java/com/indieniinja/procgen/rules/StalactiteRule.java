package com.indieniinja.procgen.rules;

import com.indieniinja.procgen.intent.RoomIntent;
import com.indieniinja.procgen.model.Biome;
import com.indieniinja.procgen.model.FillVariant;
import com.indieniinja.procgen.model.ZoneBase;
import com.indieniinja.procgen.model.ZoneCell;
import com.indieniinja.procgen.model.ZoneSurface;

/** Legal when: biome is CAVE and surface is CEILING. */
public final class StalactiteRule implements FillVariantRule {

    @Override
    public boolean valid(ZoneCell[][] zones, int x, int y, RoomIntent intent) {
        if (intent.biome != Biome.CAVE)                         return false;
        if (zones[x][y].base != ZoneBase.SOLID_FILL)           return false;
        if (zones[x][y].surface != ZoneSurface.CEILING)        return false;
        if (RuleHelper.nearDoor(zones, x, y))                   return false;
        return true;
    }

    @Override
    public FillVariant variant() { return FillVariant.CAVE_STALACTITE; }

    @Override
    public int weight(RoomIntent intent) { return 4; }
}
