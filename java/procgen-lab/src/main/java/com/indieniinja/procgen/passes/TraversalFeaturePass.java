package com.indieniinja.procgen.passes;

import com.indieniinja.procgen.intent.RoomIntent;
import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.model.Tile;
import com.indieniinja.procgen.model.ZoneBase;
import com.indieniinja.procgen.model.ZoneCell;

import java.util.Random;

/**
 * Pass 7 — Places traversal mechanics (platforms, climbable walls) after
 * the tile stamp.  Runs on the tilemap directly.
 *
 * Current scope: place floating platforms in vertical-ascent and
 * movement-pressure rooms; add climbable tiles in vertical shafts.
 */
public final class TraversalFeaturePass {

    public void apply(byte[][] tiles, ZoneCell[][] zones, RoomIntent intent, Random rng) {
        String goal = intent.traversalGoal != null ? intent.traversalGoal : "";
        switch (goal) {
            case TraversalGoal.VERTICAL_ASCENT -> addClimbableShaft(tiles);
            case TraversalGoal.MOVEMENT_PRESSURE -> addPlatforms(tiles, rng);
            case TraversalGoal.CROSS_GAP_WITH_DASH,
                 TraversalGoal.DASH_MASTERY -> addDashLedges(tiles, rng);
            default -> { /* no traversal features for other goals */ }
        }
    }

    // -------------------------------------------------------------------------

    private void addClimbableShaft(byte[][] tiles) {
        int midX  = GenConfig.ROOM_W / 2;
        // Mark the two solid columns flanking the shaft as climbable
        for (int y = 8; y < GenConfig.ROOM_H - 8; y++) {
            markClimbable(tiles, midX - 9, y);
            markClimbable(tiles, midX + 8, y);
        }
    }

    private void addPlatforms(byte[][] tiles, Random rng) {
        int count = 3 + rng.nextInt(3);
        for (int i = 0; i < count; i++) {
            int px = 16 + rng.nextInt(GenConfig.ROOM_W - 32);
            int py = 24 + rng.nextInt(GenConfig.ROOM_H - 48);
            placePlatformRow(tiles, px, py, 3 + rng.nextInt(4));
        }
    }

    private void addDashLedges(byte[][] tiles, Random rng) {
        int midY = GenConfig.ROOM_H / 2;
        // Short ledges on each side of the gap for the player to stand on
        placePlatformRow(tiles, 8, midY + rng.nextInt(4), 4);
        placePlatformRow(tiles, GenConfig.ROOM_W - 14, midY + rng.nextInt(4), 4);
    }

    private static void placePlatformRow(byte[][] tiles, int startX, int y, int len) {
        for (int x = startX; x < startX + len && x < GenConfig.ROOM_W; x++) {
            if (inBounds(x, y) && tiles[x][y] == Tile.AIR) {
                tiles[x][y] = Tile.PLATFORM;
            }
        }
    }

    private static void markClimbable(byte[][] tiles, int x, int y) {
        if (inBounds(x, y) && tiles[x][y] == Tile.SOLID) {
            tiles[x][y] = Tile.CLIMBABLE;
        }
    }

    private static boolean inBounds(int x, int y) {
        return x >= 0 && x < GenConfig.ROOM_W && y >= 0 && y < GenConfig.ROOM_H;
    }
}
