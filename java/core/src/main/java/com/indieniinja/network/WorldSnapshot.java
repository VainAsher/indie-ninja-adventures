package com.indieniinja.network;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
// NPCState is in the same package — no explicit import needed.

/**
 * Full authoritative world state broadcast by the server each tick (Phase 3).
 * Java equivalent of Python network/snapshots.py WorldSnapshot.
 *
 * Key ordering in toMap() mirrors Python WorldSnapshot.to_dict() exactly
 * to ensure byte-identical msgpack serialisation with Python clients.
 *
 * Delta encoding fields (enemies_changed, enemies_removed, etc.) are populated
 * by DeltaEncoder before serialisation; they are null/empty in full snapshots.
 */
public final class WorldSnapshot {

    public long   frame;
    public long   seed;
    public boolean isDelta;

    /** Grid coordinates of the room this snapshot describes (multi-room world). */
    public int    roomGridX = 0;
    public int    roomGridY = 0;

    /**
     * Room type wire string: "start","exit","shop","combat","platform","treasure","boss".
     * Client uses this to pick the correct ZonePlanner probabilities.
     */
    public String roomType = "combat";

    /**
     * Directions in which this room has door openings ("up","down","left","right").
     * Client uses this to carve matching openings in the room's tile grid.
     */
    public List<String> neighborDirs = new ArrayList<>();

    // Always sent (not delta'd)
    public List<PlayerState>   players        = new ArrayList<>();

    // Full snapshot fields
    public List<EnemyState>    enemies        = new ArrayList<>();
    public List<PickupState>   pickups        = new ArrayList<>();
    public List<PlatformState> platformStates = new ArrayList<>();
    public List<ShurikenState> shurikens      = new ArrayList<>();
    /** NPCs — always full list, not delta-encoded (few entities, slow-changing). */
    public List<NPCState>      npcs           = new ArrayList<>();

    /**
     * Full world room layout — sent on full snapshots only (not deltas).
     * Client uses this to stitch all room tilemaps into a single megamap.
     * Empty list means "no change" (use previous megamap).
     */
    public List<WorldRoomDescriptor> worldRooms = new ArrayList<>();

    /**
     * Shop states for all shop NPCs in the current room — full snapshots only.
     * Client uses this to populate ShopOverlay when player interacts with a shop NPC.
     */
    public List<ShopState> shopStates = new ArrayList<>();

    // Delta fields (only populated when isDelta=true)
    public List<EnemyState>    enemiesChanged   = new ArrayList<>();
    public List<String>        enemiesRemoved   = new ArrayList<>();
    public List<PickupState>   pickupsChanged   = new ArrayList<>();
    public List<String>        pickupsRemoved   = new ArrayList<>();
    public List<PlatformState> platformsChanged = new ArrayList<>();
    public List<String>        platformsRemoved = new ArrayList<>();

    public Map<String, Object> metadata = new LinkedHashMap<>();
    public String hubId = "";

    // ── Game mode fields ──────────────────────────────────────────────────────
    /** Active play mode wire string: "arcade", "campaign", "sandbox". */
    public String gameMode    = "arcade";
    /** Arcade mode: cumulative kill score across this session. */
    public int    arcadeScore = 0;
    /** Arcade mode: current dungeon depth (rooms cleared). */
    public int    arcadeDepth = 0;
    /** Arcade mode: number of rooms in this depth level. */
    public int    arcadeRooms = 10;

    public WorldSnapshot() {}

