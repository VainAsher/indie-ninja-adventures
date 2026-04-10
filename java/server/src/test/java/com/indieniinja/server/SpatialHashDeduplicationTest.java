package com.indieniinja.server;

import com.indieniinja.core.EntityManager;
import com.indieniinja.core.EntityType;
import com.indieniinja.core.EventBus;
import com.indieniinja.core.TickEvent;
import com.indieniinja.physics.CollisionSystem;
import com.indieniinja.physics.PhysicsConstants;
import com.indieniinja.physics.PhysicsState;
import com.indieniinja.physics.PhysicsSystem;
import com.indieniinja.physics.SpatialHash;
import com.indieniinja.physics.TileRect;
import com.indieniinja.physics.TileType;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

/**
 * SpatialHash multi-chunk candidate behaviour (audit gap PHYS-4/PHYS-6).
 *
 * The Javadoc on {@link SpatialHash#candidates} explicitly notes:
 * "The returned list may contain duplicates if a tile spans multiple chunks;
 *  callers should de-duplicate by result (collision resolution is idempotent)."
 *
 * These tests:
 * <ol>
 *   <li>Document that the duplicate contract is met when a tile straddles a boundary</li>
 *   <li>Prove that {@link CollisionSystem} is idempotent — the entity is not
 *       double-pushed by the duplicate</li>
 *   <li>Verify the fast path (single-chunk query) returns no duplicates</li>
 *   <li>Confirm correct candidate lookup across all four adjacent-chunk layouts</li>
 * </ol>
 */
class SpatialHashDeduplicationTest {

    private static final float TOL = 0.5f;

    // ── Duplicate contract ────────────────────────────────────────────────────

    /**
     * A tile that spans the chunk boundary at x=320 is indexed in two chunks.
     * When candidates() is called for an entity in the left chunk, that tile
     * must be returned even though part of it lives in the right chunk.
     */
    @Test
    void tileSpanningChunkBoundaryIsFoundByQuery() {
        SpatialHash hash = new SpatialHash();
        // Tile at x=290, width=64 → spans x=290..353, crossing boundary at x=320
        TileRect spanning = new TileRect(290, 0, 64, 32, false, TileType.SOLID.id);
        hash.insert(spanning);

        // Query from an entity centred left of the boundary (chunk 0)
        List<TileRect> cands = hash.candidates(270, 0, 28, 56);
        assertThat(cands).contains(spanning);
    }

    @Test
    void tileSpanningChunkBoundaryIsFoundByQueryFromRightChunk() {
        SpatialHash hash = new SpatialHash();
        TileRect spanning = new TileRect(290, 0, 64, 32, false, TileType.SOLID.id);
        hash.insert(spanning);

        // Query from an entity centred right of the boundary (chunk 1)
        List<TileRect> cands = hash.candidates(330, 0, 28, 56);
        assertThat(cands).contains(spanning);
    }

    /**
     * A tile spanning the boundary is indexed in BOTH chunks.
     * candidates() for a query that spans both chunks will include it twice.
     * This is intentional and documented — callers (CollisionSystem) treat it
     * as idempotent. This test pins the existing contract so it is never removed
     * silently.
     */
    @Test
    void multiChunkQueryMayContainDuplicateForSpanningTile() {
        SpatialHash hash = new SpatialHash();
        // Tile at exactly the boundary: x=300, width=64 → spans chunk 0 and 1
        TileRect spanning = new TileRect(300, 0, 64, 32, false, TileType.SOLID.id);
        hash.insert(spanning);

        // Query that covers both chunks (entity x=290, width=60 → right edge at 350)
        List<TileRect> cands = hash.candidates(290, 0, 60, 56);

        // Must be found...
        assertThat(cands).contains(spanning);
        // ...and may appear more than once (duplicate contract documented in Javadoc)
        long count = cands.stream().filter(t -> t.equals(spanning)).count();
        assertThat(count).as(
            "Tile spanning a chunk boundary is expected to appear in multiple chunks; "
            + "count=%d. If this fails because deduplication was added, update the test "
            + "and CollisionSystem to match.", count)
            .isGreaterThanOrEqualTo(2);
    }

