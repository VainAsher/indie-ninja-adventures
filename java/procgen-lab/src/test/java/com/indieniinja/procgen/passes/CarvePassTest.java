package com.indieniinja.procgen.passes;

import com.indieniinja.procgen.intent.RoomIntent;
import com.indieniinja.procgen.model.Ability;
import com.indieniinja.procgen.model.Biome;
import com.indieniinja.procgen.model.Direction;
import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.model.ZoneBase;
import com.indieniinja.procgen.model.ZoneCell;
import com.indieniinja.procgen.model.RoomType;
import org.junit.jupiter.api.Test;

import java.util.EnumSet;
import java.util.Random;

import static org.assertj.core.api.Assertions.assertThat;

class CarvePassTest {

    @Test
    void horizontalIntroCarvesSomeAir() {
        ZoneCell[][] zones = solidGrid();
        new CarvePass().apply(zones, intent(TraversalGoal.HORIZONTAL_INTRO), rng());
        assertThat(airCount(zones)).isGreaterThan(0);
    }

    @Test
    void dashGapLeavesSolidColumnInMiddle() {
        ZoneCell[][] zones = solidGrid();
        new CarvePass().apply(zones, intent(TraversalGoal.CROSS_GAP_WITH_DASH), new Random(1L));
        int midY = GenConfig.ZONE_H / 2;
        // In the corridor rows (midY-2 to midY+1) there must be at least one column
        // that remains entirely solid — that is the gap the player must dash across.
        int gapCols = 0;
        for (int x = 1; x < GenConfig.ZONE_W - 1; x++) {
            boolean gapInCorridor = true;
            for (int y = midY - 2; y <= midY + 1; y++) {
                if (zones[x][y].base == ZoneBase.AIR) { gapInCorridor = false; break; }
            }
            if (gapInCorridor) gapCols++;
        }
        assertThat(gapCols).isGreaterThan(0);
    }

    @Test
    void dashGapMarksCriticalPath() {
        ZoneCell[][] zones = solidGrid();
        new CarvePass().apply(zones, intent(TraversalGoal.CROSS_GAP_WITH_DASH), rng());
        long criticalAir = countCriticalAir(zones);
        assertThat(criticalAir).isGreaterThan(0);
    }

    @Test
    void verticalAscentCarvesCentralShaft() {
        ZoneCell[][] zones = solidGrid();
        new CarvePass().apply(zones, intent(TraversalGoal.VERTICAL_ASCENT), rng());
        int midX = GenConfig.ZONE_W / 2;
        // Centre column of shaft must have air from top to bottom interior
        for (int y = 1; y < GenConfig.ZONE_H - 1; y++) {
            assertThat(zones[midX][y].base)
                    .as("shaft centre at y=%d", y)
                    .isEqualTo(ZoneBase.AIR);
        }
    }

    @Test
    void restGoalCarvesSomeAir() {
        ZoneCell[][] zones = solidGrid();
        new CarvePass().apply(zones, intent(TraversalGoal.REST), rng());
        assertThat(airCount(zones)).isGreaterThan(0);
    }

    // -------------------------------------------------------------------------

    private static ZoneCell[][] solidGrid() {
        return new SolidFillPass().apply();
    }

    private static Random rng() { return new Random(42L); }

    private static RoomIntent intent(String goal) {
        return new RoomIntent(RoomType.PUZZLE, Biome.DUNGEON, 1,
                EnumSet.of(Ability.DASH), EnumSet.noneOf(Direction.class),
                "", goal, true);
    }

    private static int airCount(ZoneCell[][] zones) {
        int count = 0;
        for (int x = 0; x < GenConfig.ZONE_W; x++)
            for (int y = 0; y < GenConfig.ZONE_H; y++)
                if (zones[x][y].base == ZoneBase.AIR) count++;
        return count;
    }

    private static long countCriticalAir(ZoneCell[][] zones) {
        long count = 0;
        for (int x = 0; x < GenConfig.ZONE_W; x++)
            for (int y = 0; y < GenConfig.ZONE_H; y++)
                if (zones[x][y].base == ZoneBase.AIR && zones[x][y].criticalPath) count++;
        return count;
    }
}
