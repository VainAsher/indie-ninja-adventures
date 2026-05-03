package com.indieniinja.procgen.rules;

import com.indieniinja.procgen.intent.RoomIntent;
import com.indieniinja.procgen.model.Biome;
import com.indieniinja.procgen.model.FillVariant;
import com.indieniinja.procgen.model.ZoneBase;
import com.indieniinja.procgen.model.ZoneCell;
import com.indieniinja.procgen.model.ZoneSurface;

/** Legal when: biome is DUNGEON and surface is LEFT_WALL or RIGHT_WALL. */
public final class CrackedWallRule implements FillVariantRule {

    @Override
    public boolean valid(ZoneCell[][] zones, int x, int y, RoomIntent intent) {
        if (intent.biome != Biome.DUNGEON)              return false;
        if (zones[x][y].base != ZoneBase.SOLID_FILL)   return false;
        ZoneSurface s = zones[x][y].surface;
        if (s != ZoneSurface.LEFT_WALL && s != ZoneSurface.RIGHT_WALL) return false;
        if (RuleHelper.nearDoor(zones, x, y))            return false;
        return true;
    }

    @Override
    public FillVariant variant() { return FillVariant.DUNGEON_CRACKED_WALL; }

    @Override
    public int weight(RoomIntent intent) { return 2; }
}
