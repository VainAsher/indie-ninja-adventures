package com.indieniinja.procgen.stamps;

import com.indieniinja.procgen.model.Tile;

/**
 * Stalagmite rising from the bottom row.
 * Mirror of StalactiteStamp.
 */
public final class StalagmiteStamp implements Stamp {
    @Override
    public byte[][] tiles() {
        byte[][] t = new byte[8][8];
        for (int x = 0; x < 8; x++) t[x][7] = Tile.SOLID;
        for (int x = 1; x < 7; x++) t[x][6] = Tile.SOLID;
        for (int x = 2; x < 6; x++) t[x][5] = Tile.SOLID;
        for (int x = 3; x < 5; x++) t[x][4] = Tile.SOLID;
        t[3][3] = Tile.SOLID;
        return t;
    }
}
