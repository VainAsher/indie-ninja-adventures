package com.indieniinja.procgen.macro;

import com.indieniinja.procgen.intent.RegionIntent;
import com.indieniinja.procgen.model.MapNode;

import java.util.ArrayList;
import java.util.List;

public final class RegionPlan {
    public final RegionIntent  intent;
    public final MapNode       node;
    /** Ordered location nodes within this region (village, dungeon, cave, gate, boss, exit). */
    public final List<MapNode> locations   = new ArrayList<>();
    /** Directed edges between location nodes: [fromId, toId] pairs. */
    public final List<String[]> edges      = new ArrayList<>();

    public RegionPlan(RegionIntent intent, MapNode node) {
        this.intent = intent;
        this.node   = node;
    }

    public void addEdge(String fromId, String toId) {
        edges.add(new String[]{fromId, toId});
    }

    public MapNode locationById(String id) {
        return locations.stream()
                .filter(n -> n.id.equals(id))
                .findFirst()
                .orElse(null);
    }
}
