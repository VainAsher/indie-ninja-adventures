package com.indieniinja.procgen.room;

import com.indieniinja.procgen.intent.RoomIntent;
import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.model.ZoneCell;

public final class GeneratedRoom {
    public final RoomIntent          intent;
    public final ZoneCell[][]        zones;  // [zoneX][zoneY], dimensions ZONE_W × ZONE_H
    public final byte[][]            tiles;  // [tileX][tileY], dimensions ROOM_W × ROOM_H
    public final RoomGenerationReport report;

    public GeneratedRoom(RoomIntent intent, ZoneCell[][] zones, byte[][] tiles,
                         RoomGenerationReport report) {
        this.intent = intent;
        this.zones  = zones;
        this.tiles  = tiles;
        this.report = report;
    }

    public boolean isValid() {
        return !report.hasErrors();
    }

    /** Zone grid width in cells. */
    public int zoneW() { return GenConfig.ZONE_W; }

    /** Zone grid height in cells. */
    public int zoneH() { return GenConfig.ZONE_H; }

    /** Tilemap width in tiles. */
    public int tileW() { return GenConfig.ROOM_W; }

    /** Tilemap height in tiles. */
    public int tileH() { return GenConfig.ROOM_H; }
}