    // ── Single-chunk fast path — no duplicates ────────────────────────────────

    @Test
    void singleChunkQueryNoDuplicates() {
        SpatialHash hash = new SpatialHash();
        // Tile entirely within chunk 0 (x=0..319)
        TileRect tile = new TileRect(50, 0, 32, 32, false, TileType.SOLID.id);
        hash.insert(tile);

        // Query entirely within chunk 0 — fast path, no ArrayList allocation
        List<TileRect> cands = hash.candidates(40, 0, 28, 56);
        long count = cands.stream().filter(t -> t.equals(tile)).count();
        assertThat(count).as("Single-chunk query must not duplicate a tile").isEqualTo(1);
    }

    // ── Idempotent collision — no double-push ────────────────────────────────

    /**
     * Entity hits a tile that spans two chunks, so CollisionSystem sees it twice
     * in candidates(). The entity must be pushed back exactly once to the wall
     * edge — not twice (which would over-compensate).
     */
    @Test
    void collisionIsIdempotentForMultiChunkTile() {
        SpatialHash hash = new SpatialHash();
        // Solid floor spanning chunk boundary: y=200, width=640 spans chunks 0 and 1
        TileRect floor = new TileRect(0, 200, 640, 32, false, TileType.SOLID.id);
        hash.insert(floor);

        // Entity falling (vy=5) from y=160, bottom=216, 16 px into the floor
        PhysicsState p = new PhysicsState(50, 160, 28, 56);
        p.vy = 5f;

        EventBus bus = new EventBus();
        EntityManager em = new EntityManager(bus);
        em.create(EntityType.PLAYER, p);
        new PhysicsSystem(bus, em.activeEntities());
        new CollisionSystem(bus, em.activeEntities(), hash);

        bus.emit(new TickEvent(PhysicsConstants.FIXED_DT, 0));

        // Entity should land with bottom exactly at floor top (y=144 = 200-56)
        assertThat(p.onGround).isTrue();
        assertThat(p.vy).isCloseTo(0f, within(TOL));
        // Position must be AT the floor, not below (double-push would move it further up)
        assertThat(p.y).isCloseTo(floor.y() - p.height, within(TOL));
        assertThat(p.y).isGreaterThanOrEqualTo(floor.y() - p.height - 1f);
    }

    // ── Four-chunk corner: tile at intersection of 4 chunks ───────────────────

    @Test
    void tileCenteredOnFourChunkCornerIsFoundFromAllFourChunks() {
        SpatialHash hash = new SpatialHash();
        // Tile centred on (320,320) — spans all four quadrants
        TileRect corner = new TileRect(290, 290, 60, 60, false, TileType.SOLID.id);
        hash.insert(corner);

        // Query from top-left chunk quadrant
        assertThat(hash.candidates(270, 270, 28, 56)).contains(corner);
        // Query from top-right chunk quadrant
        assertThat(hash.candidates(330, 270, 28, 56)).contains(corner);
        // Query from bottom-left chunk quadrant
        assertThat(hash.candidates(270, 330, 28, 56)).contains(corner);
        // Query from bottom-right chunk quadrant
        assertThat(hash.candidates(330, 330, 28, 56)).contains(corner);
    }

    // ── remove() cleans all chunk slots ──────────────────────────────────────

    @Test
    void removeCleansBothChunksForSpanningTile() {
        SpatialHash hash = new SpatialHash();
        TileRect spanning = new TileRect(290, 0, 64, 32, false, TileType.SOLID.id);
        hash.insert(spanning);

        hash.remove(spanning);

        // After removal, neither side of the boundary should find the tile
        assertThat(hash.candidates(270, 0, 28, 56)).doesNotContain(spanning);
        assertThat(hash.candidates(330, 0, 28, 56)).doesNotContain(spanning);
    }
}
