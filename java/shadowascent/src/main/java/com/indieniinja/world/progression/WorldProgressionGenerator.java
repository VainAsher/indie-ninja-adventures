package com.indieniinja.world.progression;

import com.indieniinja.world.SeedHierarchy;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * Generates deterministic macro progression before room/section layout.
 */
public final class WorldProgressionGenerator {
    private static final String[] BIOMES = {
        "forest", "cathedral", "cavern", "archive", "foundry", "spire"
    };
    private static final String[] ABILITIES = {
        "double_jump", "dash", "wall_jump", "shuriken", "teleport", "ninjutsu"
    };

    private WorldProgressionGenerator() {}

    public static WorldProgressionGraph generate(long worldSeed) {
        Random rng = new Random(SeedHierarchy.deriveSeed(worldSeed, "world_progression"));
        int regionCount = 3 + rng.nextInt(2);
        List<WorldProgressionGraph.ProgressionNode> worldNodes = new ArrayList<>();
        List<WorldProgressionGraph.RegionHub> regionHubs = new ArrayList<>();
        List<WorldProgressionGraph.ProgressionNode> dungeonNodes = new ArrayList<>();
        List<WorldProgressionGraph.ProgressionNode> criticalPath = new ArrayList<>();

        List<String> regionIds = new ArrayList<>();
        for (int i = 0; i < regionCount; i++) {
            regionIds.add(regionId(i, worldSeed));
        }

        WorldProgressionGraph.ProgressionNode centralHub = new WorldProgressionGraph.ProgressionNode(
            "central_hub",
            WorldProgressionGraph.NodeKind.CENTRAL_HUB,
            "nexus",
            List.of(),
            List.of(),
            regionIds,
            List.of("safe", "hub", "return_point"),
            "low",
            false
        );
        worldNodes.add(centralHub);
        criticalPath.add(centralHub);

        String previousGrant = "";
        for (int i = 0; i < regionCount; i++) {
            String regionId = regionIds.get(i);
            String biome = BIOMES[Math.floorMod(i + rng.nextInt(BIOMES.length), BIOMES.length)];
            String grant = ABILITIES[Math.min(i, ABILITIES.length - 1)];
            List<String> requires = previousGrant.isBlank() ? List.of() : List.of(previousGrant);

            String entry = regionId + "_entry";
            String trial = regionId + "_trial";
            String gate = regionId + "_gate";
            String boss = regionId + "_boss";
            String treasure = regionId + "_treasure";

            WorldProgressionGraph.ProgressionNode regionNode = new WorldProgressionGraph.ProgressionNode(
                regionId,
                WorldProgressionGraph.NodeKind.REGION_HUB,
                biome,
                requires,
                List.of(),
                List.of(entry, treasure),
                List.of("region_hub", "act" + (i + 1)),
                difficulty(i),
                false
            );
            worldNodes.add(regionNode);
            criticalPath.add(regionNode);

            WorldProgressionGraph.ProgressionNode entryNode = dungeon(
                entry, biome, requires, List.of(), List.of(trial), "entry", difficulty(i), false);
            WorldProgressionGraph.ProgressionNode trialNode = dungeon(
                trial, biome, requires, List.of(grant), List.of(gate), "ability_trial", difficulty(i), false);
            WorldProgressionGraph.ProgressionNode gateNode = dungeon(
                gate, biome, List.of(grant), List.of(), List.of(boss), "lock_gate", difficulty(i), false);
            WorldProgressionGraph.ProgressionNode bossNode = dungeon(
                boss, biome, List.of(grant), List.of(), List.of(), "boss", difficulty(i), false);
            WorldProgressionGraph.ProgressionNode treasureNode = dungeon(
                treasure, biome, List.of(grant), List.of(), List.of(), "treasure", difficulty(i), true);

            dungeonNodes.add(entryNode);
            dungeonNodes.add(trialNode);
            dungeonNodes.add(gateNode);
            dungeonNodes.add(bossNode);
            dungeonNodes.add(treasureNode);
            criticalPath.add(entryNode);
            criticalPath.add(trialNode);
            criticalPath.add(gateNode);
            criticalPath.add(bossNode);

            regionHubs.add(new WorldProgressionGraph.RegionHub(
                regionId,
                "central_hub",
                List.of(
                    new WorldProgressionGraph.PortalRule(entry, requires),
                    new WorldProgressionGraph.PortalRule(treasure, List.of(grant))
                ),
                List.of(new WorldProgressionGraph.ShortcutRule(grant, boss, regionId)),
                i == 0 ? List.of("save", "shop") : List.of("save"),
                biome + "_route"
            ));

            previousGrant = grant;
        }

        return new WorldProgressionGraph(worldSeed, centralHub, worldNodes, regionHubs, dungeonNodes, criticalPath);
    }

    private static WorldProgressionGraph.ProgressionNode dungeon(
            String id,
            String biome,
            List<String> requires,
            List<String> grants,
            List<String> children,
            String tag,
            String difficulty,
            boolean optional) {
        return new WorldProgressionGraph.ProgressionNode(
            id,
            WorldProgressionGraph.NodeKind.DUNGEON,
            biome,
            requires,
            grants,
            children,
            List.of("dungeon", tag),
            difficulty,
            optional
        );
    }

    private static String regionId(int index, long seed) {
        String biome = BIOMES[Math.floorMod(index + Long.hashCode(seed), BIOMES.length)];
        return biome + "_region_" + (index + 1);
    }

    private static String difficulty(int index) {
        if (index <= 0) {
            return "low";
        }
        if (index == 1) {
            return "mid";
        }
        return "high";
    }
}
