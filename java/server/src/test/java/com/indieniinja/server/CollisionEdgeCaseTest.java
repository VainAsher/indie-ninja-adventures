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
import com.indieniinja.world.WorldGenerator;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

/**
 * Collision edge-case tests — swept resolution, one-way platforms, hazard tiles,
 * and SpatialHash.remove() used for runtime puzzle door unlocking.
 *
 * Covers the gaps identified in the Phase 0 audit (java/audit.md):
 *   PHYS-1  swept collision prevents tunnelling at dash speed
 *   PHYS-2  one-way platform blocks from above / passes from below
 *   PHYS-3  water drag caps vy and sets inWater
 *   PHYS-4  lava floor sets onLava
 *   PHYS-5  lava ceiling sets onLava
 *   PHYS-6  SpatialHash.remove() drops tile from candidates
 *   PHYS-7  removed door tile allows entity passthrough
 */
class CollisionEdgeCaseTest {

    private static final float TOL = 0.01f;

    // ── Helpers ───────────────────────────────────────────────────────────────

    /** Build a one-tick simulation: physics + collision, single entity. */
    private record Sim(EventBus bus, PhysicsState p, CollisionSystem cs) {}

    private Sim buildSim(PhysicsState p, SpatialHash hash) {
        EventBus bus = new EventBus();
        EntityManager em = new EntityManager(bus);
        em.create(EntityType.PLAYER, p);
        new PhysicsSystem(bus, em.activeEntities());
        CollisionSystem cs = new CollisionSystem(bus, em.activeEntities(), hash);
        return new Sim(bus, p, cs);
    }

    private void tick(Sim sim, int tickIndex) {
        sim.bus().emit(new TickEvent(PhysicsConstants.FIXED_DT, tickIndex));
    }

    // ── PHYS-1: swept collision prevents tunnelling at dash speed ─────────────

    @Test
    void wallStopsEntityAtDashSpeed() {
        // Entity at x=80, dashing right at vx=16 (DASH_SPEED).
        // Wall tile starts at x=108 — without swept resolution the entity
        // (width=28) would land well inside the wall. Swept sub-steps must
        // resolve the hit and zero vx before it passes through.
        SpatialHash hash = new SpatialHash();
        TileRect wall = new TileRect(108, 195, 32, 70, false);
        hash.insert(wall);

        PhysicsState p = new PhysicsState(80, 200, 28, 56);
        p.vx = PhysicsConstants.DASH_SPEED;  // 16 px/tick → triggers swept path
        Sim sim = buildSim(p, hash);
        tick(sim, 0);

        // Velocity must be zeroed — wall absorbed the dash
        assertThat(p.vx).isCloseTo(0f, within(TOL));
        // Entity must not have tunnelled to the far side of the wall
        assertThat(p.x + p.width).isLessThan(wall.x() + wall.w());
    }

    // ── PHYS-2a: one-way platform blocks from above ───────────────────────────

    @Test
    void onewayPlatformBlocksFromAbove() {
        // Entity falling (vy=10) from above should land on a platform tile.
        // Position y=245 puts bottom at 301 — just 1 px below platform top (300).
        SpatialHash hash = new SpatialHash();
        TileRect platform = new TileRect(50, 300, 200, 32, true);  // isPlatform=true
        hash.insert(platform);

        PhysicsState p = new PhysicsState(100, 245, 28, 56);
        p.vy = 10f;
        Sim sim = buildSim(p, hash);
        tick(sim, 0);

        assertThat(p.onGround).isTrue();
        assertThat(p.vy).isCloseTo(0f, within(TOL));
        assertThat(p.y).isCloseTo(platform.y() - p.height, within(1f));
    }

    // ── PHYS-2b: one-way platform passes from below ───────────────────────────

    @Test
    void onewayPlatformPassthroughFromBelow() {
        // Entity rising fast (vy=-20) through a platform should pass without
        // landing — platforms only resolve when the entity is moving downward.
        SpatialHash hash = new SpatialHash();
        TileRect platform = new TileRect(50, 300, 200, 32, true);
        hash.insert(platform);

        PhysicsState p = new PhysicsState(100, 310, 28, 56);
        p.vy = -20f;
        Sim sim = buildSim(p, hash);
        tick(sim, 0);

        assertThat(p.onGround).isFalse();
        assertThat(p.vy).isLessThan(0f);   // still rising (or at least not zeroed)
    }

