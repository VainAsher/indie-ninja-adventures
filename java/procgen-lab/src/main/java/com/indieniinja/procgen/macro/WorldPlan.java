package com.indieniinja.procgen.macro;

import java.util.ArrayList;
import java.util.List;

public final class WorldPlan {
    public final long           seed;
    public final String         campaignName;
    /** Regions in progression order. */
    public final List<RegionPlan> regions = new ArrayList<>();

    public WorldPlan(long seed, String campaignName) {
        this.seed         = seed;
        this.campaignName = campaignName;
    }

    public RegionPlan regionById(String id) {
        return regions.stream()
                .filter(r -> r.intent.id.equals(id))
                .findFirst()
                .orElse(null);
    }
}
