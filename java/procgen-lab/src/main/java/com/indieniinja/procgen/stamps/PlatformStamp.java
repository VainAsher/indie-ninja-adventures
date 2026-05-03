package com.indieniinja.procgen.stamps;

import com.indieniinja.procgen.model.Tile;

/** Single row of PLATFORM tiles at mid-height, rest AIR. */
public final class PlatformStamp implements Stamp {
    @Override
    public byte[][] tiles() {
        byte[][] t = new byte[8][8];
        for (int x = 0; x < 8; x++)
            t[x][3] = Tile.PLATFORM;
        return t;
    }
}
