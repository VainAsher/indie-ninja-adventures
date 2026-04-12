package com.indieniinja.sim;

import com.indieniinja.world.HubStateMachine;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayDeque;
import java.util.Map;

/**
 * Shadow Ascent M5 — Boss Psychological Pattern Library.
 *
 * Each of the four narrative bosses has a distinct behavioral pattern that
 * maps to a psychological theme.  Patterns are stateless helpers: they operate
 * on the mutable SimBoss + context and return an optional server-side event.
 *
 * Design note: Ship working FSMs first, tune after (Lesson 1 from project history).
 *
 * Boss → Pattern:
 *   SIREN           → ScriptedLossPattern  (Act II — invincible, strips Yin/Yang)
 *   ECHO_WARDEN     → EchoMirrorPattern    (Act III — mirrors player 0.5 s delayed)
 *   TIME_LEECH_LORD → LanternDrainPattern  (Act IV — drains Lantern, spawns time leeches)
 *   MEMORY_EATER    → PhaseResetPattern    (Act VI — resets platforms per phase)
 */
public final class BossPatternLibrary {

    private static final Logger log = LoggerFactory.getLogger(BossPatternLibrary.class);

    private BossPatternLibrary() {}

    // ── Public dispatch ───────────────────────────────────────────────────────

    /**
     * Called from GameSimulator.stepBosses() once per tick for Shadow Ascent bosses.
     * Returns a non-null ServerEvent if the caller should broadcast a message.
     *
     * @param boss      the boss being ticked
     * @param ctx       simulation context (players, hub, lantern access)
     * @param dt        delta time in seconds
     * @return optional server event or null
     */
    public static ServerEvent tick(SimBoss boss, PatternContext ctx, float dt) {
        return switch (boss.type) {
            case SIREN           -> ScriptedLossPattern.tick(boss, ctx, dt);
            case ECHO_WARDEN     -> EchoMirrorPattern.tick(boss, ctx, dt);
            case TIME_LEECH_LORD -> LanternDrainPattern.tick(boss, ctx, dt);
            case MEMORY_EATER    -> PhaseResetPattern.tick(boss, ctx, dt);
            default              -> null;
        };
    }

    // ── Context object ────────────────────────────────────────────────────────

    /** Everything a pattern needs to read or write during a tick. */
    public static final class PatternContext {
        public final Map<Integer, SimPlayer> players;
        public final HubStateMachine         hub;
        /** Called to broadcast a SCRIPTED_LOSS message to all clients. */
        public final Runnable                broadcastScriptedLoss;
        /** Called to spawn a time_leech enemy near a world position. */
        public final SpawnRequest            spawnEnemy;

        public PatternContext(Map<Integer, SimPlayer> players,
                              HubStateMachine hub,
                              Runnable broadcastScriptedLoss,
                              SpawnRequest spawnEnemy) {
            this.players             = players;
            this.hub                 = hub;
            this.broadcastScriptedLoss = broadcastScriptedLoss;
            this.spawnEnemy          = spawnEnemy;
        }
    }

    @FunctionalInterface
    public interface SpawnRequest {
        void spawn(String enemyType, float x, float y);
    }

    // ── Server event ─────────────────────────────────────────────────────────

    public enum ServerEvent { SCRIPTED_LOSS }

    // ─────────────────────────────────────────────────────────────────────────
    // Pattern 1 — Siren: Scripted Loss (Act II)
    // ─────────────────────────────────────────────────────────────────────────
    /**
     * The Siren is not a fight.
     *
     * Phase 1: Siren appears in IDLE state, begins a brief "song sequence"
     *          (dialogue timer).  Player attacks deal 0 damage.
     * Phase 2: After SIREN_SONG_DURATION seconds, the sequence completes:
     *   - Server zeros all player Yin + Yang
     *   - HubStateMachine.onSirenDefeated() → hub transitions to EMPTY
     *   - SCRIPTED_LOSS event broadcast → clients play collapse animation
     * Phase 3: Siren despawns.
     *
     * Psychological theme: scripted loss — the player cannot win this fight.
     * The "defeat" is the narrative point.
     */
    private static final class ScriptedLossPattern {

        private static final float SIREN_SONG_DURATION = 6.0f; // seconds of "dialogue"

