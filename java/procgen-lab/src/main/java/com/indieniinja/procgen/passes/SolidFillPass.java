package com.indieniinja.procgen.passes;

import com.indieniinja.procgen.model.FillVariant;
import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.model.ZoneBase;
import com.indieniinja.procgen.model.ZoneCell;
import com.indieniinja.procgen.model.ZoneSurface;

public final class SolidFillPass {

    /** Returns a fresh ZONE_W × ZONE_H grid with every cell set to SOLID_FILL. */
    public ZoneCell[][] apply() {
        ZoneCell[][] zones = new ZoneCell[GenConfig.ZONE_W][GenConfig.ZONE_H];
        for (int x = 0; x < GenConfig.ZONE_W; x++) {
            for (int y = 0; y < GenConfig.ZONE_H; y++) {
                ZoneCell cell = new ZoneCell();
                cell.base    = ZoneBase.SOLID_FILL;
                cell.surface = ZoneSurface.NONE;
                cell.variant = FillVariant.SOLID_8X8;
                zones[x][y] = cell;
            }
        }
        return zones;
    }
}
