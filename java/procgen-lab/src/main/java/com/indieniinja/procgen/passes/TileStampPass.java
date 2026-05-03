package com.indieniinja.procgen.passes;

import com.indieniinja.procgen.model.FillVariant;
import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.model.ZoneBase;
import com.indieniinja.procgen.model.ZoneCell;
import com.indieniinja.procgen.stamps.CrackedWallStamp;
import com.indieniinja.procgen.stamps.DoorStamp;
import com.indieniinja.procgen.stamps.EmptyStamp;
import com.indieniinja.procgen.stamps.HollowBoxStamp;
import com.indieniinja.procgen.stamps.PillarStamp;
import com.indieniinja.procgen.stamps.PlatformStamp;
import com.indieniinja.procgen.stamps.Stamp;
import com.indieniinja.procgen.stamps.SolidStamp;
import com.indieniinja.procgen.stamps.StalactiteStamp;
import com.indieniinja.procgen.stamps.StalagmiteStamp;

import java.util.EnumMap;
import java.util.Map;

/**
 * Pass 6 — Expands the 16×16 zone grid into the final 128×128 tilemap by
 * stamping each zone's 8×8 tile pattern into the correct tile-space position.
 *
 * Output array indexing: tiles[tileX][tileY], 0-based, origin top-left.
 */
public final class TileStampPass {

    private static final int ZS = GenConfig.ZONE_SIZE;

    private static final Map<FillVariant, Stamp> STAMP_MAP;
    private static final Stamp EMPTY  = new EmptyStamp();
    private static final Stamp DOOR_S = new DoorStamp();

    static {
        Map<FillVariant, Stamp> m = new EnumMap<>(FillVariant.class);
        m.put(FillVariant.SOLID_8X8,         new SolidStamp());
        m.put(FillVariant.HOLLOW_BOX_8X8,    new HollowBoxStamp());
        m.put(FillVariant.CAVE_STALACTITE,   new StalactiteStamp());
        m.put(FillVariant.CAVE_STALAGMITE,   new StalagmiteStamp());
        m.put(FillVariant.DUNGEON_PILLAR,    new PillarStamp());
        m.put(FillVariant.DUNGEON_CRACKED_WALL, new CrackedWallStamp());
        // Remaining variants fall back to SolidStamp
        STAMP_MAP = m;
    }

    /**
     * @param zones ZONE_W × ZONE_H zone grid from previous passes
     * @return ROOM_W × ROOM_H tilemap
     */
    public byte[][] apply(ZoneCell[][] zones) {
        byte[][] tiles = new byte[GenConfig.ROOM_W][GenConfig.ROOM_H];

        for (int zx = 0; zx < GenConfig.ZONE_W; zx++) {
            for (int zy = 0; zy < GenConfig.ZONE_H; zy++) {
                byte[][] stamp = stampFor(zones[zx][zy]).tiles();
                int originX = zx * ZS;
                int originY = zy * ZS;
                for (int sx = 0; sx < ZS; sx++) {
                    for (int sy = 0; sy < ZS; sy++) {
                        tiles[originX + sx][originY + sy] = stamp[sx][sy];
                    }
                }
            }
        }

        return tiles;
    }

    private static Stamp stampFor(ZoneCell cell) {
        if (cell.base == ZoneBase.AIR)  return EMPTY;
        if (cell.base == ZoneBase.DOOR) return DOOR_S;
        Stamp s = STAMP_MAP.get(cell.variant);
        return s != null ? s : new SolidStamp();
    }
}
