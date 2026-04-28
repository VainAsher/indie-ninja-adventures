package com.indieniinja.world;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

/**
 * Central registry of all named hub worlds in Indie Ninja Adventures.
 *
 * Mirrors Python game/hub_manager.py HubDefinition / HUB_REGISTRY.
 *
 * World hierarchy:
 *   Central Hub (starting zone, no gate)
 *     ├── Forest Hub      (requires: none)
 *     ├── Town Hub        (requires: double_jump)
 *     ├── Cave Hub        (requires: dash)
 *     ├── Sewer Hub       (requires: wall_jump)
 *     ├── Castle Hub      (requires: shuriken)
 *     ├── Dungeon Hub     (requires: teleport)
 *     └── Hallowed Cave   (requires: all — ninjutsu)
 *
 * Each hub has:
 *   - A stable string id used as the masterHubId in zone keys.
 *   - A display name shown on portals.
 *   - A biome string matching WorldGraph / BlobTileSet biome names.
 *   - A required ability to enter (empty = open).
 *   - A seed offset XOR'd with the session seed to derive the hub's world seed.
 *   - A suggested WorldGraph.WorldShape for room layout variety.
 *   - An approximate room count for this hub's WorldGraph.
 */
public final class HubRegistry {

    private HubRegistry() {}

    /**
     * One hub world definition.
     */
    public record HubDef(
        String id,
        String displayName,
        String biome,
        String requiredAbility,
        long   seedOffset,
        String graphShape,
        int    roomCount
    ) {
        /** True if a player with the given ability set can enter this hub. */
        public boolean isAccessible(java.util.Collection<String> abilities) {
            return requiredAbility.isEmpty() || abilities.contains(requiredAbility);
        }
    }

    /** All hub definitions — order is stable (display order in portal UI). */
    public static final List<HubDef> ALL = Collections.unmodifiableList(Arrays.asList(
        // Act I starting hub — Lantern Heights (warm village, Aen's home before the hollowing)
        new HubDef("lantern_heights", "Lantern Heights", "grass", "",             0x0000L, "BLOB",    10),
        new HubDef("central_hub",    "Central Hub",    "earth",  "",             0x1111L, "BLOB",    12),
        new HubDef("forest_hub",     "Forest",         "grass",  "",             0xABCDL, "BLOB",    10),
        new HubDef("town_hub",       "Town",           "earth",  "double_jump",  0x1234L, "GRID",     8),
        new HubDef("cave_hub",       "Cave",           "stone",  "dash",         0x5678L, "SNAKE",   12),
        new HubDef("sewer_hub",      "Sewer",          "sand",   "wall_jump",    0x9ABCL, "BRANCHY", 10),
        new HubDef("castle_hub",     "Castle",         "snow",   "shuriken",     0xDEF0L, "BLOB",    14),
        new HubDef("dungeon_hub",    "Dungeon",        "stone",  "teleport",     0x2468L, "TREE",    16),
        new HubDef("hallowed_cave",  "Hallowed Cave",  "stone",  "ninjutsu",     0xFEDCL, "SPIRAL",  20)
    ));

    /**
     * Look up a hub definition by its stable string ID.
     * Returns the central hub definition as a fallback if not found.
     */
    public static HubDef get(String hubId) {
        for (HubDef h : ALL) {
            if (h.id().equals(hubId)) return h;
        }
        return ALL.get(0);  // fallback: lantern_heights (Act I starting hub)
    }

    /**
     * Derive the world seed for a hub from the session seed.
     * Uses the hub's seedOffset XOR'd with the session seed to give each
     * hub its own independent procedural layout.
     */
    public static long hubSeed(long sessionSeed, String hubId) {
        return sessionSeed ^ get(hubId).seedOffset();
    }

    /**
     * Return the list of hubs that are accessible given a set of player abilities.
     * Used by portal rendering and ability-gate enforcement.
     */
    public static List<HubDef> accessible(java.util.Collection<String> abilities) {
        return ALL.stream()
            .filter(h -> h.isAccessible(abilities))
            .toList();
    }

    /**
     * Return the destination hub a portal in the given hub should link to.
     *
     * Simple rotation: each hub's exit portal leads to the next hub in the
     * registry that the player hasn't visited yet, or wraps around.
     * This is deterministic from the hub id alone.
     */
    public static HubDef nextHub(String currentHubId) {
        for (int i = 0; i < ALL.size(); i++) {
            if (ALL.get(i).id().equals(currentHubId)) {
                return ALL.get((i + 1) % ALL.size());
            }
        }
        return ALL.get(1);  // fallback: forest_hub
    }
}
