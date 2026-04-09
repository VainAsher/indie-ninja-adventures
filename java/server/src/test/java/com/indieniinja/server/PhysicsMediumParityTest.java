package com.indieniinja.server;

import com.indieniinja.core.EntityManager;
import com.indieniinja.core.EntityType;
import com.indieniinja.core.EventBus;
import com.indieniinja.core.TickEvent;
import com.indieniinja.physics.*;
import org.junit.jupiter.api.Test;

import java.util.Collections;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

/**
 * Regression tests for physics medium effects, ability gating, GAS tile,
 * swept collision, and SpatialHash.raycast.
 *
 * Covers audit gaps: water drag parity, ice friction gating, gas drag,
 * swept non-tunnel, raycast hit/miss.
 */
class PhysicsMediumParityTest {

    private static final float TOL = 0.001f;

    // ── Helpers ───────────────────────────────────────────────────────────────

    /**
     * Build a SpatialHash with one tile, a CollisionSystem, run N ticks.
     * Entity starts at (startX, startY) with given initial velocity.
     */
    private PhysicsState collide(float startX, float startY,
                                 float vx, float vy,
                                 TileRect tile, int ticks) {
        return collide(startX, startY, vx, vy, tile, ticks, 0);
    }

    private PhysicsState collide(float startX, float startY,
                                 float vx, float vy,
                                 TileRect tile, int ticks, int abilityFlags) {
        EventBus bus = new EventBus();
        SpatialHash hash = new SpatialHash();
        hash.insert(tile);

        PhysicsState p = new PhysicsState(startX, startY, 28, 56);
        p.vx = vx;
        p.vy = vy;
        p.abilityFlags = abilityFlags;

        EntityManager em = new EntityManager(bus);
        em.create(EntityType.PLAYER, p);
        new PhysicsSystem(bus, em.activeEntities());
        new CollisionSystem(bus, em.activeEntities(), hash);

        for (int i = 0; i < ticks; i++) {
            bus.emit(new TickEvent(PhysicsConstants.FIXED_DT, i));
        }
        return p;
    }

    // ── Water drag parity ─────────────────────────────────────────────────────

    @Test
    void waterDampsVelocityAndCapsVy() {
        // WATER tile 100×100 at (0,0) — entity starts inside it
        TileRect water = new TileRect(0, 0, 200, 200, false, TileType.WATER.id);
        PhysicsState p = collide(10, 10, 6f, 0f, water, 5);

        assertThat(p.inWater).isTrue();
        // After 5 ticks of 0.82 vx multiplier: 6 * 0.82^5 ≈ 2.25
        assertThat(Math.abs(p.vx)).isLessThan(Math.abs(6f));
        // vy must not exceed 2.0 (water fall cap)
        assertThat(p.vy).isLessThanOrEqualTo(2.0f + TOL);
    }

    @Test
    void waterDragSkippedWithWaterWalkAbility() {
        TileRect water = new TileRect(0, 0, 200, 200, false, TileType.WATER.id);
        // With WATER_WALK ability, drag must NOT be applied
        PhysicsState p = collide(10, 10, 6f, 0f, water, 1, PhysicsConstants.ABILITY_WATER_WALK);

        assertThat(p.inWater).isTrue();   // flag still set (entity is in water)
        // vx should be ≈ 6.0 (no drag applied in this tick; gravity integration only)
        assertThat(Math.abs(p.vx)).isCloseTo(6f, within(TOL));
        // vy must exceed 2.0 (no fall cap applied)
        assertThat(p.vy).isGreaterThan(2.0f);
    }

    // ── Ice friction gating ───────────────────────────────────────────────────

    @Test
    void iceSetsFlagWhenNoAbility() {
        // ICE tile acting as floor; entity descends onto it
        TileRect ice = new TileRect(0, 200, 200, 32, false, TileType.ICE.id);
        PhysicsState p = collide(10, 100, 0f, 5f, ice, 5);

        assertThat(p.onGround).isTrue();
        assertThat(p.onIce).isTrue();
    }

    @Test
    void iceFlagSuppressedWithIceGripAbility() {
        TileRect ice = new TileRect(0, 200, 200, 32, false, TileType.ICE.id);
        PhysicsState p = collide(10, 100, 0f, 5f, ice, 5, PhysicsConstants.ABILITY_ICE_GRIP);

        assertThat(p.onGround).isTrue();
        assertThat(p.onIce).isFalse();   // ability suppresses the flag
    }

    // ── GAS tile drag ─────────────────────────────────────────────────────────

