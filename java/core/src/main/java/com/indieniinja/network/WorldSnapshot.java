package com.indieniinja.network;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

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

    // Always sent (not delta'd)
    public List<PlayerState>   players        = new ArrayList<>();

    // Full snapshot fields
    public List<EnemyState>    enemies        = new ArrayList<>();
    public List<PickupState>   pickups        = new ArrayList<>();
    public List<PlatformState> platformStates = new ArrayList<>();

    // Delta fields (only populated when isDelta=true)
    public List<EnemyState>    enemiesChanged   = new ArrayList<>();
    public List<String>        enemiesRemoved   = new ArrayList<>();
    public List<PickupState>   pickupsChanged   = new ArrayList<>();
    public List<String>        pickupsRemoved   = new ArrayList<>();
    public List<PlatformState> platformsChanged = new ArrayList<>();
    public List<String>        platformsRemoved = new ArrayList<>();

    public Map<String, Object> metadata = new LinkedHashMap<>();
    public String hubId = "";

    public WorldSnapshot() {}

    /**
     * Serialize to a Map that can be msgpack-encoded for the wire.
     * Key order matches Python's WorldSnapshot.to_dict().
     */
    public Map<String, Object> toMap() {
        Map<String, Object> m = new LinkedHashMap<>(16);
        m.put("frame",    frame);
        m.put("seed",     seed);
        m.put("is_delta", isDelta);
        m.put("players",  playerList());

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
