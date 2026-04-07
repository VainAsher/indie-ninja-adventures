package com.indieniinja.client.rendering;

import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.g2d.TextureRegion;
import com.indieniinja.network.EnemyState;
import com.indieniinja.network.PickupState;
import com.indieniinja.network.PlayerState;
import com.indieniinja.network.ShurikenState;
import com.indieniinja.network.WorldSnapshot;
import com.indieniinja.sim.SimShuriken;
import com.indieniinja.physics.PhysicsConstants;

/**
 * Renders players, enemies, and pickups from the authoritative WorldSnapshot.
 *
 * Animation keys follow the convention:
 *   "player_<animState>"  — e.g. "player_idle", "player_run", "player_jump"
 *   "enemy_<type>_<aiState>" — e.g. "enemy_ninja_chase" (type from enemyId prefix)
 *   "pickup_<pickupType>" — e.g. "pickup_health"
 *
 * Falls back to a coloured rectangle when the atlas key is not found so the
 * client is playable before the full asset pack is integrated.
 *
 * SpriteBatch must be begun by the caller; EntityRenderer does not call begin/end.
 */
public final class EntityRenderer {

    private static final int PW  = PhysicsConstants.PLAYER_WIDTH;        // 28 (physics AABB)
    private static final int PH  = PhysicsConstants.PLAYER_HEIGHT;       // 56 (physics AABB)
    private static final int PCH = PhysicsConstants.PLAYER_CROUCH_HEIGHT;// 28
    private static final int SW  = AnimationRegistry.SPRITE_W;           // 80 (source frame)
    private static final int SH  = AnimationRegistry.SPRITE_H;           // 80 (source frame)

    // Render at 2× scale so the character fills ~2 tiles vertically (good visual size)
    private static final float SCALE   = 2f;
    private static final int   SDW     = (int)(SW * SCALE);  // 160 — display width
    private static final int   SDH     = (int)(SH * SCALE);  // 160 — display height

    // The template sprite has 16 empty rows below the character's feet inside the 80px frame.
    // (Inspected: feet at row 63, bottom of frame row 79 → 16 empty rows.)
    // Scaled by SCALE to match the display quad size.
    private static final int FEET_PAD = (int)(16 * SCALE); // 32 px at 2×

    // Horizontal offset to center SDW display quad over the PW AABB
    // posX + PW/2  = AABB centre.  drawX = AABB centre - SDW/2
    private static final int SPRITE_OX = PW / 2 - SDW / 2;  // 14 - 80 = -66

    private static final int PICKUP_SIZE = 20;

    /** Returns [w, h] physics dimensions for an enemy type — matches GameSimulator.buildEnemy(). */
    private static int[] enemySize(String enemyType) {
        return switch (enemyType) {
            case "bat"      -> new int[]{28, 28};
            case "slime"    -> new int[]{32, 28};
            case "wolf"     -> new int[]{40, 32};
            case "goblin",
                 "skeleton" -> new int[]{32, 48};
            default         -> new int[]{32, 48};
        };
    }

    // Per-state FPS constants matching Python sprite_manager.py ANIMATION_DEFS exactly
    // idle=8, walk/slow_walk=8-10, run=12, dash=20, attack=15, throw=12, hurt=12, death=12
    private static final float FPS_IDLE       = 8f;
    private static final float FPS_WALK       = 10f;
    private static final float FPS_RUN        = 12f;
    private static final float FPS_DASH       = 20f;
    private static final float FPS_JUMP       = 10f;
    private static final float FPS_ATTACK     = 15f;
    private static final float FPS_THROW      = 12f;
    private static final float FPS_HURT       = 12f;
    private static final float FPS_DEATH      = 12f;
    private static final float FPS_WALL_SLIDE = 8f;
    private static final float ENEMY_ANIM_FPS = 6f;
    private static final float PICKUP_ANIM_FPS= 4f;

    private final AnimationRegistry anims;
    private final ParticleSystem    particles;

    // Per-entity state time for smooth animation (render-thread managed)
    private final java.util.HashMap<String, Float>   stateTimes  = new java.util.HashMap<>();
    private final java.util.HashMap<String, String>  lastState   = new java.util.HashMap<>();
    // Particle event tracking
    private final java.util.HashMap<String, Float>   prevVelY    = new java.util.HashMap<>();
    private final java.util.HashMap<String, Integer> prevHealth  = new java.util.HashMap<>();
    private final java.util.HashMap<String, Float>   dustTimers  = new java.util.HashMap<>();
    private final java.util.HashMap<String, Boolean> prevTeleport= new java.util.HashMap<>();

    public EntityRenderer(AnimationRegistry anims, ParticleSystem particles) {
        this.anims     = anims;
        this.particles = particles;
    }

