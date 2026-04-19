package com.indieniinja.content;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

public class ContentRegistry {

    private final Map<String, EnemyDefinition>    enemies   = new LinkedHashMap<>();
    private final Map<String, NpcDefinition>      npcs      = new LinkedHashMap<>();
    private final Map<String, RoomTypeDefinition> roomTypes = new LinkedHashMap<>();

    // ── Enemy ──────────────────────────────────────────────────────────────────

    public void registerEnemy(EnemyDefinition def) {
        enemies.put(def.id(), def);
    }

    public EnemyDefinition getEnemy(String id) {
        EnemyDefinition def = enemies.get(id);
        if (def == null) throw new ContentNotFoundException("Unknown enemy id: '" + id + "'");
        return def;
    }

    public EnemyDefinition getEnemyOrNull(String id) {
        return enemies.get(id);
    }

    public List<EnemyDefinition> allEnemies() {
        return new ArrayList<>(enemies.values());
    }

    public List<EnemyDefinition> enemiesByTag(String tag) {
        return enemies.values().stream()
            .filter(e -> e.tags().contains(tag))
            .collect(Collectors.toList());
    }

    public List<EnemyDefinition> enemiesByBiome(String biome) {
        return enemies.values().stream()
            .filter(e -> e.biomeAffinity().contains(biome) || e.biomeAffinity().contains("any"))
            .collect(Collectors.toList());
    }

    // ── NPC ───────────────────────────────────────────────────────────────────

    public void registerNpc(NpcDefinition def) {
        npcs.put(def.id(), def);
    }

    public NpcDefinition getNpc(String id) {
        NpcDefinition def = npcs.get(id);
        if (def == null) throw new ContentNotFoundException("Unknown npc id: '" + id + "'");
        return def;
    }

    public NpcDefinition getNpcOrNull(String id) {
        return npcs.get(id);
    }

    public List<NpcDefinition> allNpcs() {
        return new ArrayList<>(npcs.values());
    }

    // ── RoomType ──────────────────────────────────────────────────────────────

    public void registerRoomType(RoomTypeDefinition def) {
        roomTypes.put(def.id(), def);
    }

    public RoomTypeDefinition getRoomType(String id) {
        RoomTypeDefinition def = roomTypes.get(id);
        if (def == null) throw new ContentNotFoundException("Unknown room type id: '" + id + "'");
        return def;
    }

    public RoomTypeDefinition getRoomTypeOrNull(String id) {
        return roomTypes.get(id);
    }

    public List<RoomTypeDefinition> allRoomTypes() {
        return new ArrayList<>(roomTypes.values());
    }

    // ── Stats ─────────────────────────────────────────────────────────────────

    public int enemyCount()   { return enemies.size();   }
    public int npcCount()     { return npcs.size();      }
    public int roomTypeCount(){ return roomTypes.size();  }
}
