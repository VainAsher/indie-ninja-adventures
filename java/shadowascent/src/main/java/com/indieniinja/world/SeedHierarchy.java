package com.indieniinja.world;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/**
 * Deterministic 6-level seed derivation — Java port of systems/seed_hierarchy.py.
 *
 * Algorithm (must be byte-identical to Python SeedDerivation.derive_seed):
 *   combined = "{parentSeed}:{identifier}"
 *   digest   = SHA-256(combined.encode("utf-8"))
 *   result   = (first 4 bytes as big-endian uint32) & 0x7FFF_FFFF
 *
 * Hierarchy:
 *   Level 1 — worldSeed        (user input)
 *   Level 2 — regionSeed       = derive(worldSeed,   "region:{regionId}")
 *   Level 3 — missionSeed      = derive(regionSeed,  "mission:{missionId}")
 *   Level 4 — roomSeed         = derive(missionSeed, "room:{roomNodeId}")
 *   Level 5 — subroomSeed      = derive(roomSeed,    "subroom:{subroomIndex}")
 *   Level 6 — featureSeed      = derive(subroomSeed, "feature:{featureType}")
 */
public final class SeedHierarchy {

    private SeedHierarchy() {}

    // ── Core derivation ────────────────────────────────────────────────��──────

    /**
     * Derive a child seed from a parent seed and a string identifier.
     *
     * Produces the same value as Python's SeedDerivation.derive_seed() for
     * identical inputs.
     *
     * @param parentSeed parent seed (any long; only lower 32 bits used in format)
     * @param identifier derivation label, e.g. "region:forest"
     * @return positive 32-bit seed value (0 .. Integer.MAX_VALUE)
     */
    public static int deriveSeed(long parentSeed, String identifier) {
        // Format matches Python: f"{parent_seed}:{identifier}"
        String combined = parentSeed + ":" + identifier;
        byte[] digest   = sha256(combined.getBytes(StandardCharsets.UTF_8));

        // First 4 bytes, big-endian uint32, masked to positive 31-bit range
        int raw = ((digest[0] & 0xFF) << 24)
                | ((digest[1] & 0xFF) << 16)
                | ((digest[2] & 0xFF) <<  8)
                |  (digest[3] & 0xFF);
        return raw & 0x7FFF_FFFF;
    }

    // ── Level helpers ─────────────────────────────────────────────────────────

    /** Level 2: region seed from world seed. */
    public static int deriveRegion(long worldSeed, String regionId) {
        return deriveSeed(worldSeed, "region:" + regionId);
    }

    /** Level 3: mission seed from region seed. */
    public static int deriveMission(long regionSeed, String missionId) {
        return deriveSeed(regionSeed, "mission:" + missionId);
    }

    /** Level 4: room seed from mission seed. */
    public static int deriveRoom(long missionSeed, String roomNodeId) {
        return deriveSeed(missionSeed, "room:" + roomNodeId);
    }

    /** Level 4 (int index): room seed from mission seed and room index. */
    public static int deriveRoom(long missionSeed, int roomIndex) {
        return deriveRoom(missionSeed, String.valueOf(roomIndex));
    }

    /** Level 5: sub-room seed from room seed. */
    public static int deriveSubroom(long roomSeed, int subroomIndex) {
        return deriveSeed(roomSeed, "subroom:" + subroomIndex);
    }

    /** Level 6: feature seed from sub-room seed. */
    public static int deriveFeature(long subroomSeed, String featureType) {
        return deriveSeed(subroomSeed, "feature:" + featureType);
    }

    // ── SHA-256 helper ────────────────────────────────────────────────────────

    private static byte[] sha256(byte[] input) {
        try {
            return MessageDigest.getInstance("SHA-256").digest(input);
        } catch (NoSuchAlgorithmException e) {
            // SHA-256 is guaranteed present in every JRE
            throw new IllegalStateException("SHA-256 not available", e);
        }
    }
}
