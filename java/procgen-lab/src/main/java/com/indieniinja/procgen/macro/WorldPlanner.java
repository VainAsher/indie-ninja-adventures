package com.indieniinja.procgen.macro;

import com.indieniinja.procgen.intent.RegionIntent;
import com.indieniinja.procgen.intent.WorldIntent;

import java.util.List;

public final class WorldPlanner {

    private final RegionPlanner regionPlanner = new RegionPlanner();

    /**
     * Builds a WorldPlan from a WorldIntent and a list of RegionIntents in
     * progression order. Each region is placed one row below the previous on
     * the world map.
     */
    public WorldPlan plan(WorldIntent worldIntent, List<RegionIntent> regions) {
        WorldPlan worldPlan = new WorldPlan(worldIntent.seed, worldIntent.campaignName);

        for (int i = 0; i < regions.size(); i++) {
            RegionIntent intent = regions.get(i);
            long regionSeed = worldIntent.seed ^ (long) intent.id.hashCode() ^ (i * 31L);
            RegionPlan rp = regionPlanner.plan(intent, regionSeed, 0, i * 2);
            worldPlan.regions.add(rp);
        }

        return worldPlan;
    }
}