    /** Deserialize from a decoded payload map (client-side receive path). */
    @SuppressWarnings("unchecked")
    public static WorldSnapshot fromMap(java.util.Map<String, Object> m) {
        WorldSnapshot s = new WorldSnapshot();
        s.frame      = num(m, "frame",      0L);
        s.seed       = num(m, "seed",       0L);
        s.isDelta    = bool(m, "is_delta");
        s.hubId       = str(m, "hub_id",     "");
        s.gameMode    = str(m, "game_mode",  "arcade");
        s.arcadeScore = (int) num(m, "arcade_score", 0L);
        s.arcadeDepth = (int) num(m, "arcade_depth", 0L);
        s.arcadeRooms = (int) num(m, "arcade_rooms", 10L);
        s.roomGridX  = (int) num(m, "room_grid_x", 0L);
        s.roomGridY  = (int) num(m, "room_grid_y", 0L);
        s.roomType   = str(m, "room_type", "combat");
        for (Object d : list(m, "neighbor_dirs")) s.neighborDirs.add(d.toString());

        for (Object p : list(m, "players"))
            if (p instanceof java.util.Map<?,?> pm)
                s.players.add(PlayerState.fromMap((java.util.Map<String,Object>) pm));

        if (s.isDelta) {
            for (Object e : list(m, "enemies_changed"))
                if (e instanceof java.util.Map<?,?> em)
                    s.enemiesChanged.add(EnemyState.fromMap((java.util.Map<String,Object>) em));
            for (Object e : list(m, "enemies_removed"))
                s.enemiesRemoved.add(e.toString());
            for (Object p : list(m, "pickups_changed"))
                if (p instanceof java.util.Map<?,?> pm)
                    s.pickupsChanged.add(PickupState.fromMap((java.util.Map<String,Object>) pm));
            for (Object p : list(m, "pickups_removed"))
                s.pickupsRemoved.add(p.toString());
            for (Object p : list(m, "platforms_changed"))
                if (p instanceof java.util.Map<?,?> pm)
                    s.platformsChanged.add(PlatformState.fromMap((java.util.Map<String,Object>) pm));
            for (Object p : list(m, "platforms_removed"))
                s.platformsRemoved.add(p.toString());
        } else {
            for (Object e : list(m, "enemies"))
                if (e instanceof java.util.Map<?,?> em)
                    s.enemies.add(EnemyState.fromMap((java.util.Map<String,Object>) em));
            for (Object p : list(m, "pickups"))
                if (p instanceof java.util.Map<?,?> pm)
                    s.pickups.add(PickupState.fromMap((java.util.Map<String,Object>) pm));
            for (Object p : list(m, "platform_states"))
                if (p instanceof java.util.Map<?,?> pm)
                    s.platformStates.add(PlatformState.fromMap((java.util.Map<String,Object>) pm));
        }
        // Shurikens always present on the wire (not delta-encoded — see toMap()).
        for (Object sh : list(m, "shurikens"))
            if (sh instanceof java.util.Map<?,?> shm)
                s.shurikens.add(ShurikenState.fromMap((java.util.Map<String,Object>) shm));
        // NPCs always present on the wire (not delta-encoded).
        for (Object n : list(m, "npcs"))
            if (n instanceof java.util.Map<?,?> nm)
                s.npcs.add(NPCState.fromMap((java.util.Map<String,Object>) nm));
        // World room layout — present only on full snapshots.
        for (Object r : list(m, "world_rooms"))
            if (r instanceof java.util.Map<?,?> rm)
                s.worldRooms.add(WorldRoomDescriptor.fromMap((java.util.Map<String,Object>) rm));
        // Shop states — present only on full snapshots.
        for (Object r : list(m, "shop_states"))
            if (r instanceof java.util.Map<?,?> rm)
                s.shopStates.add(ShopState.fromMap(rm));
        return s;
    }

    @SuppressWarnings("unchecked")
    private static java.util.List<Object> list(java.util.Map<String,Object> m, String k) {
        Object v = m.get(k);
        return v instanceof java.util.List<?> l ? (java.util.List<Object>) l : java.util.List.of();
    }
    private static long    num(java.util.Map<String,Object> m, String k, long   d) { Object v=m.get(k); return v instanceof Number n?n.longValue():d; }
    private static boolean bool(java.util.Map<String,Object> m, String k)           { Object v=m.get(k); return v instanceof Boolean b&&b; }
    private static String  str(java.util.Map<String,Object> m, String k, String d)  { Object v=m.get(k); return v!=null?v.toString():d; }

