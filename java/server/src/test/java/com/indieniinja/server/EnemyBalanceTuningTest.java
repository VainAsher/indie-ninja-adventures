package com.indieniinja.server;

import com.indieniinja.network.WorldSnapshot;
import com.indieniinja.sim.EnemyAttackGeometry;
import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.sim.SimEnemy;
import com.indieniinja.sim.SimPlayer;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

class EnemyBalanceTuningTest {

    @Test
    void slimeAttackExtendsOneBodyLengthInFront() {
        float bodyX = 100f;
        float bodyY = 200f;
        float bodyW = 40f;
        float bodyH = 32f;

        EnemyAttackGeometry.Rect right = EnemyAttackGeometry.attackRect(
            "slime", bodyX, bodyY, bodyW, bodyH, 40f, true, 0.9f);
        EnemyAttackGeometry.Rect left = EnemyAttackGeometry.attackRect(
            "slime", bodyX, bodyY, bodyW, bodyH, 40f, false, 0.9f);

        float rightExtension = (right.x + right.w) - (bodyX + bodyW);
        float leftExtension = bodyX - left.x;

        assertThat(right.x).isCloseTo(bodyX + bodyW, within(0.01f));
        assertThat(left.x + left.w).isCloseTo(bodyX, within(0.01f));
        assertThat(rightExtension).isGreaterThanOrEqualTo(bodyW - 0.01f);
        assertThat(leftExtension).isGreaterThanOrEqualTo(bodyW - 0.01f);
    }

    @Test
    void skeletonAttackRangeIsExtendedBy15Percent() {
        LevelLayout layout = LevelLayout.buildTestLayout(901L);
        layout.enemySpawns.clear();
        layout.enemySpawns.add(new LevelLayout.EnemySpawn("skeleton", 560f, 896f, 480f, 640f));

        GameSimulator sim = new GameSimulator(901L, "test_hub", layout);
        SimEnemy skeleton = sim.getEnemies().get(0);

        assertThat(skeleton.attackRange).isCloseTo(64f * 1.15f, within(0.001f));
        assertThat(EnemyAttackGeometry.defaultAttackRange("skeleton"))
            .isCloseTo(64f * 1.15f, within(0.001f));
    }

    @Test
    void archerFiresProjectileThatDamagesPlayer() {
        LevelLayout layout = LevelLayout.buildTestLayout(902L);
        layout.enemySpawns.clear();
        layout.enemySpawns.add(new LevelLayout.EnemySpawn("archer", 640f, 896f, 544f, 736f));

        GameSimulator sim = new GameSimulator(902L, "test_hub", layout);
        SimPlayer p = new SimPlayer("p1", 0, 520f, 896f);
        sim.addPlayer(p);

        int initialHealth = p.health;
        boolean sawEnemyProjectile = false;

        for (int i = 0; i < 240; i++) {
            sim.step(Map.of());
            WorldSnapshot snap = sim.getSnapshot(i);
            if (snap.shurikens.stream().anyMatch(s -> s.ownerSlot < 0)) {
                sawEnemyProjectile = true;
            }
            if (p.health < initialHealth) break;
        }

        assertThat(sawEnemyProjectile).isTrue();
        assertThat(p.health).isLessThan(initialHealth);
    }
}