    /**
     * Draw all world entities for the current frame.
     *
     * @param batch     active SpriteBatch (already begun)
     * @param snap      latest merged WorldSnapshot from GameStateBuffer
     * @param deltaTime seconds since last render (for animation clock)
     */
    public void render(SpriteBatch batch, WorldSnapshot snap, float deltaTime) {
        if (snap == null) return;

        for (ShurikenState sh : snap.shurikens) renderShuriken(batch, sh, deltaTime);
        for (EnemyState    e  : snap.enemies)   renderEnemy(batch, e, deltaTime);
        for (PickupState   p  : snap.pickups)   renderPickup(batch, p, deltaTime);
        for (PlayerState   p  : snap.players)   renderPlayer(batch, p, deltaTime);
    }

    // ── Shurikens ─────────────────────────────────────────────────────────────

    private void renderShuriken(SpriteBatch batch, ShurikenState sh, float dt) {
        if (!sh.alive) return;
        // Spin the sprite by cycling through a "shuriken" atlas key if available,
        // otherwise falls back to the placeholder (small grey square).
        float stateTime = tickStateTime(sh.shurikenId, "shuriken", dt);
        TextureRegion frame = anims.getFrame("shuriken", stateTime, 12f);
        batch.setColor(sh.stuck ? Color.GRAY : Color.WHITE);
        batch.draw(frame, sh.x, sh.y, SimShuriken.W, SimShuriken.H);
        batch.setColor(Color.WHITE);
    }

    // ── Players ───────────────────────────────────────────────────────────────

    /** Map an animState string to its correct FPS — matches Python ANIMATION_DEFS fps column. */
    private static float playerFps(String animState) {
        return switch (animState) {
            case "attack", "slash1", "slash2", "slash3", "slash_air", "jump_slash" -> FPS_ATTACK;
            case "throw", "throw_ground", "throw_air", "throw_crouch",
                 "teleport", "ninjutsu_hand", "ninjutsu_summon"                    -> FPS_THROW;
            case "hurt", "hurt2", "death"                                           -> FPS_DEATH;
            case "dash"                                                             -> FPS_DASH;
            case "run"                                                              -> FPS_RUN;
            case "walk", "slow_walk"                                                -> FPS_WALK;
            case "jump", "fall", "wall_slide", "wall_hang", "air_spin"             -> FPS_JUMP;
            default                                                                 -> FPS_IDLE;
        };
    }

    private void renderPlayer(SpriteBatch batch, PlayerState p, float dt) {
        if (p.isDead) return;

        String state   = (p.animState != null && !p.animState.isEmpty()) ? p.animState : "idle";
        String animKey = "player_" + state;

        // ── Animation state tracking ──────────────────────────────────────────
        String prevAnim = lastState.get(p.playerId);
        float stateTime = tickStateTime(p.playerId, animKey, dt);
        boolean stateChanged = !animKey.equals(prevAnim);
        TextureRegion frame = anims.getFrame(animKey, stateTime, playerFps(state));

        // Sprites default to facing right.  Flip X when facing left.
        boolean wantFlipX  = (p.facing == -1);
        boolean needChange = wantFlipX != frame.isFlipX();
        if (needChange) frame.flip(true, false);

        // Y offset: align character feet (16 source-px from sprite bottom, scaled) with AABB bottom.
        boolean crouching = "crouch".equals(state) || "crouch_walk".equals(state);
        int aabbH   = crouching ? PCH : PH;
        float sprOY = aabbH - SDH + FEET_PAD;

        float drawX = p.posX + SPRITE_OX;
        float drawY = p.posY + sprOY;
        batch.draw(frame, drawX, drawY, SDW, SDH);

        if (needChange) frame.flip(true, false);  // restore shared region

        // Teleport ghost cursor
        if (p.teleportPhaseMode) {
            batch.setColor(0.4f, 0.8f, 1f, 0.55f);
            float gx = p.teleportCursorX + SPRITE_OX;
            float gy = p.teleportCursorY + sprOY;
            if (wantFlipX != frame.isFlipX()) frame.flip(true, false);
            batch.draw(frame, gx, gy, SDW, SDH);
            if (wantFlipX != frame.isFlipX()) frame.flip(true, false);
            batch.setColor(Color.WHITE);
        }

        // ── Particle emission ─────────────────────────────────────────────────
        if (particles != null) {
            float feetX = p.posX + PW * 0.5f;
            float feetY = p.posY + aabbH;
            float pvy0  = prevVelY.getOrDefault(p.playerId, 0f);

            // Jump puff — on first frame of jump anim
            if (stateChanged && "player_jump".equals(animKey)) {
                particles.emitJumpPuff(feetX, feetY);
            }

            // Landing puff — was falling (velY > 2), now grounded (velY ≤ 0)
            if (pvy0 > 2f && p.velY <= 0f && !"player_jump".equals(animKey)) {
                particles.emitLandPuff(feetX, feetY);
            }

            // Run dust — periodic while in run state
            if ("run".equals(state)) {
                float dustT = dustTimers.getOrDefault(p.playerId, 0f) - dt;
                if (dustT <= 0f) {
                    particles.emitRunDust(feetX, feetY, p.facing);
                    dustT = 0.08f;  // emit every 80ms
                }
                dustTimers.put(p.playerId, dustT);
            } else {
                dustTimers.remove(p.playerId);
            }

            // Teleport burst — on phase-mode start (was false, now true)
            boolean wasTeleporting = prevTeleport.getOrDefault(p.playerId, false);
            if (p.teleportPhaseMode && !wasTeleporting) {
                particles.emitTeleportBurst(feetX, feetY - aabbH * 0.5f);
            }
            // Also burst at destination when phase ends
            if (!p.teleportPhaseMode && wasTeleporting) {
                particles.emitTeleportBurst(feetX, feetY - aabbH * 0.5f);
            }
            prevTeleport.put(p.playerId, p.teleportPhaseMode);
            prevVelY.put(p.playerId, p.velY);
        }
    }

