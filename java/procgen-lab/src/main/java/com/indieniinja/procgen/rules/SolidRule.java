package com.indieniinja.procgen.rules;

import com.indieniinja.procgen.intent.RoomIntent;
import com.indieniinja.procgen.model.FillVariant;
import com.indieniinja.procgen.model.ZoneBase;
import com.indieniinja.procgen.model.ZoneCell;

/** Default fallback — always valid for any SOLID_FILL zone. */
public final class SolidRule implements FillVariantRule {

    @Override
    public boolean valid(ZoneCell[][] zones, int x, int y, RoomIntent intent) {
        return zones[x][y].base == ZoneBase.SOLID_FILL;
    }

    @Override
    public FillVariant variant() { return FillVariant.SOLID_8X8; }

    @Override
    public int weight(RoomIntent intent) { return 10; }
}
