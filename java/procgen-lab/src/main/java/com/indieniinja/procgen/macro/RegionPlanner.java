package com.indieniinja.procgen.macro;

import com.indieniinja.procgen.intent.RegionIntent;
import com.indieniinja.procgen.model.MapNode;
import com.indieniinja.procgen.model.MapNodeType;

import java.util.Random;

public final class RegionPlanner {

    /**
     * Builds a RegionPlan from the given intent.
     * Layout coordinates are assigned deterministically from the seed.
     *
     * @param intent region definition
     * @param seed   derived from world seed + region index
     * @param baseX  world-map column offset for this region
     * @param baseY  world-map row offset for this region
     */
    public RegionPlan plan(RegionIntent intent, long seed, int baseX, int baseY) {
        Random rng = new Random(seed);

        MapNode regionNode = new MapNode(
                intent.id,
                intent.displayName,
                MapNodeType.REGION,
                baseX,
                baseY);

        RegionPlan plan = new RegionPlan(intent, regionNode);

        int col = 0;

        // Village (optional)
        MapNode prev = null;
        if (intent.hasVillage) {
            MapNode village = node(intent.id + "_village", intent.displayName + " Camp",
                    MapNodeType.VILLAGE, baseX + col, baseY + 1);
            plan.locations.add(village);
            col++;
            prev = village;
        }

        // Main dungeon (optional but typical)
        MapNode dungeon = null;
        if (intent.hasMainDungeon) {
            dungeon = node(intent.id + "_dungeon", intent.displayName + " Dungeon",
                    MapNodeType.DUNGEON, baseX + col, baseY + 1);
            plan.locations.add(dungeon);
            if (prev != null) plan.addEdge(prev.id, dungeon.id);
            col++;
            prev = dungeon;
        }

        // Optional cave branch (hangs off dungeon node)
        if (intent.hasOptionalCave) {
            MapNode cave = node(intent.id + "_cave", intent.displayName + " Cave",
                    MapNodeType.CAVE, baseX + col, baseY + 2);
            plan.locations.add(cave);
            String branchFrom = dungeon != null ? dungeon.id
                    : (prev != null ? prev.id : regionNode.id);
            plan.addEdge(branchFrom, cave.id);
            // cave is a dead-end branch — no col advance on main path
        }

        // Gate
        MapNode gate = node(intent.id + "_gate", intent.displayName + " Gate",
                MapNodeType.GATE, baseX + col, baseY + 1);
        gate.locked         = !intent.requiredAbilities.isEmpty();
        gate.requiredAbility = intent.requiredAbilities.isEmpty()
                ? null
                : intent.requiredAbilities.iterator().next();
        plan.locations.add(gate);
        if (prev != null) plan.addEdge(prev.id, gate.id);
        col++;

        // Boss
        MapNode boss = node(intent.id + "_boss", intent.displayName + " Guardian",
                MapNodeType.BOSS, baseX + col, baseY + 1);
        plan.locations.add(boss);
        plan.addEdge(gate.id, boss.id);
        col++;

        // Exit
        MapNode exit = node(intent.id + "_exit", "Exit to Next Region",
                MapNodeType.EXIT, baseX + col, baseY + 1);
        plan.locations.add(exit);
        plan.addEdge(boss.id, exit.id);

        return plan;
    }

    private static MapNode node(String id, String name, MapNodeType type, int x, int y) {
        return new MapNode(id, name, type, x, y);
    }
}
