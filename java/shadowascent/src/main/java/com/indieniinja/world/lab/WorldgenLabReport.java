package com.indieniinja.world.lab;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public record WorldgenLabReport(
        long worldSeed,
        String overallStatus,
        int qualityScore,
        int roomCount,
        Map<String, Integer> typeCounts,
        Map<String, Integer> warningCounts,
        List<RoomLabMetrics> rooms
) {
    public Map<String, Object> toMap() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("worldSeed", worldSeed);
        out.put("overallStatus", overallStatus);
        out.put("qualityScore", qualityScore);
        out.put("roomCount", roomCount);
        out.put("typeCounts", new LinkedHashMap<>(typeCounts));
        out.put("warningCounts", new LinkedHashMap<>(warningCounts));
        out.put("rooms", rooms.stream().map(RoomLabMetrics::toMap).toList());
        return out;
    }

    public record RoomLabMetrics(
            String roomKey,
            String roomType,
            int solidTiles,
            int platformTiles,
            int airTiles,
            List<String> warnings
    ) {
        public Map<String, Object> toMap() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("roomKey", roomKey);
            out.put("roomType", roomType);
            out.put("solidTiles", solidTiles);
            out.put("platformTiles", platformTiles);
            out.put("airTiles", airTiles);
            out.put("warnings", new ArrayList<>(warnings));
            return out;
        }
    }
}
