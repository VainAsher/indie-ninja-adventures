package com.indieniinja.procgen.passes;

import com.indieniinja.procgen.intent.RoomIntent;
import com.indieniinja.procgen.model.Direction;
import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.model.ZoneBase;
import com.indieniinja.procgen.model.ZoneCell;

import java.util.Random;

/**
 * Pass 2 — Carves playable air-space into the solid-filled zone grid based on
 * the room's traversal goal.  Door corridors are NOT carved here; DoorPass
 * handles them.  Every carved zone on the critical path is marked accordingly.
 */
public final class CarvePass {

    private static final int W = GenConfig.ZONE_W;
    private static final int H = GenConfig.ZONE_H;

    // One-zone perimeter of solid is preserved as the room shell.
    private static final int LEFT   = 1;
    private static final int RIGHT  = W - 2;
    private static final int TOP    = 1;
    private static final int BOTTOM = H - 2;

    public void apply(ZoneCell[][] zones, RoomIntent intent, Random rng) {
        String goal = intent.traversalGoal != null ? intent.traversalGoal : TraversalGoal.HORIZONTAL_INTRO;
        switch (goal) {
            case TraversalGoal.REST,
                 TraversalGoal.HORIZONTAL_INTRO    -> carveHorizontal(zones, true);
            case TraversalGoal.CROSS_GAP_WITH_DASH -> carveDashGap(zones, rng);
            case TraversalGoal.DASH_MASTERY        -> carveDashMastery(zones, rng);
            case TraversalGoal.VERTICAL_ASCENT     -> carveVertical(zones);
            case TraversalGoal.MOVEMENT_PRESSURE   -> carveOpen(zones);
            case TraversalGoal.OPTIONAL_REWARD     -> carveOptionalReward(zones, rng);
            default                                -> carveHorizontal(zones, false);
        }
    }

    // -------------------------------------------------------------------------
    // Carve strategies

    /** Wide horizontal corridor across the mid-section. */
    private void carveHorizontal(ZoneCell[][] zones, boolean markCritical) {
        int midY = H / 2;
        // Floor at midY+2, ceiling at midY-2 — 4-zone-tall corridor
        for (int x = LEFT; x <= RIGHT; x++) {
            for (int y = midY - 2; y <= midY + 1; y++) {
                air(zones, x, y, markCritical);
            }
        }
    }

    /**
     * Horizontal corridor split by a one-zone-wide solid gap in the middle.
     * The gap forces a Dash to cross.
     */
    private void carveDashGap(ZoneCell[][] zones, Random rng) {
        int midY  = H / 2;
        int gapX  = LEFT + 2 + rng.nextInt(RIGHT - LEFT - 4); // gap not at very edge

        for (int x = LEFT; x <= RIGHT; x++) {
            for (int y = midY - 2; y <= midY + 1; y++) {
                if (x != gapX) {
                    air(zones, x, y, true);
                }
                // gapX column stays solid — forms the impassable gap
            }
        }
        // Floor below gap so there's something to land on after dash
        air(zones, gapX, midY + 2, false);
    }

    /**
     * Like dashGap but with multiple narrower gaps to require precise dash mastery.
     */
    private void carveDashMastery(ZoneCell[][] zones, Random rng) {
        int midY = H / 2;
        // Carve base corridor
        for (int x = LEFT; x <= RIGHT; x++) {
            for (int y = midY - 2; y <= midY + 1; y++) {
                air(zones, x, y, true);
            }
        }
        // Place two solid pillars to dash over
        int gap1 = LEFT + 2;
        int gap2 = LEFT + 2 + (RIGHT - LEFT) / 2;
        for (int y = midY - 1; y <= midY + 1; y++) {
            zones[gap1][y].base = ZoneBase.SOLID_FILL;
            zones[gap1][y].criticalPath = false;
            zones[gap2][y].base = ZoneBase.SOLID_FILL;
            zones[gap2][y].criticalPath = false;
        }
    }

    /** Vertical shaft rising from bottom to top with landing ledges. */
    private void carveVertical(ZoneCell[][] zones) {
        int midX = W / 2;
        for (int y = TOP; y <= BOTTOM; y++) {
            air(zones, midX - 1, y, true);
            air(zones, midX,     y, true);
            air(zones, midX + 1, y, true);
        }
        // Ledges every 4 rows to support wall-jump / climb puzzle
        for (int y = TOP; y <= BOTTOM; y += 4) {
            if (midX - 3 >= LEFT) air(zones, midX - 3, y, false);
            if (midX + 3 <= RIGHT) air(zones, midX + 3, y, false);
        }
    }

    /** Wide-open arena for movement-pressure / boss rooms. */
    private void carveOpen(ZoneCell[][] zones) {
        for (int x = LEFT; x <= RIGHT; x++) {
            for (int y = TOP; y <= BOTTOM; y++) {
                air(zones, x, y, true);
            }
        }
    }

    /** Smaller pocket to one side for optional treasure rooms. */
    private void carveOptionalReward(ZoneCell[][] zones, Random rng) {
        int pocketW = (RIGHT - LEFT) / 2;
        int startX  = rng.nextBoolean() ? LEFT : LEFT + pocketW;
        int midY    = H / 2;
        for (int x = startX; x < startX + pocketW; x++) {
            for (int y = midY - 1; y <= midY + 2; y++) {
                air(zones, x, y, false);
            }
        }
    }

    // -------------------------------------------------------------------------

    private static void air(ZoneCell[][] zones, int x, int y, boolean critical) {
        if (x < 0 || x >= W || y < 0 || y >= H) return;
        zones[x][y].base         = ZoneBase.AIR;
        zones[x][y].criticalPath = critical;
    }
}
