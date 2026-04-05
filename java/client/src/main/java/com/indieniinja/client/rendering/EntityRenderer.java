package com.indieniinja.client.rendering;

import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.g2d.TextureRegion;
import com.indieniinja.network.EnemyState;
import com.indieniinja.network.PickupState;
import com.indieniinja.network.PlayerState;
import com.indieniinja.network.WorldSnapshot;
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

    private static final int PW = PhysicsConstants.PLAYER_WIDTH;   // 28
    private static final int PH = PhysicsConstants.PLAYER_HEIGHT;  // 56
    private static final int PICKUP_SIZE = 20;
    private static final int ENEMY_W     = 32;
    private static final int ENEMY_H     = 48;

    // Animation FPS constants matching Python's AnimationRegistry
    private static final float PLAYER_ANIM_FPS = 8f;
    private static final float ENEMY_ANIM_FPS  = 6f;
    private static final float PICKUP_ANIM_FPS = 4f;

    private final AnimationRegistry anims;

    // Per-entity state time for smooth animation (render-thread managed)
    private final java.util.HashMap<String, Float> stateTimes = new java.util.HashMap<>();
    private final java.util.HashMap<String, String> lastState  = new java.util.HashMap<>();

    public EntityRenderer(AnimationRegistry anims) {
        this.anims = anims;
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

        for (EnemyState  e : snap.enemies)  renderEnemy(batch, e, deltaTime);
        for (PickupState p : snap.pickups)  renderPickup(batch, p, deltaTime);
        for (PlayerState p : snap.players)  renderPlayer(batch, p, deltaTime);
    }

    // ── Players ───────────────────────────────────────────────────────────────

    private void renderPlayer(SpriteBatch batch, PlayerState p, float dt) {
        if (p.isDead) return;

        String animKey = "player_" + (p.animState != null && !p.animState.isEmpty()
            ? p.animState : "idle");

        float stateTime = tickStateTime(p.playerId, animKey, dt);
        TextureRegion frame = anims.getFrame(animKey, stateTime, PLAYER_ANIM_FPS);

        // Sprites default to facing right.  Flip X when facing left.
        // Preserve any pre-applied Y-flip (Y-DOWN correction set at load time).
        boolean wantFlipX  = (p.facing == -1);
        boolean needChange = wantFlipX != frame.isFlipX();
        if (needChange) frame.flip(true, false);

        // posX/posY are the AABB top-left corner (left edge, top edge in Y-DOWN).
        batch.draw(frame, p.posX, p.posY, PW, PH);

        if (needChange) frame.flip(true, false);  // restore shared region
    }

    // ── Enemies ───────────────────────────────────────────────────────────────

    private void renderEnemy(SpriteBatch batch, EnemyState e, float dt) {
        if ("dead".equals(e.aiState)) return;

        // Derive entity type from enemyId prefix (e.g. "ninja_0" → "ninja")
        String typePrefix = e.enemyId.contains("_")
            ? e.enemyId.substring(0, e.enemyId.lastIndexOf('_'))
            : e.enemyId;
        String animKey = "enemy_" + typePrefix + "_" + (e.aiState != null ? e.aiState : "idle");

        float stateTime = tickStateTime(e.enemyId, animKey, dt);
        TextureRegion frame = anims.getFrame(animKey, stateTime, ENEMY_ANIM_FPS);

        boolean wantEnemyFlipX  = !e.facingRight;
        boolean needEnemyChange = wantEnemyFlipX != frame.isFlipX();
        if (needEnemyChange) frame.flip(true, false);

        // e.x / e.y are the AABB top-left corner
        batch.draw(frame, e.x, e.y, ENEMY_W, ENEMY_H);

        if (needEnemyChange) frame.flip(true, false);
    }

    // ── Pickups ───────────────────────────────────────────────────────────────

    private void renderPickup(SpriteBatch batch, PickupState p, float dt) {
        if (!p.alive) return;

        String animKey = "pickup_" + (p.pickupType != null ? p.pickupType : "generic");
        float stateTime = tickStateTime(p.pickupId, animKey, dt);
        TextureRegion frame = anims.getFrame(animKey, stateTime, PICKUP_ANIM_FPS);

        batch.draw(frame, p.x - PICKUP_SIZE / 2f, p.y, PICKUP_SIZE, PICKUP_SIZE);
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
        snap.players.forEach(p -> live.add(p.playerId));
        snap.enemies.forEach(e -> live.add(e.enemyId));
        snap.pickups.forEach(p -> live.add(p.pickupId));
        stateTimes.keySet().retainAll(live);
        lastState.keySet().retainAll(live);
    }
}
