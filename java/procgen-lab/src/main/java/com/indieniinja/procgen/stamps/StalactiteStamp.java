package com.indieniinja.procgen.stamps;

import com.indieniinja.procgen.model.Tile;

/**
 * Stalactite hanging from the top row.
 * Solid top half, tapers to a point by row 5, air below.
 */
public final class StalactiteStamp implements Stamp {
    @Override
    public byte[][] tiles() {
        byte[][] t = new byte[8][8];
        // Full solid top 3 rows
        for (int x = 0; x < 8; x++) t[x][0] = Tile.SOLID;
        for (int x = 1; x < 7; x++) t[x][1] = Tile.SOLID;
        for (int x = 2; x < 6; x++) t[x][2] = Tile.SOLID;
        // Tapering point rows
        for (int x = 3; x < 5; x++) t[x][3] = Tile.SOLID;
        t[3][4] = Tile.SOLID;
        // Rest is air
        return t;
    }
}
