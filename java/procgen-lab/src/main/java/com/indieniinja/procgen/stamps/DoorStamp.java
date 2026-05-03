package com.indieniinja.procgen.stamps;

import com.indieniinja.procgen.model.Tile;

/**
 * Door zone stamp: DOOR tile in the centre column/row with AIR clearance around it.
 * The surrounding tiles are AIR so the door opening is always passable.
 */
public final class DoorStamp implements Stamp {
    @Override
    public byte[][] tiles() {
        byte[][] t = new byte[8][8];
        // Full air block — door is a zone marker, not a tile that blocks traversal
        for (int x = 0; x < 8; x++)
            for (int y = 0; y < 8; y++)
                t[x][y] = Tile.AIR;
        // Door tile in centre
        t[3][3] = Tile.DOOR;
        t[4][3] = Tile.DOOR;
        t[3][4] = Tile.DOOR;
        t[4][4] = Tile.DOOR;
        return t;
    }
}
