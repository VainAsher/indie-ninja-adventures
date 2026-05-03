package com.indieniinja.procgen.stamps;

import com.indieniinja.procgen.model.Tile;

/** 2-tile-wide solid column centred in an 8×8 block, air on sides. */
public final class PillarStamp implements Stamp {
    @Override
    public byte[][] tiles() {
        byte[][] t = new byte[8][8];
        for (int y = 0; y < 8; y++) {
            t[3][y] = Tile.SOLID;
            t[4][y] = Tile.SOLID;
        }
        return t;
    }
}
