package com.indieniinja.procgen.intent;

import java.util.List;

public final class WorldIntent {
    public final long         seed;
    public final String       campaignName;
    public final List<String> actOrder;

    public WorldIntent(long seed, String campaignName, List<String> actOrder) {
        this.seed         = seed;
        this.campaignName = campaignName;
        this.actOrder     = List.copyOf(actOrder);
    }
}
