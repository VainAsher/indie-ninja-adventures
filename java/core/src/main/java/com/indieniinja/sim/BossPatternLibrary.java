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
        public final java.util.List<SimEnemy> enemies;
        public final HubStateMachine         hub;
        /** Called to broadcast a SCRIPTED_LOSS message to all clients. */
        public final Runnable                broadcastScriptedLoss;
        /** Called to spawn a time_leech enemy near a world position. */
        public final SpawnRequest            spawnEnemy;
        /** Called to fire a boss projectile toward a target point. */
        public final ProjectileRequest       fireProjectile;

        public PatternContext(Map<Integer, SimPlayer> players,
                              java.util.List<SimEnemy> enemies,
                              HubStateMachine hub,
                              Runnable broadcastScriptedLoss,
                              SpawnRequest spawnEnemy,
                              ProjectileRequest fireProjectile) {
            this.players             = players;
            this.enemies             = enemies;
            this.hub                 = hub;
            this.broadcastScriptedLoss = broadcastScriptedLoss;
            this.spawnEnemy          = spawnEnemy;
            this.fireProjectile      = fireProjectile;
        }
    }

    @FunctionalInterface
    public interface SpawnRequest {
        void spawn(String enemyType, float x, float y);
    }

    @FunctionalInterface
    public interface ProjectileRequest {
        void fire(SimBoss boss, float targetX, float targetY, float speed, int damage);
    }

    // ── Server event ─────────────────────────────────────────────────────────

    public enum ServerEvent { SCRIPTED_LOSS }

    // ─────────────────────────────────────────────────────────────────────────
    // Pattern 1 — Siren: Scripted Loss (Act II)
    // ─────────────────────────────────────────────────────────────────────────
    /**
     * Campaign first-boss rewrite:
     *   Phase 1 - archer-style standoff and single projectile fire.
     *   Phase 2 - adds short-range teleport repositioning.
     *   Phase 3 - upgrades attacks into 3-shot volleys.
     *
     * Each phase spawns red-tinted slime adds in the boss room. Boss damage
     * windows are expected to open only after that wave is cleared.
     */
    private static final class ScriptedLossPattern {

        private static final float PHASE1_MIN_RANGE = 220f;
        private static final float PHASE1_MAX_RANGE = 360f;
        private static final float PHASE2_MIN_RANGE = 180f;
        private static final float PHASE2_MAX_RANGE = 320f;
        private static final float PROJECTILE_SPEED = SimPlayer.SHURIKEN_SPEED * 0.95f;
        private static final float TELEPORT_COOLDOWN = 3.0f;
        private static final float VOLLEY_INTERVAL = 0.22f;

        static ServerEvent tick(SimBoss boss, PatternContext ctx, float dt) {
            SimPlayer target = nearestAlivePlayer(boss, ctx);
            if (target == null) return null;

            boss.tickInvincibility();
            if (boss.attackCooldown > 0f) boss.attackCooldown -= dt;
            if (boss.sirenTeleportCooldown > 0f) boss.sirenTeleportCooldown -= dt;
            if (boss.sirenVulnerableTimer > 0f) boss.sirenVulnerableTimer -= dt;

            int phase = Math.max(1, Math.min(3, boss.phaseNumber));
            if (boss.sirenAddsPhaseSpawned < phase) {
                spawnSirenAddsForPhase(boss, ctx, phase);
                boss.sirenAddsPhaseSpawned = phase;
                boss.sirenVulnerableTimer = 0f;
            }

            // Keep the boss in a ranged pressure band.
            float bossCx = boss.physics.x + boss.physics.width * 0.5f;
            float bossCy = boss.physics.y + boss.physics.height * 0.5f;
            float tx = target.physics.x + target.physics.width * 0.5f;
            float ty = target.physics.y + target.physics.height * 0.5f;
            float dx = tx - bossCx;
            float absDx = Math.abs(dx);
            float speed = boss.type.moveSpeed * dt;
            float minRange = phase >= 2 ? PHASE2_MIN_RANGE : PHASE1_MIN_RANGE;
            float maxRange = phase >= 2 ? PHASE2_MAX_RANGE : PHASE1_MAX_RANGE;

            // Phase 2+ teleport to force directional swaps.
            if (phase >= 2 && boss.sirenTeleportCooldown <= 0f && absDx < minRange * 1.25f) {
                float teleportDir = dx >= 0f ? -1f : 1f;
                float jump = 140f + phase * 26f;
                float dstX = boss.physics.x + teleportDir * jump;
                boss.physics.x = Math.max(boss.arenaMinX, Math.min(boss.arenaMaxX, dstX));
                boss.sirenTeleportCooldown = TELEPORT_COOLDOWN;
            } else {
                if (absDx < minRange) {
                    boss.physics.x += (dx >= 0f ? -1f : 1f) * speed;
                } else if (absDx > maxRange) {
                    boss.physics.x += (dx >= 0f ? 1f : -1f) * speed;
                }
            }

            boss.facingRight = tx >= boss.physics.x + boss.physics.width * 0.5f;
            boss.clampToArena();

            // Phase 3 bursts: fire 3-shot volley with short cadence.
            if (boss.sirenVolleyShotsRemaining > 0) {
                boss.aiState = BossAIState.ATTACK_RANGED;
                boss.sirenVolleyTimer -= dt;
                if (boss.sirenVolleyTimer <= 0f) {
                    float spread = (boss.sirenVolleyShotsRemaining - 2) * 26f;
                    if (ctx.fireProjectile != null) {
                        ctx.fireProjectile.fire(boss, tx + spread, ty, PROJECTILE_SPEED, boss.type.baseDamage + 1);
                    }
                    boss.sirenVolleyShotsRemaining--;
                    boss.sirenVolleyTimer = VOLLEY_INTERVAL;
                }
                return null;
            }

            if (boss.attackCooldown <= 0f) {
                if (phase == 3) {
                    boss.sirenVolleyShotsRemaining = 3;
                    boss.sirenVolleyTimer = 0f;
                    boss.attackCooldown = 1.95f;
                    boss.aiState = BossAIState.ATTACK_RANGED;
                } else {
                    if (ctx.fireProjectile != null) {
                        ctx.fireProjectile.fire(boss, tx, ty, PROJECTILE_SPEED, boss.type.baseDamage + (phase >= 2 ? 1 : 0));
                    }
                    boss.attackCooldown = (phase == 1) ? 1.70f : 1.35f;
                    boss.aiState = BossAIState.ATTACK_RANGED;
                }
            } else {
                boss.aiState = BossAIState.MOVE;
            }
            return null;
        }

        private static void spawnSirenAddsForPhase(SimBoss boss, PatternContext ctx, int phase) {
            if (ctx.spawnEnemy == null) return;

            int extraMax = phase * 2;
            int seed = Math.abs(boss.bossId.hashCode() * 31 + phase * 97);
            int extra = seed % (extraMax + 1);
            int addCount = phase * 3 + extra; // [phase*3, phase*5]
            float cx = boss.physics.x + boss.physics.width * 0.5f;
            float cy = boss.physics.y + boss.physics.height * 0.5f;

            for (int i = 0; i < addCount; i++) {
                double a = (Math.PI * 2.0 * i) / Math.max(1, addCount);
                float r = 96f + (i % 4) * 28f;
                float sx = cx + (float) Math.cos(a) * r;
                float sy = cy + (float) Math.sin(a) * (r * 0.35f);
                sx = Math.max(boss.arenaMinX, Math.min(boss.arenaMaxX, sx));
                sy = Math.max(boss.arenaMinY, Math.min(boss.arenaMaxY, sy));
                ctx.spawnEnemy.spawn("slime_red", sx, sy);
            }
            log.info("[Siren] phase {} add wave spawned: {}", phase, addCount);
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
        private static final int   MAX_ACTIVE_LEECHES = 5;

        static ServerEvent tick(SimBoss boss, PatternContext ctx, float dt) {
            // Drain all players' Lantern values
            for (SimPlayer p : ctx.players.values()) {
                if (p.lantern != null) p.lantern.decay(DRAIN_RATE * dt, true);
            }

            // Spawn time_leech minions on interval
            boss.spawnTimer -= dt;
            if (boss.spawnTimer <= 0 && ctx.spawnEnemy != null) {
                boss.spawnTimer = SPAWN_INTERVAL;
                int activeLeeches = 0;
                for (SimEnemy en : ctx.enemies) {
                    if (!en.isAlive()) continue;
                    if (!"time_leech".equals(en.enemyType)) continue;
                    float cx = en.physics.x + en.physics.width * 0.5f;
                    float cy = en.physics.y + en.physics.height * 0.5f;
                    if (cx < boss.arenaMinX - 64f || cx > boss.arenaMaxX + 64f) continue;
                    if (cy < boss.arenaMinY - 64f || cy > boss.arenaMaxY + 64f) continue;
                    activeLeeches++;
                }
                if (activeLeeches < MAX_ACTIVE_LEECHES) {
                    float spawnX = boss.physics.x + (boss.facingRight ? 64 : -64);
                    float spawnY = boss.physics.y;
                    spawnX = Math.max(boss.arenaMinX, Math.min(boss.arenaMaxX, spawnX));
                    spawnY = Math.max(boss.arenaMinY, Math.min(boss.arenaMaxY, spawnY));
                    ctx.spawnEnemy.spawn("time_leech", spawnX, spawnY);
                    log.debug("[TimeLord] spawned time_leech at ({},{}) [{} active]", spawnX, spawnY, activeLeeches + 1);
                } else {
                    log.debug("[TimeLord] spawn skipped; {} active time_leech minions", activeLeeches);
                }
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
