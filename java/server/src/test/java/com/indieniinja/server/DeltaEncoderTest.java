package com.indieniinja.server;

import com.indieniinja.network.EnemyState;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * DeltaEncoder tests — verifies CRC-based change detection, reset behaviour,
 * and removed-entity tracking.
 *
 * Covers audit gap NET-3: DeltaEncoder.reset() must force a full re-diff so
 * that clients receiving a full snapshot on reconnect get complete state.
 *
 * DeltaEncoder is package-private; tests live in the same package.
 */
class DeltaEncoderTest {

    // ── NET-3a: first call returns all entities (no prior checksums) ──────────

    @Test
    void enemiesChangedReturnsAllOnFirstCall() {
        DeltaEncoder enc = new DeltaEncoder();
        List<EnemyState> enemies = List.of(
            makeEnemy("e1", 100f, 200f),
            makeEnemy("e2", 300f, 400f)
        );

        List<EnemyState> changed = enc.enemiesChanged(enemies);

        assertThat(changed).hasSize(2);
    }

    // ── NET-3b: unchanged entities not re-sent on second call ─────────────────

    @Test
    void enemiesChangedReturnsNothingWhenUnchanged() {
        DeltaEncoder enc = new DeltaEncoder();
        List<EnemyState> enemies = List.of(makeEnemy("e1", 100f, 200f));

        enc.enemiesChanged(enemies);                     // seed checksums
        List<EnemyState> second = enc.enemiesChanged(enemies);  // identical state

        assertThat(second).isEmpty();
    }

    // ── NET-3c: reset() forces full re-diff on next call ─────────────────────

    @Test
    void resetForcesFullRediff() {
        DeltaEncoder enc = new DeltaEncoder();
        List<EnemyState> enemies = List.of(
            makeEnemy("e1", 100f, 200f),
            makeEnemy("e2", 300f, 400f)
        );

        enc.enemiesChanged(enemies);  // seed checksums
        enc.reset();                  // clear all checksums

        List<EnemyState> afterReset = enc.enemiesChanged(enemies);
        assertThat(afterReset).hasSize(2);  // all enemies re-appear
    }

    // ── NET-3d: enemiesRemoved tracks departed entities ───────────────────────

    @Test
    void enemiesRemovedReturnsDepartedIds() {
        DeltaEncoder enc = new DeltaEncoder();
        List<EnemyState> full = List.of(
            makeEnemy("e1", 100f, 200f),
            makeEnemy("e2", 300f, 400f)
        );
        List<EnemyState> afterDeath = List.of(makeEnemy("e1", 100f, 200f));

        enc.enemiesChanged(full);              // register both enemies
        List<String> removed = enc.enemiesRemoved(afterDeath);  // e2 gone

        assertThat(removed).containsExactly("e2");
    }

    // ── Helper ────────────────────────────────────────────────────────────────

    private static EnemyState makeEnemy(String id, float x, float y) {
        EnemyState e = new EnemyState();
        e.enemyId     = id;
        e.x           = x;
        e.y           = y;
        e.vx          = 0f;
        e.vy          = 0f;
        e.hp          = 10;
        e.aiState     = "idle";
        e.facingRight = true;
        return e;
    }
}
