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
        Map<String, String> zoneLegend,
        Map<String, String> tileLegend,
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
        out.put("zoneLegend", new LinkedHashMap<>(zoneLegend));
        out.put("tileLegend", new LinkedHashMap<>(tileLegend));
        out.put("typeCounts", new LinkedHashMap<>(typeCounts));
        out.put("warningCounts", new LinkedHashMap<>(warningCounts));
        out.put("rooms", rooms.stream().map(RoomLabMetrics::toMap).toList());
        return out;
    }

    public record RoomLabMetrics(
            String roomKey,
            String roomType,
            List<String> neighborDirs,
            int biomeIndex,
            int solidTiles,
            int platformTiles,
            int airTiles,
            List<String> zoneRows,
            List<String> tilePreviewRows,
            List<String> warnings
    ) {
        public Map<String, Object> toMap() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("roomKey", roomKey);
            out.put("roomType", roomType);
            out.put("neighborDirs", new ArrayList<>(neighborDirs));
            out.put("biomeIndex", biomeIndex);
            out.put("solidTiles", solidTiles);
            out.put("platformTiles", platformTiles);
            out.put("airTiles", airTiles);
            out.put("zoneRows", new ArrayList<>(zoneRows));
            out.put("tilePreviewRows", new ArrayList<>(tilePreviewRows));
            out.put("warnings", new ArrayList<>(warnings));
            return out;
        }
    }
}
