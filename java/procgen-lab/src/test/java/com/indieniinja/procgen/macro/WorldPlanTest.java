package com.indieniinja.procgen.macro;

import com.indieniinja.procgen.intent.RegionIntent;
import com.indieniinja.procgen.intent.WorldIntent;
import com.indieniinja.procgen.model.Ability;
import com.indieniinja.procgen.model.Biome;
import org.junit.jupiter.api.Test;

import java.util.EnumSet;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class WorldPlanTest {

    private static final WorldIntent WORLD = new WorldIntent(
            42L, "Shadow Ascent Prototype",
            List.of("Bamboo Vale", "Labyrinth Court", "Hearth Mountain", "Upper Peaks"));

    private static final List<RegionIntent> REGIONS = List.of(
            region("bamboo_vale",       "Bamboo Vale",       Biome.FOREST,   EnumSet.noneOf(Ability.class), EnumSet.of(Ability.DASH)),
            region("labyrinth_court",   "Labyrinth Court",   Biome.DUNGEON,  EnumSet.of(Ability.DASH),      EnumSet.of(Ability.WALL_JUMP)),
            region("hearth_mountain",   "Hearth Mountain",   Biome.MOUNTAIN, EnumSet.of(Ability.WALL_JUMP), EnumSet.of(Ability.CLIMB)),
            region("upper_peaks",       "Upper Peaks",       Biome.MOUNTAIN, EnumSet.of(Ability.CLIMB),     EnumSet.noneOf(Ability.class)));

    @Test
    void producesFourRegions() {
        WorldPlan plan = new WorldPlanner().plan(WORLD, REGIONS);
        assertThat(plan.regions).hasSize(4);
    }

    @Test
    void eachRegionHasIdBiomeAndDifficulty() {
        WorldPlan plan = new WorldPlanner().plan(WORLD, REGIONS);
        for (RegionPlan rp : plan.regions) {
            assertThat(rp.intent.id).isNotBlank();
            assertThat(rp.intent.primaryBiome).isNotNull();
            assertThat(rp.intent.difficulty).isGreaterThanOrEqualTo(0);
        }
    }

    @Test
    void eachRegionHasAtLeastOneLocation() {
        WorldPlan plan = new WorldPlanner().plan(WORLD, REGIONS);
        for (RegionPlan rp : plan.regions) {
            assertThat(rp.locations).isNotEmpty();
        }
    }

    @Test
    void eachRegionHasAtLeastOneEdge() {
        WorldPlan plan = new WorldPlanner().plan(WORLD, REGIONS);
        for (RegionPlan rp : plan.regions) {
            assertThat(rp.edges).isNotEmpty();
        }
    }

    @Test
    void regionLookupByIdWorks() {
        WorldPlan plan = new WorldPlanner().plan(WORLD, REGIONS);
        assertThat(plan.regionById("bamboo_vale")).isNotNull();
        assertThat(plan.regionById("upper_peaks")).isNotNull();
        assertThat(plan.regionById("does_not_exist")).isNull();
    }

    @Test
    void deterministicAcrossRuns() {
        WorldPlan a = new WorldPlanner().plan(WORLD, REGIONS);
        WorldPlan b = new WorldPlanner().plan(WORLD, REGIONS);
        for (int i = 0; i < a.regions.size(); i++) {
            assertThat(a.regions.get(i).intent.id)
                    .isEqualTo(b.regions.get(i).intent.id);
            assertThat(a.regions.get(i).locations.size())
                    .isEqualTo(b.regions.get(i).locations.size());
        }
    }

    // -------------------------------------------------------------------------

    private static RegionIntent region(String id, String name, Biome biome,
                                       EnumSet<Ability> required, EnumSet<Ability> unlocks) {
        return new RegionIntent(id, name, biome, "neutral", required, unlocks,
                1, true, true, true);
    }
}
