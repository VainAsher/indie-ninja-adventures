package com.indieniinja.server;

import com.indieniinja.core.EntityManager;
import com.indieniinja.core.EntityType;
import com.indieniinja.core.EventBus;
import com.indieniinja.core.TickEvent;
import com.indieniinja.physics.PhysicsConstants;
import com.indieniinja.physics.PhysicsState;
import com.indieniinja.physics.PhysicsSystem;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

/**
 * Physics parity tests — verifies Java physics matches Python physics_system.py.
 *
 * Reference values computed from Python with same initial conditions.
 * Tolerance: 0.001f (accounts for float vs double intermediate precision).
 */
class PhysicsParityTest {

    private static final float TOL = 0.001f;

    /** Run N ticks of physics on a single entity, return final state. */
    private PhysicsState simulate(float startVy, boolean onGround, int ticks) {
        EventBus bus = new EventBus();
        PhysicsState p = new PhysicsState(0, 0, 28, 56);
        p.vy = startVy;
        p.onGround = onGround;

        EntityManager em = new EntityManager(bus);
        em.create(EntityType.PLAYER, p);
        new PhysicsSystem(bus, em.activeEntities());

        for (int i = 0; i < ticks; i++) {
            bus.emit(new TickEvent(PhysicsConstants.FIXED_DT, i));
        }
        return p;
    }

    @Test
    void freefallFromRest_1tick() {
        // Python reference: vy starts 0, after 1 tick:
        //   vy += GRAVITY (0.4) → vy = 0.4
        //   (vy > 0) → vy += 0.4 * (1.5 - 1.0) = 0.2 → vy = 0.6
        // y += 0.6 → y = 0.6
        PhysicsState p = simulate(0f, false, 1);
        assertThat(p.vy).isCloseTo(0.6f, within(TOL));
        assertThat(p.y).isCloseTo(0.6f, within(TOL));
    }

    @Test
    void freefallFromRest_10ticks() {
        // After 10 ticks of freefall gravity should approach terminal velocity
        PhysicsState p = simulate(0f, false, 10);
        assertThat(p.vy).isGreaterThan(0f)
                        .isLessThanOrEqualTo(PhysicsConstants.MAX_FALL_SPEED);
    }

    @Test
    void terminalVelocityNotExceeded() {
        // Start near terminal velocity — should be capped at MAX_FALL_SPEED
        PhysicsState p = simulate(11.5f, false, 5);
        assertThat(p.vy).isLessThanOrEqualTo(PhysicsConstants.MAX_FALL_SPEED + TOL);
    }

    @Test
    void onGroundSkipsGravity() {
        // Entity on ground — gravity must NOT be applied, vy stays 0
        PhysicsState p = simulate(0f, true, 10);
        assertThat(p.vy).isCloseTo(0f, within(TOL));
    }

    @Test
    void jumpCutAppliesExtraGravity() {
        EventBus bus = new EventBus();
        PhysicsState p = new PhysicsState(0, 0, 28, 56);
        p.vy = -8f;  // rising
        p.jumpCutActive = true;

        EntityManager em = new EntityManager(bus);
        em.create(EntityType.PLAYER, p);
        new PhysicsSystem(bus, em.activeEntities());
        bus.emit(new TickEvent(PhysicsConstants.FIXED_DT, 0));

        // Expected: vy += 0.4 (base) + 0.4*(3.0-1.0) = 0.4 + 0.8 = 1.2 added
        // Python: vy = -8 + 0.4 + 0.4*(3-1) = -8 + 1.2 = -6.8
        assertThat(p.vy).isCloseTo(-6.8f, within(TOL));
    }

    @Test
    void constantsMatchPython() {
        // Regression: constants must never silently drift from Python values
        assertThat(PhysicsConstants.GRAVITY).isEqualTo(0.4f);
        assertThat(PhysicsConstants.MAX_FALL_SPEED).isEqualTo(12.0f);
        assertThat(PhysicsConstants.JUMP_POWER).isEqualTo(14.5f);
        assertThat(PhysicsConstants.DASH_SPEED).isEqualTo(16.0f);
        assertThat(PhysicsConstants.TILE_SIZE).isEqualTo(32);
        assertThat(PhysicsConstants.PLAYER_WIDTH).isEqualTo(28);
        assertThat(PhysicsConstants.PLAYER_HEIGHT).isEqualTo(56);
        assertThat(PhysicsConstants.FIXED_DT).isCloseTo(1f / 60f, within(1e-7f));
    }
}
