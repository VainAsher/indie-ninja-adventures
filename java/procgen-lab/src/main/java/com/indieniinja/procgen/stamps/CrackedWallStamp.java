package com.indieniinja.procgen.stamps;

import com.indieniinja.procgen.model.Tile;

/**
 * Dungeon wall with a few interior air holes suggesting cracks.
 * Outer border remains solid; scattered interior tiles are AIR.
 */
public final class CrackedWallStamp implements Stamp {
    private static final int[][] CRACKS = {{2,2},{2,5},{5,3},{5,6},{3,4},{6,2}};

    @Override
    public byte[][] tiles() {
        byte[][] t = new byte[8][8];
        for (int x = 0; x < 8; x++)
            for (int y = 0; y < 8; y++)
                t[x][y] = Tile.SOLID;
        for (int[] c : CRACKS) t[c[0]][c[1]] = Tile.AIR;
        return t;
    }
}
