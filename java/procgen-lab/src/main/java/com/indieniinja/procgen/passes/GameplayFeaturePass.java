package com.indieniinja.procgen.passes;

import com.indieniinja.procgen.intent.RoomIntent;
import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.model.RoomType;
import com.indieniinja.procgen.model.Tile;
import com.indieniinja.procgen.quest.FeatureRequest;

import java.util.List;
import java.util.Random;

/**
 * Pass 8 — Places gameplay features (save points, boss spawns, pickups)
 * based on RoomType.  Features are placed only in legal air positions
 * with a solid floor directly below.
 */
public final class GameplayFeaturePass {

    public void apply(byte[][] tiles, RoomIntent intent, Random rng) {
        apply(tiles, intent, rng, List.of());
    }

    public void apply(byte[][] tiles, RoomIntent intent, Random rng,
                      List<FeatureRequest> requests) {
        switch (intent.type) {
            case SAVE     -> placeSavePoint(tiles, rng);
            case BOSS     -> placeBossSpawn(tiles);
            case TREASURE -> placePickups(tiles, rng, 3);
            case COMBAT   -> placePickups(tiles, rng, 1);
            default       -> { /* no required gameplay features */ }
        }
        for (FeatureRequest req : requests) {
            int[] pos = findFloorTile(tiles, GenConfig.ROOM_W / 2, rng);
            if (pos != null) tiles[pos[0]][pos[1]] = req.tileType;
        }
    }

    // -------------------------------------------------------------------------

    private void placeSavePoint(byte[][] tiles, Random rng) {
        int[] pos = findFloorTile(tiles, GenConfig.ROOM_W / 2, rng);
        if (pos != null) tiles[pos[0]][pos[1]] = Tile.SAVE_POINT;
    }

    private void placeBossSpawn(byte[][] tiles) {
        // Boss spawns at the centre of the room
        int cx = GenConfig.ROOM_W / 2;
        int cy = GenConfig.ROOM_H / 2;
        for (int x = cx - 2; x <= cx + 2; x++) {
            for (int y = cy - 2; y <= cy + 2; y++) {
                if (inBounds(x, y) && tiles[x][y] == Tile.AIR) {
                    tiles[x][y] = Tile.BOSS_SPAWN;
                    return;
                }
            }
        }
    }

    private void placePickups(byte[][] tiles, Random rng, int count) {
        for (int i = 0; i < count; i++) {
            int startX = 16 + rng.nextInt(GenConfig.ROOM_W - 32);
            int[] pos  = findFloorTile(tiles, startX, rng);
            if (pos != null) tiles[pos[0]][pos[1]] = Tile.PICKUP;
        }
    }

    /** Returns an air tile directly above a solid floor near startX, or null. */
    private static int[] findFloorTile(byte[][] tiles, int startX, Random rng) {
        int xRange = GenConfig.ROOM_W / 4;
        for (int dx = 0; dx < xRange; dx++) {
            int x = startX + (rng.nextBoolean() ? dx : -dx);
            if (x < 1 || x >= GenConfig.ROOM_W - 1) continue;
            for (int y = 8; y < GenConfig.ROOM_H - 2; y++) {
                if (tiles[x][y] == Tile.AIR && tiles[x][y + 1] == Tile.SOLID) {
                    return new int[]{x, y};
                }
            }
        }
        return null;
    }

    private static boolean inBounds(int x, int y) {
        return x >= 0 && x < GenConfig.ROOM_W && y >= 0 && y < GenConfig.ROOM_H;
    }
}
