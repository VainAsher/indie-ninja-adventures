package com.indieniinja.server;

import com.indieniinja.network.EnemyState;
import com.indieniinja.network.PickupState;
import com.indieniinja.network.PlatformState;
import com.indieniinja.network.WorldSnapshot;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.zip.CRC32;

/**
 * Delta encoder for WorldSnapshot — computes changed/removed entity sets.
 *
 * Java equivalent of Python network/server.py _dict_hash() based delta logic,
 * but using CRC32 on fixed-layout float/int fields instead of
 * hash(tuple(sorted(d.items()))) — zero allocation per unchanged entity.
 *
 * One DeltaEncoder instance per ZoneInstance (not shared across zones).
 */
final class DeltaEncoder {

    // CRC32 is not thread-safe; this encoder is only used from the sim thread
    private final CRC32 crc = new CRC32();

    private final Map<String, Long> enemyChecksums    = new HashMap<>();
    private final Map<String, Long> pickupChecksums   = new HashMap<>();
    private final Map<String, Long> platformChecksums = new HashMap<>();

    // ── Enemy delta ───────────────────────────────────────────────────────────

    List<EnemyState> enemiesChanged(List<EnemyState> current) {
        List<EnemyState> changed = new ArrayList<>();
        for (EnemyState e : current) {
            long cs = checksumEnemy(e);
            if (!cs.equals(enemyChecksums.get(e.enemyId))) {
                enemyChecksums.put(e.enemyId, cs);
                changed.add(e);
            }
        }
        return changed;
    }

    List<String> enemiesRemoved(List<EnemyState> current) {
        Set<String> currentIds = new HashSet<>();
        for (EnemyState e : current) currentIds.add(e.enemyId);
        List<String> removed = new ArrayList<>();
        for (String id : enemyChecksums.keySet()) {
            if (!currentIds.contains(id)) removed.add(id);
        }
        removed.forEach(enemyChecksums::remove);
        return removed;
    }

    // ── Pickup delta ──────────────────────────────────────────────────────────

    List<PickupState> pickupsChanged(List<PickupState> current) {
        List<PickupState> changed = new ArrayList<>();
        for (PickupState p : current) {
            long cs = checksumPickup(p);
            if (!cs.equals(pickupChecksums.get(p.pickupId))) {
                pickupChecksums.put(p.pickupId, cs);
                changed.add(p);
            }
        }
        return changed;
    }

    List<String> pickupsRemoved(List<PickupState> current) {
        Set<String> ids = new HashSet<>();
        for (PickupState p : current) ids.add(p.pickupId);
        List<String> removed = new ArrayList<>();
        for (String id : pickupChecksums.keySet()) {
            if (!ids.contains(id)) removed.add(id);
        }
        removed.forEach(pickupChecksums::remove);
        return removed;
    }

    // ── Platform delta ────────────────────────────────────────────────────────

    List<PlatformState> platformsChanged(List<PlatformState> current) {
        List<PlatformState> changed = new ArrayList<>();
        for (PlatformState p : current) {
            long cs = checksumPlatform(p);
            if (!cs.equals(platformChecksums.get(p.platformId))) {
                platformChecksums.put(p.platformId, cs);
                changed.add(p);
            }
        }
        return changed;
    }

    List<String> platformsRemoved(List<PlatformState> current) {
        Set<String> ids = new HashSet<>();
        for (PlatformState p : current) ids.add(p.platformId);
        List<String> removed = new ArrayList<>();
        for (String id : platformChecksums.keySet()) {
            if (!ids.contains(id)) removed.add(id);
        }
        removed.forEach(platformChecksums::remove);
        return removed;
    }

    /** Reset all checksums (triggers full re-diff on next tick — used after full snapshot). */
    void reset() {
        enemyChecksums.clear();
        pickupChecksums.clear();
        platformChecksums.clear();
    }

    // ── CRC helpers ───────────────────────────────────────────────────────────

    private long checksumEnemy(EnemyState e) {
        crc.reset();
        updateFloat(e.x);
        updateFloat(e.y);
        updateFloat(e.vx);
        updateFloat(e.vy);
        crc.update(e.hp);
        crc.update(e.aiState.hashCode());
        crc.update(e.facingRight ? 1 : 0);
        return crc.getValue();
    }

    private long checksumPickup(PickupState p) {
        crc.reset();
        updateFloat(p.x);
        updateFloat(p.y);
        crc.update(p.alive ? 1 : 0);
        return crc.getValue();
    }

    private long checksumPlatform(PlatformState p) {
        crc.reset();
        updateFloat(p.posY);
        updateFloat(p.timer);
        updateFloat(p.vy);
        crc.update(p.state.hashCode());
        return crc.getValue();
    }

    private void updateFloat(float v) {
        int bits = Float.floatToRawIntBits(v);
        crc.update((bits >>> 24) & 0xFF);
        crc.update((bits >>> 16) & 0xFF);
        crc.update((bits >>>  8) & 0xFF);
        crc.update(bits         & 0xFF);
    }
}
