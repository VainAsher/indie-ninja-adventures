package com.indieniinja.procgen.map;

import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.model.Tile;
import com.indieniinja.procgen.room.GeneratedRoom;

import java.awt.*;
import java.awt.image.BufferedImage;

public final class RoomMinimapRenderer {

    private static final Color[] PALETTE = buildPalette();

    /** Renders a 1-px-per-tile minimap (128×128 pixels). */
    public BufferedImage render(GeneratedRoom room) {
        BufferedImage img = new BufferedImage(
                GenConfig.ROOM_W, GenConfig.ROOM_H, BufferedImage.TYPE_INT_RGB);
        byte[][] tiles = room.tiles;
        for (int x = 0; x < GenConfig.ROOM_W; x++) {
            for (int y = 0; y < GenConfig.ROOM_H; y++) {
                int id = tiles[x][y] & 0xFF;
                Color c = id < PALETTE.length ? PALETTE[id] : Color.MAGENTA;
                img.setRGB(x, y, c.getRGB());
            }
        }
        return img;
    }

    private static Color[] buildPalette() {
        Color[] c = new Color[13];
        c[Tile.AIR]         = new Color( 20,  22,  32);
        c[Tile.SOLID]       = new Color( 90,  95, 110);
        c[Tile.PLATFORM]    = new Color(130,  85,  40);
        c[Tile.WATER]       = new Color( 30, 100, 200);
        c[Tile.LAVA]        = new Color(220,  80,  20);
        c[Tile.SPIKES]      = new Color(210, 195,  50);
        c[Tile.DOOR]        = new Color( 60, 200,  90);
        c[Tile.LOCKED_DOOR] = new Color(200,  50,  50);
        c[Tile.CLIMBABLE]   = new Color( 50, 175, 175);
        c[Tile.PICKUP]      = new Color(255, 215,   0);
        c[Tile.ENEMY_SPAWN] = new Color(255, 120,   0);
        c[Tile.SAVE_POINT]  = new Color(  0, 210, 210);
        c[Tile.BOSS_SPAWN]  = new Color(210,  50, 210);
        return c;
    }
}