    // ── Enemies ───────────────────────────────────────────────────────────────

    private void renderEnemy(SpriteBatch batch, EnemyState e, float dt) {
        if ("dead".equals(e.aiState)) return;

        // Use explicit enemyType from wire; fall back to ID-parsing for old snapshots
        String typePrefix = (e.enemyType != null && !e.enemyType.isEmpty())
            ? e.enemyType
            : derivePrefixFromId(e.enemyId);
        String animKey = "enemy_" + typePrefix + "_" + (e.aiState != null ? e.aiState : "idle");

        float stateTime = tickStateTime(e.enemyId, animKey, dt);
        TextureRegion frame = anims.getFrame(animKey, stateTime, ENEMY_ANIM_FPS);

        boolean wantEnemyFlipX  = !e.facingRight;
        boolean needEnemyChange = wantEnemyFlipX != frame.isFlipX();
        if (needEnemyChange) frame.flip(true, false);

        int[] sz = enemySize(typePrefix);
        batch.draw(frame, e.x, e.y, sz[0], sz[1]);

        if (needEnemyChange) frame.flip(true, false);

        // Hit spark — emit when health has decreased since last frame
        if (particles != null) {
            int prev = prevHealth.getOrDefault(e.enemyId, e.hp);
            if (e.hp < prev) {
                float cx = e.x + sz[0] * 0.5f;
                float cy = e.y + sz[1] * 0.5f;
                particles.emitHitSpark(cx, cy);
            }
            prevHealth.put(e.enemyId, e.hp);
        }
    }

    // ── Pickups ───────────────────────────────────────────────────────────────

    private void renderPickup(SpriteBatch batch, PickupState p, float dt) {
        if (!p.alive) return;

        String animKey = "pickup_" + (p.pickupType != null ? p.pickupType : "generic");
        float stateTime = tickStateTime(p.pickupId, animKey, dt);
        TextureRegion frame = anims.getFrame(animKey, stateTime, PICKUP_ANIM_FPS);

        batch.draw(frame, p.x - PICKUP_SIZE / 2f, p.y, PICKUP_SIZE, PICKUP_SIZE);
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    /** Fallback: derive type string from enemy ID convention "hub_type_idx". */
    private static String derivePrefixFromId(String enemyId) {
        String[] parts = enemyId.split("_");
        return (parts.length >= 2) ? parts[parts.length - 2] : enemyId;
    }

    // ── Animation clock helpers ───────────────────────────────────────────────

    /**
     * Track per-entity state time; resets to 0 when animKey changes (state transition).
     */
    private float tickStateTime(String entityId, String animKey, float dt) {
        String prev = lastState.get(entityId);
        float  t    = stateTimes.getOrDefault(entityId, 0f);
        if (!animKey.equals(prev)) {
            t = 0f;   // state changed — restart animation
            lastState.put(entityId, animKey);
        }
        t += dt;
        stateTimes.put(entityId, t);
        return t;
    }

    /** Remove per-entity tracking when an entity is no longer in the snapshot. */
    public void pruneEntities(WorldSnapshot snap) {
        if (snap == null) return;
        java.util.Set<String> live = new java.util.HashSet<>();
        snap.players.forEach(p  -> live.add(p.playerId));
        snap.enemies.forEach(e  -> live.add(e.enemyId));
        snap.pickups.forEach(p  -> live.add(p.pickupId));
        snap.shurikens.forEach(s -> live.add(s.shurikenId));
        stateTimes.keySet().retainAll(live);
        lastState.keySet().retainAll(live);
        prevVelY.keySet().retainAll(live);
        prevHealth.keySet().retainAll(live);
        dustTimers.keySet().retainAll(live);
        prevTeleport.keySet().retainAll(live);
    }
}
