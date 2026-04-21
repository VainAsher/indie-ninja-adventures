package com.indieniinja.server;

import com.indieniinja.network.InputCommand;
import com.indieniinja.network.WorldSnapshot;
import com.indieniinja.sim.EnemyAIState;
import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.sim.SimEnemy;
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

    @Test
    void stanceSwitchInputBiasesYinYangTowardToggledStance() {
        GameSimulator sim = buildSim(321L);
        SimPlayer player = new SimPlayer("p1", 0, 200f, 800f);
        sim.addPlayer(player);

        InputCommand toggle = new InputCommand(0);
        toggle.stanceSwitch = true;
        sim.step(Map.of(0, toggle)); // default yin -> yang

        for (int i = 0; i < 60; i++) sim.step(Map.of());

        WorldSnapshot snap = sim.getSnapshot(61);
        assertThat(snap.players).hasSize(1);
        assertThat(snap.players.get(0).yangValue).isGreaterThan(snap.players.get(0).yinValue);
    }

    @Test
    void weaponHotSwapInputPersistsAcrossYangTicks() {
        GameSimulator sim = buildSim(541L);
        SimPlayer player = new SimPlayer("p1", 0, 200f, 800f);
        player.stanceMode = "yang";
        sim.addPlayer(player);

        sim.step(Map.of(0, new InputCommand(0)));
        assertThat(player.weaponState).isEqualTo("sword");

        InputCommand selectUnarmed = new InputCommand(1);
        selectUnarmed.selectWeapon1 = true;
        sim.step(Map.of(0, selectUnarmed));
        assertThat(player.weaponState).isEqualTo("unarmed");

        sim.step(Map.of(0, new InputCommand(2)));
        assertThat(player.weaponState).isEqualTo("unarmed");

        InputCommand selectArmed = new InputCommand(3);
        selectArmed.selectWeapon2 = true;
        sim.step(Map.of(0, selectArmed));
        assertThat(player.weaponState).isEqualTo("sword");
    }

    @Test
    void yinStanceStillForcesUnarmedUntilStanceSwitchBackToYang() {
        GameSimulator sim = buildSim(542L);
        SimPlayer player = new SimPlayer("p1", 0, 200f, 800f);
        player.stanceMode = "yin";
        sim.addPlayer(player);

        InputCommand selectArmed = new InputCommand(0);
        selectArmed.selectWeapon2 = true;
        sim.step(Map.of(0, selectArmed));
        assertThat(player.weaponState).isEqualTo("unarmed");

        InputCommand toggleToYang = new InputCommand(1);
        toggleToYang.stanceSwitch = true;
        sim.step(Map.of(0, toggleToYang));
        assertThat(player.stanceMode).isEqualTo("yang");
        assertThat(player.weaponState).isEqualTo("sword");
    }

    @Test
    void guardParryBlocksFrontMeleeAndStunsAttacker() {
        GameSimulator sim = buildSim(777L);
        SimPlayer player = new SimPlayer("p1", 0, 300f, 900f);
        player.facing = -1; // block toward the attacker on the left
        sim.addPlayer(player);

        SimEnemy attacker = configureSingleMeleeAttacker(sim, 260f, 900f, true);

        InputCommand holdBlock = new InputCommand(0);
        holdBlock.block = true;
        sim.step(Map.of(0, holdBlock));

        assertThat(player.health).isEqualTo(player.maxHealth);
        assertThat(attacker.aiState).isEqualTo(EnemyAIState.STUNNED);
    }

    @Test
    void noBlockTakesFrontMeleeDamage() {
        GameSimulator sim = buildSim(778L);
        SimPlayer player = new SimPlayer("p1", 0, 300f, 900f);
        player.facing = -1;
        sim.addPlayer(player);

        configureSingleMeleeAttacker(sim, 260f, 900f, true);
        sim.step(Map.of(0, new InputCommand(0)));

        assertThat(player.health).isLessThan(player.maxHealth);
    }

    @Test
    void climbOnlyActivatesOnClimbableTaggedWalls() {
        LevelLayout fixture = LevelLayout.buildTraversalLedgeFixtureLayout(880L);

        GameSimulator solidWallSim = new GameSimulator(880L, "test_hub", fixture);
        SimPlayer solidWallPlayer = new SimPlayer("p_solid", 0, 14 * 32f - 28f, 18 * 32f);
        solidWallPlayer.stanceMode = "yin";
        solidWallSim.addPlayer(solidWallPlayer);
        InputCommand intoWall = new InputCommand(0);
        intoWall.right = true;
        solidWallSim.step(Map.of(0, intoWall)); // establish onWall from collision
        InputCommand climbAttempt = new InputCommand(1);
        climbAttempt.right = true;
        solidWallSim.step(Map.of(0, climbAttempt));
        assertThat(solidWallPlayer.isClimbing).isFalse();

        GameSimulator climbableWallSim = new GameSimulator(881L, "test_hub", fixture);
        SimPlayer climbableWallPlayer = new SimPlayer("p_climbable", 0, 20 * 32f - 28f, 18 * 32f);
        climbableWallPlayer.stanceMode = "yin";
        climbableWallSim.addPlayer(climbableWallPlayer);
        InputCommand intoClimbable = new InputCommand(0);
        intoClimbable.right = true;
        climbableWallSim.step(Map.of(0, intoClimbable)); // establish onWall from collision
        InputCommand climbOnTag = new InputCommand(1);
        climbOnTag.right = true;
        climbableWallSim.step(Map.of(0, climbOnTag));
        assertThat(climbableWallPlayer.isClimbing).isTrue();
    }

    @Test
    void yangWallContactSlidesInsteadOfClimbing() {
        LevelLayout fixture = LevelLayout.buildTraversalLedgeFixtureLayout(884L);
        GameSimulator sim = new GameSimulator(884L, "test_hub", fixture);
        SimPlayer player = new SimPlayer("p_yang", 0, 20 * 32f - 28f, 18 * 32f);
        player.stanceMode = "yang";
        sim.addPlayer(player);

        InputCommand intoWall = new InputCommand(0);
        intoWall.right = true;
        sim.step(Map.of(0, intoWall)); // establish wall contact

        InputCommand holdWall = new InputCommand(1);
        holdWall.right = true;
        sim.step(Map.of(0, holdWall));

        assertThat(player.isClimbing).isFalse();
        assertThat(player.isWallSliding).isTrue();
    }

    @Test
    void ledgeGrabTransitionsIntoLedgeClimbAndTopOut() {
        LevelLayout fixture = LevelLayout.buildTraversalLedgeFixtureLayout(882L);
        GameSimulator sim = new GameSimulator(882L, "test_hub", fixture);
        SimPlayer player = new SimPlayer("p1", 0, 30 * 32f - 28f, 18 * 32f + 10f);
        sim.addPlayer(player);

        InputCommand grab = new InputCommand(0);
        grab.up = true;
        sim.step(Map.of(0, grab));
        assertThat(player.isOnLedge).isTrue();

        InputCommand climb = new InputCommand(1);
        climb.up = true;
        sim.step(Map.of(0, climb));
        assertThat(player.isLedgeClimbing).isTrue();

        for (int i = 0; i < 20; i++) {
            sim.step(Map.of(0, new InputCommand(2 + i)));
        }

        assertThat(player.isOnLedge).isFalse();
        assertThat(player.isLedgeClimbing).isFalse();
        assertThat(player.physics.onGround).isTrue();
    }

    @Test
    void waterExitSnapsPlayerToSolidBank() {
        LevelLayout fixture = LevelLayout.buildWaterExitFixtureLayout(883L);
        GameSimulator sim = new GameSimulator(883L, "test_hub", fixture);
        SimPlayer player = new SimPlayer("p1", 0, fixture.spawnX, fixture.spawnY);
        sim.addPlayer(player);

        sim.step(Map.of(0, new InputCommand(0))); // allow collision pass to set inWater flag
        assertThat(player.physics.inWater).isTrue();

        InputCommand exit = new InputCommand(1);
        exit.right = true;
        exit.jump = true;
        sim.step(Map.of(0, exit));

        float expectedExitX = 24 * 32f - 28f + 2f;
        assertThat(player.physics.x).isGreaterThanOrEqualTo(expectedExitX - 2f);
        assertThat(player.physics.y).isLessThan(fixture.spawnY);
    }

    @Test
    void waterSurfaceJumpBurstWorksWithoutBankExit() {
        LevelLayout fixture = LevelLayout.buildWaterSurfaceFixtureLayout(885L);
        GameSimulator sim = new GameSimulator(885L, "test_hub", fixture);
        SimPlayer player = new SimPlayer("p1", 0, fixture.spawnX, fixture.spawnY);
        sim.addPlayer(player);

        sim.step(Map.of(0, new InputCommand(0))); // establish inWater
        sim.step(Map.of(0, new InputCommand(1))); // compute atWaterSurface from previous inWater tick
        assertThat(player.physics.inWater).isTrue();
        assertThat(player.atWaterSurface).isTrue();

        player.physics.y = 19 * 32f - 20f;
        float yBeforeJump = player.physics.y;
        InputCommand jump = new InputCommand(2);
        jump.jump = true;
        sim.step(Map.of(0, jump));

        assertThat(player.physics.vy).isLessThan(0f);
        assertThat(player.physics.y).isLessThanOrEqualTo(yBeforeJump);
        assertThat(player.physics.onGround).isFalse();
        assertThat(player.jumpCount).isGreaterThanOrEqualTo(1);
    }

    @Test
    void blockedWaterExitFallsBackToSurfaceJump() {
        LevelLayout fixture = LevelLayout.buildBlockedWaterExitFixtureLayout(886L);
        GameSimulator sim = new GameSimulator(886L, "test_hub", fixture);
        SimPlayer player = new SimPlayer("p1", 0, fixture.spawnX, fixture.spawnY);
        // Shift player near the water surface so fallback jump path is valid.
        player.physics.y = 20 * 32f - 20f;
        sim.addPlayer(player);

        sim.step(Map.of(0, new InputCommand(0))); // establish inWater
        sim.step(Map.of(0, new InputCommand(1))); // compute atWaterSurface
        assertThat(player.physics.inWater).isTrue();
        assertThat(player.atWaterSurface).isTrue();

        player.physics.y = 20 * 32f - 20f;
        float xBefore = player.physics.x;
        float yBefore = player.physics.y;
        InputCommand exitAttempt = new InputCommand(2);
        exitAttempt.right = true;
        exitAttempt.jump = true;
        sim.step(Map.of(0, exitAttempt));

        // Should not snap to bank top-out due blocked headroom.
        float bankSnapX = 24 * 32f - 28f + 2f;
        assertThat(Math.abs(player.physics.x - bankSnapX)).isGreaterThan(1.0f);
        // Bank-blocked attempt may burst upward or remain in-water, but should not
        // advance into a deeper/farther invalid placement.
        assertThat(player.physics.y).isLessThanOrEqualTo(yBefore + 32f);
        assertThat(player.physics.x).isGreaterThanOrEqualTo(xBefore - 2f);
    }

    @Test
    void leverInteractionQueuesLeverAnimationFeedback() {
        LevelLayout fixture = LevelLayout.buildInteractionMarkerFixtureLayout(887L, "lever_fx_0");
        GameSimulator sim = new GameSimulator(887L, "test_hub", fixture);
        SimPlayer player = new SimPlayer("p1", 0, fixture.spawnX, fixture.spawnY);
        sim.addPlayer(player);

        InputCommand interact = new InputCommand(0);
        interact.interact = true;
        sim.step(Map.of(0, interact));

        assertThat(player.interactionState).isEqualTo("lever");
        assertThat(player.interactionTimer).isGreaterThan(0f);
        assertThat(player.animState).isEqualTo("lever");

        for (int i = 0; i < 60; i++) {
            sim.step(Map.of(0, new InputCommand(1 + i)));
        }
        assertThat(player.interactionState).isBlank();
        assertThat(player.interactionTimer).isEqualTo(0f);
    }

    @Test
    void buttonInteractionQueuesButtonAnimationFeedback() {
        LevelLayout fixture = LevelLayout.buildInteractionMarkerFixtureLayout(888L, "btn_0_fx_0");
        GameSimulator sim = new GameSimulator(888L, "test_hub", fixture);
        SimPlayer player = new SimPlayer("p1", 0, fixture.spawnX, fixture.spawnY);
        sim.addPlayer(player);

        InputCommand interact = new InputCommand(0);
        interact.interact = true;
        sim.step(Map.of(0, interact));

        assertThat(player.interactionState).isEqualTo("button");
        assertThat(player.interactionTimer).isGreaterThan(0f);
        assertThat(player.animState).isEqualTo("button");
    }

    @Test
    void stanceSwitchHeldAcrossTicksOnlyTogglesOncePerPress() {
        LevelLayout fixture = LevelLayout.buildTestLayout(890L);
        GameSimulator sim = new GameSimulator(890L, "test_hub", fixture);
        SimPlayer player = new SimPlayer("p1", 0, fixture.spawnX, fixture.spawnY);
        sim.addPlayer(player);

        assertThat(player.stanceMode).isEqualTo("yin");

        InputCommand pressAndHold = new InputCommand(0);
        pressAndHold.stanceSwitch = true;

        sim.step(Map.of(0, pressAndHold));
        assertThat(player.stanceMode).isEqualTo("yang");

        // Same held command on the next tick must not bounce back to yin.
        sim.step(Map.of(0, pressAndHold));
        assertThat(player.stanceMode).isEqualTo("yang");

        InputCommand release = new InputCommand(1);
        sim.step(Map.of(0, release));

        InputCommand secondPress = new InputCommand(2);
        secondPress.stanceSwitch = true;
        sim.step(Map.of(0, secondPress));
        assertThat(player.stanceMode).isEqualTo("yin");
    }

    @Test
    void echoTriggerInteractionSpawnsEchoAndQueuesFeedback() {
        LevelLayout fixture = LevelLayout.buildInteractionMarkerFixtureLayout(889L, "echo_trigger_fx_0");
        GameSimulator sim = new GameSimulator(889L, "test_hub", fixture);
        SimPlayer player = new SimPlayer("p1", 0, fixture.spawnX, fixture.spawnY);
        sim.addPlayer(player);

        InputCommand interact = new InputCommand(0);
        interact.interact = true;
        sim.step(Map.of(0, interact));

        assertThat(player.interactionState).isEqualTo("button");
        assertThat(player.interactionTimer).isGreaterThan(0f);
        assertThat(sim.getEchoes()).hasSize(1);
        assertThat(sim.getEchoes().get(0).echoId).contains("test_hub_echo_");
        assertThat(sim.getEchoes().get(0).ticksPlayed()).isEqualTo(0);

        sim.step(Map.of(0, new InputCommand(1)));
        assertThat(sim.getEchoes().get(0).ticksPlayed()).isEqualTo(1);
    }

    @Test
    void timeLeechLordSpawnsTypedCappedMinions() {
        long seed = findBossSeed("time_leech_lord");
        LevelLayout layout = LevelLayout.buildProceduralLayout(
            seed, java.util.Collections.emptySet(), "boss", "test_hub");
        GameSimulator sim = new GameSimulator(seed, "test_hub", layout);

        SimPlayer player = new SimPlayer("p1", 0, layout.spawnX + 120f, layout.spawnY);
        sim.addPlayer(player);

        // > 5 spawn windows at 8s each
        for (int i = 0; i < 3200; i++) {
            sim.step(Map.of(0, new InputCommand(i)));
        }

        long activeLeeches = sim.getEnemies().stream()
            .filter(SimEnemy::isAlive)
            .filter(e -> "time_leech".equals(e.enemyType))
            .count();
        long mistypedLeeches = sim.getEnemies().stream()
            .filter(e -> e.enemyId.contains("_tl_"))
            .filter(e -> "slime".equals(e.enemyType))
            .count();

        assertThat(activeLeeches).isLessThanOrEqualTo(5);
        assertThat(mistypedLeeches).isZero();
    }

    private static SimEnemy configureSingleMeleeAttacker(GameSimulator sim, float x, float y, boolean facingRight) {
        SimEnemy attacker = sim.getEnemies().get(0);
        for (SimEnemy en : sim.getEnemies()) {
            en.removed = true;
            en.hp = 0;
            en.aiState = EnemyAIState.DEAD;
        }
        attacker.removed = false;
        attacker.hp = attacker.maxHp;
        attacker.physics.x = x;
        attacker.physics.y = y;
        attacker.facingRight = facingRight;
        attacker.aiState = EnemyAIState.ATTACK;
        attacker.attackWindupTimer = 0f;
        attacker.attackActiveTimer = SimEnemy.ATTACK_ACTIVE_TIME * 0.5f;
        attacker.attackRecoveryTimer = 0f;
        return attacker;
    }

    private static long findBossSeed(String bossWire) {
        for (long seed = 0; seed < 1024; seed++) {
            LevelLayout layout = LevelLayout.buildProceduralLayout(
                seed, java.util.Collections.emptySet(), "boss", "test_hub");
            if (layout.bossSpawn != null && bossWire.equals(layout.bossSpawn.bossTypeWire())) {
                return seed;
            }
        }
        throw new AssertionError("No seed found for boss type: " + bossWire);
    }
}