    @Test
    void gasDampsVelocity() {
        TileRect gas = new TileRect(0, 0, 200, 200, false, TileType.GAS.id);
        PhysicsState p = collide(10, 10, 4f, 0f, gas, 5);

        assertThat(p.inGas).isTrue();
        // vx < initial after 5 ticks of GAS_DRAG
        assertThat(Math.abs(p.vx)).isLessThan(4f);
        // GAS does NOT cap vy — fall speed can exceed 2.0
        assertThat(p.vy).isGreaterThan(2.0f);
    }

    @Test
    void gasDragSkippedWithGasResistAbility() {
        TileRect gas = new TileRect(0, 0, 200, 200, false, TileType.GAS.id);
        PhysicsState p = collide(10, 10, 4f, 0f, gas, 1, PhysicsConstants.ABILITY_GAS_RESIST);

        assertThat(p.inGas).isTrue();
        assertThat(Math.abs(p.vx)).isCloseTo(4f, within(TOL));
    }

    // ── Swept collision non-tunnel ────────────────────────────────────────────

    @Test
    void sweptCollisionPreventsWallTunnel() {
        // Thin wall (2 px wide) at x=100; entity at x=60 dashes at 16 px/tick rightward.
        // Without swept sub-stepping the entity would skip past the wall entirely.
        TileRect wall = new TileRect(100, 0, 2, 200, false, TileType.SOLID.id);

        EventBus bus = new EventBus();
        SpatialHash hash = new SpatialHash();
        hash.insert(wall);

        PhysicsState p = new PhysicsState(60, 50, 28, 56);
        p.vx = PhysicsConstants.DASH_SPEED; // 16 px/tick — triggers swept path
        p.vy = 0;

        EntityManager em = new EntityManager(bus);
        em.create(EntityType.PLAYER, p);
        new PhysicsSystem(bus, em.activeEntities());
        new CollisionSystem(bus, em.activeEntities(), hash);

        bus.emit(new TickEvent(PhysicsConstants.FIXED_DT, 0));

        // Entity must be stopped at or before the wall's left edge — not through it
        assertThat(p.x + p.width).isLessThanOrEqualTo(wall.x() + TOL);
        assertThat(p.onWall).isTrue();
        assertThat(p.vx).isCloseTo(0f, within(TOL));
    }

    // ── SpatialHash raycast ───────────────────────────────────────────────────

    @Test
    void raycastHitsSolidTile() {
        SpatialHash hash = new SpatialHash();
        TileRect wall = new TileRect(200, 0, 32, 200, false, TileType.SOLID.id);
        hash.insert(wall);

        // Ray from x=0 to x=400 at y=50 — must hit wall
        TileRect hit = hash.raycast(0, 50, 400, 50);
        assertThat(hit).isNotNull();
        assertThat(hit).isEqualTo(wall);
    }

    @Test
    void raycastMissesWhenNoTile() {
        SpatialHash hash = new SpatialHash();
        TileRect wall = new TileRect(200, 0, 32, 200, false, TileType.SOLID.id);
        hash.insert(wall);

        // Ray below the wall — y=250 doesn't intersect y-range [0,200]
        TileRect hit = hash.raycast(0, 250, 400, 250);
        assertThat(hit).isNull();
    }

    @Test
    void raycastPassesThroughWater() {
        SpatialHash hash = new SpatialHash();
        TileRect water = new TileRect(100, 0, 50, 200, false, TileType.WATER.id);
        TileRect solid = new TileRect(300, 0, 32, 200, false, TileType.SOLID.id);
        hash.insert(water);
        hash.insert(solid);

        // Ray passes through WATER and continues to hit the SOLID behind it
        TileRect hit = hash.raycast(0, 50, 500, 50);
        assertThat(hit).isNotNull();
        assertThat(hit).isEqualTo(solid);
    }

    @Test
    void raycastReturnsMissForEmptyHash() {
        SpatialHash hash = new SpatialHash();
        assertThat(hash.raycast(0, 0, 1000, 1000)).isNull();
    }

    @Test
    void raycastHitsDynamicTile() {
        SpatialHash hash = new SpatialHash();
        TileRect platform = new TileRect(150, 100, 64, 16, false, TileType.SOLID.id);
        hash.setDynamicTiles(Collections.singletonList(platform));

        TileRect hit = hash.raycast(150, 0, 150, 300);
        assertThat(hit).isNotNull();
        assertThat(hit).isEqualTo(platform);
    }
}