    @Test
    void stackedPlatformAboveSolidDoesNotSnapEntityUpward() {
        // Repro case: one-way platform directly above solid terrain.
        // Entity overlapping both tiles should resolve to the solid floor, not pop up
        // onto the one-way platform from below.
        SpatialHash hash = new SpatialHash();
        TileRect platform = new TileRect(50, 288, 220, 32, true);
        TileRect floor = new TileRect(50, 320, 220, 32, false);
        hash.insert(platform);
        hash.insert(floor);

        PhysicsState p = new PhysicsState(100, 262, 28, 56);
        p.vy = 4f;
        Sim sim = buildSim(p, hash);
        tick(sim, 0);

        assertThat(p.onGround).isTrue();
        assertThat(p.y).isCloseTo(floor.y() - p.height, within(1f));
        assertThat(p.y).isGreaterThan(250f);
    }

    // ── PHYS-3: water drag caps vy and sets inWater ───────────────────────────

    @Test
    void waterSetsInWaterFlagAndCapsVy() {
        // Entity inside a water tile with vy=10 (fast fall).
        // Water must: set inWater=true, cap vy to 2.0, and dampen vx.
        SpatialHash hash = new SpatialHash();
        TileRect water = new TileRect(50, 200, 200, 200, false, WorldGenerator.WATER);
        hash.insert(water);

        PhysicsState p = new PhysicsState(100, 250, 28, 56);
        p.vy = 10f;
        p.vx = 5f;
        Sim sim = buildSim(p, hash);
        tick(sim, 0);

        assertThat(p.inWater).isTrue();
        assertThat(p.vy).isLessThanOrEqualTo(2.0f + TOL);
        assertThat(p.vx).isLessThan(5f);   // 0.82 damping applied
    }

    // ── PHYS-4: lava floor sets onLava ────────────────────────────────────────

    @Test
    void lavaFloorSetsOnLavaFlag() {
        // Entity falling onto a lava floor tile.
        // Position y=250 → after 1 tick of gravity falls to ~256, bottom crosses
        // lava tile top at y=310.
        SpatialHash hash = new SpatialHash();
        TileRect lava = new TileRect(50, 310, 200, 32, false, WorldGenerator.LAVA);
        hash.insert(lava);

        PhysicsState p = new PhysicsState(100, 250, 28, 56);
        p.vy = 5f;   // falling toward the lava
        Sim sim = buildSim(p, hash);
        tick(sim, 0);

        assertThat(p.onLava).isTrue();
        assertThat(p.onGround).isTrue();
    }

    // ── PHYS-5: lava ceiling sets onLava ─────────────────────────────────────

    @Test
    void lavaCeilingSetsOnLavaFlag() {
        // Entity jumping upward (vy=-15) into a lava ceiling tile.
        // Lava at y=190–222; entity starts at y=230, rises to ~215 after tick.
        SpatialHash hash = new SpatialHash();
        TileRect lava = new TileRect(50, 190, 200, 32, false, WorldGenerator.LAVA);
        hash.insert(lava);

        PhysicsState p = new PhysicsState(100, 230, 28, 56);
        p.vy = -15f;  // jumping up into lava ceiling
        Sim sim = buildSim(p, hash);
        tick(sim, 0);

        assertThat(p.onLava).isTrue();
    }

    // ── PHYS-6: SpatialHash.remove() drops tile from candidates ──────────────

    @Test
    void spatialHashRemoveExcludesTile() {
        // Direct unit test for SpatialHash.remove() — the primitive used when a
        // puzzle door is unlocked at runtime.
        SpatialHash hash = new SpatialHash();
        TileRect tile = new TileRect(100, 100, 32, 32, false);
        hash.insert(tile);

        assertThat(hash.candidates(100, 100, 32, 32)).contains(tile);

        hash.remove(tile);

        assertThat(hash.candidates(100, 100, 32, 32)).doesNotContain(tile);
    }

    // ── PHYS-7: removed door tile allows entity passthrough ───────────────────

    @Test
    void removedDoorTileAllowsEntityPassthrough() {
        // Two-tick integration test for puzzle door unlock:
        //   Tick 0: solid floor present → entity lands (onGround=true)
        //   Tick 1: floor removed from hash → entity falls through (onGround=false)
        SpatialHash hash = new SpatialHash();
        TileRect floor = new TileRect(50, 310, 200, 32, false);
        hash.insert(floor);

        PhysicsState p = new PhysicsState(100, 250, 28, 56);
        p.vy = 5f;
        Sim sim = buildSim(p, hash);

        tick(sim, 0);
        assertThat(p.onGround).isTrue();

        // Simulate door unlock: remove tile and hot-swap hash into collision system
        hash.remove(floor);
        sim.cs().setSpatialHash(hash);

        // Reset entity to fall again
        p.vy = 5f;

        tick(sim, 1);
        assertThat(p.onGround).isFalse();
    }
}
