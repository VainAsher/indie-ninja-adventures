package com.indieniinja.procgen.rules;

import com.indieniinja.procgen.intent.RoomIntent;
import com.indieniinja.procgen.model.FillVariant;
import com.indieniinja.procgen.model.ZoneCell;

public interface FillVariantRule {

    /** Returns true when this variant is legal for zone (x, y) given the room intent. */
    boolean valid(ZoneCell[][] zones, int x, int y, RoomIntent intent);

    FillVariant variant();

    /** Higher weight = more frequently selected. */
    int weight(RoomIntent intent);
}
