package com.indieniinja.network;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Wire descriptor for a single room in the world graph.
 *
 * Sent in full WorldSnapshot.worldRooms so the client can stitch all rooms
 * into a single megamap without needing additional round-trips.
 *
 * Python parity: systems/megamap.py Megamap — each room entry in room_tilemaps.
 */
public final class WorldRoomDescriptor {

    public int          gridX;
    public int          gridY;
    public long         seed;
    public String       roomType   = "combat";
    public List<String> neighborDirs = new ArrayList<>();
    public int          biomeIndex = 0;

    public Map<String, Object> toMap() {
        Map<String, Object> m = new LinkedHashMap<>(6);
        m.put("gx",            gridX);
        m.put("gy",            gridY);
        m.put("seed",          seed);
        m.put("room_type",     roomType);
        m.put("neighbor_dirs", new ArrayList<>(neighborDirs));
        m.put("biome_index",   biomeIndex);
        return m;
    }

    public static WorldRoomDescriptor fromMap(Map<String, Object> m) {
        WorldRoomDescriptor d = new WorldRoomDescriptor();
        d.gridX      = (int) num(m, "gx", 0L);
        d.gridY      = (int) num(m, "gy", 0L);
        d.seed       = num(m, "seed", 0L);
        d.roomType   = str(m, "room_type", "combat");
        d.biomeIndex = (int) num(m, "biome_index", 0L);
        Object dirs = m.get("neighbor_dirs");
        if (dirs instanceof List<?> list)
            for (Object dir : list) d.neighborDirs.add(dir.toString());
        return d;
    }

    private static long   num(Map<String,Object> m, String k, long d)   { Object v=m.get(k); return v instanceof Number n?n.longValue():d; }
    private static String str(Map<String,Object> m, String k, String d) { Object v=m.get(k); return v!=null?v.toString():d; }
}