        static ServerEvent tick(SimBoss boss, PatternContext ctx, float dt) {
            // Siren is permanently invincible — override HP if takeDamage was called
            boss.hp = Math.max(1, boss.hp);

            // Advance song timer using boss.stateTimer (reused field)
            boss.stateTimer += dt;

            if (boss.stateTimer >= SIREN_SONG_DURATION && !boss.scriptedLossTriggered) {
                boss.scriptedLossTriggered = true;
                log.info("[Siren] scripted loss sequence complete — stripping Yin/Yang");

                // Zero all player Yin/Yang
                for (SimPlayer p : ctx.players.values()) {
                    if (p.yinYang != null) {
                        p.yinYang.yin  = 0f;
                        p.yinYang.yang = 0f;
                    }
                }

                // Hub collapses
                if (ctx.hub != null) ctx.hub.onSirenDefeated();

                // Signal caller to broadcast SCRIPTED_LOSS
                if (ctx.broadcastScriptedLoss != null) ctx.broadcastScriptedLoss.run();

                // Despawn siren
                boss.hp = 0;

                return ServerEvent.SCRIPTED_LOSS;
            }
            return null;
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Pattern 2 — Echo Warden: Mirror Movement (Act III)
    // ─────────────────────────────────────────────────────────────────────────
    /**
     * The Echo Warden mirrors the nearest player's horizontal movement with a
     * 0.5-second delay using a ring buffer of recent player positions.
     *
     * Exploitation mechanic: walk toward a hazard (spike pit, lava), stop just
     * before it, and the Warden will walk into it 0.5 s later.
     *
     * Psychological theme: self-doubt — fighting your own shadow.
     */
    private static final class EchoMirrorPattern {

        private static final float ECHO_DELAY   = 0.5f;  // seconds of delay
        private static final int   BUFFER_SIZE  = 30;    // at 60 Hz: 30 ticks = 0.5 s

        // Per-boss echo buffer stored in boss.echoBuffer (initialised on first tick)
        static ServerEvent tick(SimBoss boss, PatternContext ctx, float dt) {
            if (boss.echoBuffer == null) boss.echoBuffer = new ArrayDeque<>(BUFFER_SIZE + 1);

            // Find nearest player
            SimPlayer nearest = nearestAlivePlayer(boss, ctx);
            if (nearest == null) return null;

            // Record current player X into the buffer
            boss.echoBuffer.addLast(nearest.physics.x);
            while (boss.echoBuffer.size() > BUFFER_SIZE) boss.echoBuffer.removeFirst();

            // Mirror the delayed position if buffer is full
            if (boss.echoBuffer.size() == BUFFER_SIZE) {
                float targetX = boss.echoBuffer.peekFirst();
                float bossCx  = boss.physics.x + boss.physics.width * 0.5f;
                float speed   = boss.type.moveSpeed * dt;

                if (targetX > bossCx) {
                    boss.physics.x += speed;
                    boss.facingRight = true;
                } else if (targetX < bossCx) {
                    boss.physics.x -= speed;
                    boss.facingRight = false;
                }
            }

            // Standard attack when in range
            float dist = boss.distanceTo(nearest.physics.x, nearest.physics.y);
            if (dist < SimBoss.MELEE_RANGE && boss.attackCooldown <= 0) {
                boss.aiState = BossAIState.ATTACK_MELEE;
                boss.attackCooldown = SimBoss.BASE_ATTACK_COOLDOWN;
            } else {
                boss.aiState = BossAIState.MOVE;
            }
            return null;
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Pattern 3 — Time Leech Lord: Lantern Drain (Act IV)
    // ─────────────────────────────────────────────────────────────────────────
    /**
     * The Time Leech Lord drains the player's Lantern every tick, spawns
     * TIME_LEECH minion enemies at intervals, and triggers a speed burst when
     * HP drops to 30%.
     *
     * Without a high Lantern value, the player literally cannot see clearly.
     * The room darkens progressively — a mechanical representation of burnout.
     *
     * Psychological theme: burnout — resources depleting faster than they can be restored.
     */
    private static final class LanternDrainPattern {

        private static final float DRAIN_RATE       = 0.03f;  // lantern units/s per player
        private static final float SPAWN_INTERVAL   = 8.0f;   // seconds between minion spawns
        private static final float SPEED_BURST_MULT = 2.0f;   // speed multiplier at 30% HP
        private static final float BURST_HP_RATIO   = 0.30f;

        static ServerEvent tick(SimBoss boss, PatternContext ctx, float dt) {
            // Drain all players' Lantern values
            for (SimPlayer p : ctx.players.values()) {
                if (p.lantern != null) p.lantern.decay(DRAIN_RATE * dt, true);
            }

            // Spawn time_leech minions on interval
            boss.spawnTimer -= dt;
            if (boss.spawnTimer <= 0 && ctx.spawnEnemy != null) {
                boss.spawnTimer = SPAWN_INTERVAL;
                float spawnX = boss.physics.x + (boss.facingRight ? 64 : -64);
                float spawnY = boss.physics.y;
                ctx.spawnEnemy.spawn("time_leech", spawnX, spawnY);
                log.debug("[TimeLord] spawned time_leech at ({},{})", spawnX, spawnY);
            }

            // Speed burst below 30% HP
            if (!boss.speedBurstActive && (float) boss.hp / boss.maxHp <= BURST_HP_RATIO) {
                boss.speedBurstActive = true;
                log.info("[TimeLord] speed burst activated at {}% HP",
                         (int)(100f * boss.hp / boss.maxHp));
            }

            // Standard movement — chase nearest player (speed boost applied if burst active)
            SimPlayer nearest = nearestAlivePlayer(boss, ctx);
            if (nearest == null) return null;

            float dist  = boss.distanceTo(nearest.physics.x, nearest.physics.y);
            float speed = boss.type.moveSpeed * (boss.speedBurstActive ? SPEED_BURST_MULT : 1f) * dt;
            float bossCx = boss.physics.x + boss.physics.width * 0.5f;

            if (nearest.physics.x > bossCx) { boss.physics.x += speed; boss.facingRight = true; }
            else                             { boss.physics.x -= speed; boss.facingRight = false; }

            if (dist < SimBoss.MELEE_RANGE && boss.attackCooldown <= 0) {
                boss.aiState = BossAIState.ATTACK_MELEE;
                boss.attackCooldown = SimBoss.BASE_ATTACK_COOLDOWN;
            } else {
                boss.aiState = BossAIState.MOVE;
            }
            return null;
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Pattern 4 — Memory Eater: Phase Reset (Act VI)
    // ─────────────────────────────────────────────────────────────────────────
    /**
     * The Memory Eater resets platform positions at each HP threshold (75%/50%/25%)
     * and can re-lock doors the player has already unlocked.
     *
     * Practical effect: the player must re-navigate the room layout from scratch
     * on each phase. Progress is erased.
     *
     * Psychological theme: identity loss — what you thought you knew no longer applies.
     */
    private static final class PhaseResetPattern {

        static ServerEvent tick(SimBoss boss, PatternContext ctx, float dt) {
            int prevPhase = boss.phaseNumber;

            // Standard boss movement toward nearest player
            SimPlayer nearest = nearestAlivePlayer(boss, ctx);
            if (nearest != null) {
                float dist  = boss.distanceTo(nearest.physics.x, nearest.physics.y);
                float speed = boss.type.moveSpeed * dt;
                float bossCx = boss.physics.x + boss.physics.width * 0.5f;

                if (nearest.physics.x > bossCx) { boss.physics.x += speed; boss.facingRight = true; }
                else                             { boss.physics.x -= speed; boss.facingRight = false; }

                if (dist < SimBoss.MELEE_RANGE && boss.attackCooldown <= 0) {
                    boss.aiState = BossAIState.ATTACK_MELEE;
                    boss.attackCooldown = SimBoss.BASE_ATTACK_COOLDOWN * 0.7f; // faster attacks
                } else {
                    boss.aiState = BossAIState.MOVE;
                }
            }

            // Phase transitions trigger platform reset (signalled via boss.platformReset flag)
            if (boss.phaseNumber > prevPhase) {
                boss.platformReset = true;
                log.info("[MemoryEater] phase {} — triggering platform reset", boss.phaseNumber);
                // ZoneSimulationLoop reads boss.platformReset and calls WorldGenerator
                // to regenerate obstacle tile positions for this room.
            }

            return null;
        }
    }

    // ── Utility ───────────────────────────────────────────────────────────────

    private static SimPlayer nearestAlivePlayer(SimBoss boss, PatternContext ctx) {
        SimPlayer nearest = null;
        float nearestDist = Float.MAX_VALUE;
        for (SimPlayer p : ctx.players.values()) {
            if (!p.isAlive()) continue;
            float d = boss.distanceTo(p.physics.x, p.physics.y);
            if (d < nearestDist) { nearestDist = d; nearest = p; }
        }
        return nearest;
    }
}
