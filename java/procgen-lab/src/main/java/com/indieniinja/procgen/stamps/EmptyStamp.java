package com.indieniinja.procgen.stamps;

import com.indieniinja.procgen.model.Tile;

/** 8×8 block of AIR. */
public final class EmptyStamp implements Stamp {
    @Override
    public byte[][] tiles() {
        byte[][] t = new byte[8][8];
        for (int x = 0; x < 8; x++)
            for (int y = 0; y < 8; y++)
                t[x][y] = Tile.AIR;
        return t;
    }
}
