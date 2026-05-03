package com.indieniinja.procgen.stamps;

import com.indieniinja.procgen.model.Tile;

/** 8×8 solid frame with air interior (1-tile-thick walls). */
public final class HollowBoxStamp implements Stamp {
    @Override
    public byte[][] tiles() {
        byte[][] t = new byte[8][8];
        for (int x = 0; x < 8; x++) {
            for (int y = 0; y < 8; y++) {
                boolean edge = x == 0 || x == 7 || y == 0 || y == 7;
                t[x][y] = edge ? Tile.SOLID : Tile.AIR;
            }
        }
        return t;
    }
}
