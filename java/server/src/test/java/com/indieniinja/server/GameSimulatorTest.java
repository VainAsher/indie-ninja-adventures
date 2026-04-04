package com.indieniinja.server;

import com.indieniinja.network.InputCommand;
import com.indieniinja.network.WorldSnapshot;
import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.sim.SimPlayer;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

/**
 * GameSimulator smoke tests — Phase B.
 *
 * Verifies that the Java sim initialises, runs without exceptions for 1000 ticks,
 * produces valid snapshots, and that entity counts are as expected from the
 * test layout used by LevelLayout.buildTestLayout().
 */
class GameSimulatorTest {

    private static GameSimulator buildSim(long seed) {
        LevelLayout layout = LevelLayout.buildTestLayout(seed);
        return new GameSimulator(seed, "test_hub", layout);
    }

    // ── Smoke: builds without exception ──────────────────────────────────────

    @Test
    void constructsWithTestLayout() {
        GameSimulator sim = buildSim(42L);
        assertThat(sim).isNotNull();
        assertThat(sim.getEnemies()).isNotEmpty();
        assertThat(sim.getPickups()).isNotEmpty();
    }

    // ── Step: 1 tick with no players doesn't throw ────────────────────────────

    @Test
    void stepWithNoPlayersIsNoop() {
        GameSimulator sim = buildSim(42L);
        // Should not throw — enemy AI short-circuits when no alive players
        sim.step(Map.of());
        sim.step(Map.of());
    }

    // ── Step: 1000 ticks — deterministic, no exceptions ───────────────────────

    @Test
    void thousandTicksDeterministic() {
        // Run the same seed twice and verify snapshots match at tick 1000
        GameSimulator simA = buildSim(99L);
        GameSimulator simB = buildSim(99L);

        SimPlayer playerA = new SimPlayer("p1", 0, 200f, 800f);
        SimPlayer playerB = new SimPlayer("p1", 0, 200f, 800f);
        simA.addPlayer(playerA);
        simB.addPlayer(playerB);

        InputCommand moveRight = new InputCommand(0);
        moveRight.right = true;

        for (int i = 0; i < 1000; i++) {
            simA.step(Map.of(0, moveRight));
            simB.step(Map.of(0, moveRight));
        }

        WorldSnapshot snapA = simA.getSnapshot(1000);
        WorldSnapshot snapB = simB.getSnapshot(1000);

        // Same seed → same enemy count
        assertThat(snapA.enemies.size()).isEqualTo(snapB.enemies.size());
        // Both had the same input → same player health
        assertThat(snapA.players.get(0).health).isEqualTo(snapB.players.get(0).health);
    }

    // ── Snapshot: player state round-trips correctly ──────────────────────────

    @Test
    void snapshotContainsPlayerState() {
        GameSimulator sim = buildSim(42L);
        SimPlayer p = new SimPlayer("player-uuid", 0, 300f, 700f);
        sim.addPlayer(p);

        sim.step(Map.of());
        WorldSnapshot snap = sim.getSnapshot(1);

        assertThat(snap.players).hasSize(1);
        assertThat(snap.players.get(0).playerId).isEqualTo("player-uuid");
        assertThat(snap.players.get(0).slot).isEqualTo(0);
        assertThat(snap.players.get(0).posX).isCloseTo(300f, within(1f));
    }

    // ── Snapshot: enemies present in full snapshot ────────────────────────────

    @Test
    void snapshotContainsEnemies() {
        GameSimulator sim = buildSim(42L);
        WorldSnapshot snap = sim.getSnapshot(0);
        // Test layout spawns 4 enemies
        assertThat(snap.enemies).hasSize(4);
        // Enemy IDs are set
        snap.enemies.forEach(e -> assertThat(e.enemyId).isNotBlank());
    }

    // ── Snapshot: hub ID propagated ───────────────────────────────────────────

    @Test
    void snapshotHubIdIsCorrect() {
        GameSimulator sim = buildSim(1L);
        assertThat(sim.getSnapshot(0).hubId).isEqualTo("test_hub");
    }

    // ── Platform state machine: starts idle ───────────────────────────────────

    @Test
    void platformsStartIdle() {
        GameSimulator sim = buildSim(42L);
        WorldSnapshot snap = sim.getSnapshot(0);
        // Test layout has 2 falling platforms
        assertThat(snap.platformStates).hasSize(2);
        snap.platformStates.forEach(ps ->
            assertThat(ps.state).isEqualTo("idle")
        );
    }

    // ── Pickup: alive=true before collection ─────────────────────────────────

    @Test
    void pickupsAliveAtStart() {
        GameSimulator sim = buildSim(42L);
        WorldSnapshot snap = sim.getSnapshot(0);
        assertThat(snap.pickups).isNotEmpty();
        snap.pickups.forEach(p -> assertThat(p.alive).isTrue());
    }

    // ── Physics constant parity guard ─────────────────────────────────────────

    @Test
    void physicsConstantsParity() {
        // Guard: if these fail, someone changed a constant without updating Python
        assertThat(com.indieniinja.physics.PhysicsConstants.GRAVITY).isEqualTo(0.4f);
        assertThat(com.indieniinja.physics.PhysicsConstants.MAX_FALL_SPEED).isEqualTo(12.0f);
        assertThat(com.indieniinja.physics.PhysicsConstants.DASH_SPEED).isEqualTo(16.0f);
        assertThat(com.indieniinja.physics.PhysicsConstants.PLAYER_WIDTH).isEqualTo(28);
        assertThat(com.indieniinja.physics.PhysicsConstants.PLAYER_HEIGHT).isEqualTo(56);
    }
}