    /**
     * Serialize to a Map that can be msgpack-encoded for the wire.
     * Key order matches Python's WorldSnapshot.to_dict().
     */
    public Map<String, Object> toMap() {
        Map<String, Object> m = new LinkedHashMap<>(18);
        m.put("frame",       frame);
        m.put("seed",        seed);
        m.put("is_delta",    isDelta);
        m.put("room_grid_x",  roomGridX);
        m.put("room_grid_y",  roomGridY);
        m.put("room_type",    roomType);
        m.put("neighbor_dirs", neighborDirs);
        m.put("players",      playerList());

        if (isDelta) {
            m.put("enemies_changed",   mapList(enemiesChanged));
            m.put("enemies_removed",   enemiesRemoved);
            m.put("pickups_changed",   mapList(pickupsChanged));
            m.put("pickups_removed",   pickupsRemoved);
            m.put("platforms_changed", mapList(platformsChanged));
            m.put("platforms_removed", platformsRemoved);
        } else {
            m.put("enemies",         mapList(enemies));
            m.put("pickups",         mapList(pickups));
            m.put("platform_states", mapList(platformStates));
        }
        // Shurikens always included — they are short-lived (2s TTL) and not delta-encoded.
        // Without this, clients only see shurikens on full snapshots every ~3s, which means
        // they never appear (shuriken TTL < full-snapshot interval).
        m.put("shurikens", shurikenList());
        // NPCs always included — few entities, slow-changing, no delta encoding needed.
        m.put("npcs",      npcList());
        // World room layout — full snapshots only; empty list on deltas (client keeps previous).
        m.put("world_rooms", isDelta ? java.util.List.of() : worldRoomList());
        // Shop states — full snapshots only.
        m.put("shop_states", isDelta ? java.util.List.of() : shopStateList());

        m.put("game_mode",    gameMode);
        m.put("arcade_score", arcadeScore);
        m.put("arcade_depth", arcadeDepth);
        m.put("arcade_rooms", arcadeRooms);
        m.put("metadata", metadata);
        m.put("hub_id",   hubId != null ? hubId : "");
        return m;
    }

    // ── helpers ───────────────────────────────────────────────────────────────

    private List<Map<String, Object>> playerList() {
        List<Map<String, Object>> out = new ArrayList<>(players.size());
        for (PlayerState p : players) out.add(p.toMap());
        return out;
    }

    private List<Map<String, Object>> shurikenList() {
        List<Map<String, Object>> out = new ArrayList<>(shurikens.size());
        for (ShurikenState s : shurikens) out.add(s.toMap());
        return out;
    }

    private List<Map<String, Object>> npcList() {
        List<Map<String, Object>> out = new ArrayList<>(npcs.size());
        for (NPCState n : npcs) out.add(n.toMap());
        return out;
    }

    private List<Map<String, Object>> worldRoomList() {
        List<Map<String, Object>> out = new ArrayList<>(worldRooms.size());
        for (WorldRoomDescriptor r : worldRooms) out.add(r.toMap());
        return out;
    }

    private List<Map<String, Object>> shopStateList() {
        List<Map<String, Object>> out = new ArrayList<>(shopStates.size());
        for (ShopState s : shopStates) out.add(s.toMap());
        return out;
    }

    private <T> List<Map<String, Object>> mapList(List<T> items) {
        List<Map<String, Object>> out = new ArrayList<>(items.size());
        for (T item : items) {
            if      (item instanceof EnemyState    e) out.add(e.toMap());
            else if (item instanceof PickupState   p) out.add(p.toMap());
            else if (item instanceof PlatformState p) out.add(p.toMap());
        }
        return out;
    }
}
