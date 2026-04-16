package com.indieniinja.client.rendering;

import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.g2d.TextureRegion;
import com.indieniinja.network.BossState;
import com.indieniinja.network.EnemyState;
import com.indieniinja.network.NPCState;
import com.indieniinja.network.PickupState;
import com.indieniinja.network.PlatformState;
import com.indieniinja.network.PlayerState;
import com.indieniinja.network.PortalState;
import com.indieniinja.network.ShurikenState;
import com.indieniinja.network.WorldSnapshot;
import com.indieniinja.sim.SimShuriken;
import com.indieniinja.sim.EnemyAttackGeometry;
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

    // NPC fallback size (runtime width/height now comes from NPCState payload).
    private static final int NPC_W = 48;
    private static final int NPC_H = 72;
    // "!" interaction indicator: small square above NPC head
    private static final int INDICATOR_SIZE = 8;

    // Companion orb constants — Python entities/companions.py
    private static final float COMPANION_RADIUS    = 35f;   // orbit radius in px
    private static final float COMPANION_SPEED     = 0.8f;  // rad/s — doubled in Flow Mode

    // Lift fraction relative to sprite height. Keep at 0 so enemy feet sit on tiles.
    private static final float ENEMY_LIFT = 0.0f;

    /**
     * Display size [w, h] for each enemy type.
     * Art is 128×96 px per frame; displayed at 134×101 (+5%) per player feedback.
     */
    private static int[] enemySize(String enemyType) {
        return switch (enemyType) {
            case "bat"                 -> new int[]{28, 28};
            case "slime", "slime_red", "time_leech" -> new int[]{134, 101};
            case "goblin", "swordsman" -> new int[]{134, 101};
            case "skeleton"            -> new int[]{134, 101};
            case "spearman"            -> new int[]{134, 101};
            case "archer"              -> new int[]{134, 101};
            default                    -> new int[]{134, 101};
        };
    }

    /**
     * Physics AABB height for each enemy type.
     * Must mirror GameSimulator.buildEnemy() constructor arguments exactly.
     * Used to bottom-align the display sprite with the physics feet.
     */
    private static int enemyPhysicsH(String enemyType) {
        return switch (enemyType) {
            case "bat"                 -> 28;
            case "slime", "slime_red", "time_leech" -> 32;
            case "skeleton"            -> 56;
            case "spearman"            -> 52;
            case "goblin", "swordsman",
                 "archer"              -> 48;
            default                    -> 48;
        };
    }

    /** Physics AABB width — mirrors GameSimulator.buildEnemy(). */
    private static int enemyPhysicsW(String enemyType) {
        return switch (enemyType) {
            case "bat"      -> 28;
            case "slime", "slime_red", "time_leech" -> 40;
            case "skeleton" -> 32;
            case "spearman" -> 36;
            case "goblin", "swordsman", "archer" -> 32;
            default         -> 32;
        };
    }

    /**
     * Approximate horizontal body-centre anchor inside enemy spritesheets.
     * Some frames include heavy trailing-weapon padding, so centre anchoring
     * can place the visible body away from its gameplay hitboxes.
     */
    private static float enemyBodyCenterAnchorX(String enemyType, int spriteW, boolean facingRight) {
        float anchorUnflipped = switch (enemyType) {
            case "goblin", "swordsman" -> spriteW * 0.66f;
            case "spearman"            -> spriteW * 0.60f;
            case "archer"              -> spriteW * 0.56f;
            default                    -> spriteW * 0.50f;
        };
        if ("goblin".equals(enemyType) || "swordsman".equals(enemyType)) {
            // Greatsword sheets are heavily padded behind the body; keep a fixed
            // body anchor to avoid left/right mirroring drift in gameplay hitbox alignment.
            return anchorUnflipped;
        }
        return facingRight ? anchorUnflipped : (spriteW - anchorUnflipped);
    }

    /**
     * Most enemy sheets are authored facing right.
     * Slime-family sheets are authored facing left and need inverted flip logic.
     */
    private static boolean enemySpriteDefaultFacesRight(String enemyType) {
        return switch (enemyType) {
            case "slime", "slime_red", "time_leech" -> false;
            default -> true;
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
    private static final float PICKUP_ANIM_FPS= 4f;

    /**
     * Per-type, per-AI-state animation FPS — matches Python animation_system.py ANIMATION_DEFS.
     * AI states: idle, patrol (walk), chase (run), attack, stunned (hurt), dead (death).
     */
    private static float enemyFps(String type, String aiState) {
        return switch (type + "." + aiState) {
            // swordsman (greatsword) — slow, heavy
            case "swordsman.idle"                          -> 6f;
            case "swordsman.patrol"                        -> 7f;
            case "swordsman.chase"                         -> 8f;
            case "swordsman.flee"                          -> 8f;
            case "swordsman.attack", "swordsman.attack_b"  -> 6f;
            case "swordsman.stunned"                       -> 8f;
            case "swordsman.dead"                          -> 8f;
            // goblin alias (backward compat with old snapshots)
            case "goblin.idle"   -> 6f;
            case "goblin.patrol" -> 7f;
            case "goblin.chase"  -> 8f;
            case "goblin.flee"   -> 8f;
            case "goblin.attack" -> 6f;
            case "goblin.stunned"-> 8f;
            case "goblin.dead"   -> 8f;
            // skeleton (shield fighter)
            case "skeleton.idle"                              -> 6f;
            case "skeleton.patrol"                            -> 8f;
            case "skeleton.chase", "skeleton.flee"            -> 10f;
            case "skeleton.attack", "skeleton.attack_b"       -> 10f;
            case "skeleton.guard"                             -> 6f;
            case "skeleton.stunned"                           -> 8f;
            case "skeleton.dead"                              -> 8f;
            // slime (multi-hit melee)
            case "slime.idle", "slime_red.idle", "time_leech.idle"                           -> 6f;
            case "slime.patrol", "slime.chase", "slime.flee",
                 "slime_red.patrol", "slime_red.chase", "slime_red.flee",
                 "time_leech.patrol", "time_leech.chase", "time_leech.flee"                  -> 8f;
            case "slime.attack", "slime.attack_b", "slime.attack_c",
                 "slime_red.attack", "slime_red.attack_b", "slime_red.attack_c",
                 "time_leech.attack", "time_leech.attack_b", "time_leech.attack_c"           -> 10f;
            case "slime.stunned", "slime_red.stunned", "time_leech.stunned"                  -> 8f;
            case "slime.dead", "slime_red.dead", "time_leech.dead"                           -> 8f;
            // spearman (skeleton with spear)
            case "spearman.idle"                             -> 6f;
            case "spearman.patrol"                           -> 8f;
            case "spearman.chase", "spearman.flee"           -> 10f;
            case "spearman.attack", "spearman.attack_b"      -> 10f;
            case "spearman.stunned"                          -> 8f;
            case "spearman.dead"                             -> 8f;
            // archer (skeleton archer, kiter)
            case "archer.idle"                               -> 6f;
            case "archer.patrol"                             -> 8f;
            case "archer.chase", "archer.flee"               -> 12f;
            case "archer.attack", "archer.attack_b"          -> 12f;
            case "archer.stunned"                            -> 8f;
            case "archer.dead"                               -> 8f;
            default                                    -> 8f;
        };
    }

    private final AnimationRegistry anims;
    private final ParticleSystem    particles;

    // Per-entity state time for smooth animation (render-thread managed)
    private final java.util.HashMap<String, Float>   stateTimes   = new java.util.HashMap<>();
    private final java.util.HashMap<String, String>  lastState    = new java.util.HashMap<>();
    // Particle event tracking
    private final java.util.HashMap<String, Float>   prevVelY     = new java.util.HashMap<>();
    private final java.util.HashMap<String, Integer> prevHealth   = new java.util.HashMap<>();
    private final java.util.HashMap<String, Float>   dustTimers   = new java.util.HashMap<>();
    private final java.util.HashMap<String, Boolean> prevTeleport = new java.util.HashMap<>();
    // Companion orb orbit angle per player (radians, advances each frame)
    private final java.util.HashMap<String, Float>   companionAngle = new java.util.HashMap<>();
    // Death animation elapsed time per enemy — holds last frame after animation completes
    private final java.util.HashMap<String, Float>   deathTimers    = new java.util.HashMap<>();

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

        for (com.indieniinja.network.MovingPlatformState mp : snap.movingPlatforms)
            renderMovingPlatform(batch, mp);
        for (PlatformState fp : snap.platformStates) renderFallingPlatform(batch, fp);
        for (PortalState   p  : snap.portals)   renderPortal(batch, p, deltaTime);
        for (ShurikenState sh : snap.shurikens) renderShuriken(batch, sh, deltaTime);
        for (EnemyState    e  : snap.enemies)         renderEnemy(batch, e, deltaTime);
        // Overflow enemies from adjacent zones visible through door openings
        for (EnemyState    e  : snap.overflowEnemies) renderEnemy(batch, e, deltaTime);
        for (BossState     b  : snap.bosses)          renderBoss(batch, b, deltaTime);
        for (NPCState      n  : snap.npcs)            renderNpc(batch, n, deltaTime, snap.hubState);
        for (NPCState      n  : snap.overflowNpcs)    renderNpc(batch, n, deltaTime, snap.hubState);
        for (PickupState   p  : snap.pickups)   renderPickup(batch, p, deltaTime);
        for (PlayerState   p  : snap.players)   renderPlayer(batch, p, deltaTime);
        for (PlayerState   p  : snap.players)   renderCompanions(batch, p, deltaTime);
    }

    // ── Moving platforms ──────────────────────────────────────────────────────

    private void renderMovingPlatform(SpriteBatch batch,
                                       com.indieniinja.network.MovingPlatformState mp) {
        // Rendered as a dark brown bar — same visual language as one-way platforms.
        TextureRegion dot = anims.getFrame("__dot__", 0f, 1f);
        batch.setColor(0.55f, 0.38f, 0.20f, 1f);
        batch.draw(dot, mp.x, mp.y, mp.width, mp.height);
        batch.setColor(Color.WHITE);
    }

    private void renderFallingPlatform(SpriteBatch batch, PlatformState fp) {
        if (!fp.visible) return;
        TextureRegion dot = anims.getFrame("__dot__", 0f, 1f);
        // Slightly lighter brown to distinguish from moving platforms.
        batch.setColor(0.65f, 0.48f, 0.28f, 1f);
        batch.draw(dot, fp.originX, fp.posY, fp.width, fp.height);
        batch.setColor(Color.WHITE);
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
            case "attack", "slash1", "slash2", "slash3", "slash_air", "jump_slash",
                 "punch1", "punch2", "kick", "air_punch1", "air_punch2", "air_kick",
                 "crouch_punch", "crouch_kick", "run_kick",
                 "block_hit", "block_hit_hard"                                       -> FPS_ATTACK;
            case "throw", "throw_ground", "throw_air", "throw_crouch",
                 "teleport", "ninjutsu_hand", "ninjutsu_summon"                    -> FPS_THROW;
            case "button", "lever", "pickup", "pickup_crouch",
                 "door_enter", "door_exit", "chest_side", "chest_back"             -> 12f;
            case "hurt", "hurt2", "crouch_hurt", "death", "death2",
                 "prone_death", "prone_hurt", "collapse"                             -> FPS_DEATH;
            case "dash"                                                             -> FPS_DASH;
            case "run"                                                              -> FPS_RUN;
            case "walk", "slow_walk", "crouch_walk",
                 "prone_walk", "push", "pull"                                       -> FPS_WALK;
            case "jump", "fall", "wall_slide", "wall_hang", "air_spin",
                 "flip", "air_block"                                                -> FPS_JUMP;
            case "roll", "slide", "wall_land", "run_stop", "skid"                  -> 15f;
            case "swim", "swim_up", "swim_down", "swim_surface"                    -> 10f;
            case "climb_side", "climb_back", "climb_right", "climb_left",
                 "ledge_climb", "ledge_climb_back"                                  -> 10f;
            case "swim_idle", "swim_surface_idle", "climb_idle_side",
                 "climb_idle_back", "ledge_idle", "ledge_idle_back",
                 "block", "rope", "sit"                                             -> 6f;
            default                                                                 -> FPS_IDLE;
        };
    }

    private void renderPlayer(SpriteBatch batch, PlayerState p, float dt) {
        if (p.isDead) return;

        String state  = (p.animState != null && !p.animState.isEmpty()) ? p.animState : "idle";

        // ── Weapon-state key routing (animation Phase 4) ──────────────────────
        // EntityRenderer prepends the weapon prefix ("player_sword_") when the
        // sword key is registered.  Falls through to unarmed if not registered.
        String prefix = "player";
        if ("sword".equals(p.weaponState)) {
            String swordKey = "player_sword_" + state;
            if (anims.has(swordKey)) prefix = "player_sword";
        }
        String animKey = prefix + "_" + state;
        if ("collapse".equals(state) && !anims.has(animKey)) {
            String fallback = prefix + "_death";
            animKey = anims.has(fallback) ? fallback : "player_death";
            state = "death";
        }

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
        // Use explicit enemyType from wire; fall back to ID-parsing for old snapshots
        String typePrefix = (e.enemyType != null && !e.enemyType.isEmpty())
            ? e.enemyType
            : derivePrefixFromId(e.enemyId);
        String animType = switch (typePrefix) {
            case "slime_red", "time_leech" -> "slime";
            default -> typePrefix;
        };

        boolean isDead = "dead".equals(e.aiState);

        int[] sz    = enemySize(typePrefix);
        int   physW = enemyPhysicsW(typePrefix);
        int   physH = enemyPhysicsH(typePrefix);
        float bodyCx = e.x + physW * 0.5f;
        float drawX = bodyCx - enemyBodyCenterAnchorX(typePrefix, sz[0], e.facingRight);
        // Bottom-anchor: align sprite bottom with physics feet (e.y + physH), then lift.
        // Y-down coords: smaller Y = higher on screen.
        float drawY = e.y + physH - sz[1] * (1f + ENEMY_LIFT);
        boolean spriteFacingRight = e.facingRight;
        if (!enemySpriteDefaultFacesRight(typePrefix)) {
            spriteFacingRight = !spriteFacingRight;
        }

        if (isDead) {
            // Accumulate death timer; clamp frame to last so it holds
            float elapsed = deathTimers.getOrDefault(e.enemyId, 0f) + dt;
            deathTimers.put(e.enemyId, elapsed);
            String deadKey = "enemy_" + animType + "_dead";
            float fps = enemyFps(typePrefix, "dead");
            TextureRegion frame = anims.getFrameClamped(deadKey, elapsed, fps);
            boolean wantFlip = !spriteFacingRight;
            if (wantFlip != frame.isFlipX()) frame.flip(true, false);
            batch.draw(frame, drawX, drawY, sz[0], sz[1]);
            if (wantFlip != frame.isFlipX()) frame.flip(true, false);
            return;
        }

        // Living enemy — remove stale death timer if it somehow lingers
        deathTimers.remove(e.enemyId);

        String animKey = "enemy_" + animType + "_" + (e.aiState != null ? e.aiState : "idle");
        float stateTime = tickStateTime(e.enemyId, animKey, dt);
        TextureRegion frame = anims.getFrame(animKey, stateTime, enemyFps(typePrefix, e.aiState != null ? e.aiState : "idle"));

        boolean wantEnemyFlipX  = !spriteFacingRight;
        boolean needEnemyChange = wantEnemyFlipX != frame.isFlipX();
        if (needEnemyChange) frame.flip(true, false);

        if ("slime_red".equals(typePrefix)) {
            batch.setColor(1f, 0.55f, 0.55f, 1f);
        }
        batch.draw(frame, drawX, drawY, sz[0], sz[1]);
        if ("slime_red".equals(typePrefix)) {
            batch.setColor(Color.WHITE);
        }

        if (needEnemyChange) frame.flip(true, false);

        // Hit spark — emit when health has decreased since last frame
        if (particles != null) {
            int prev = prevHealth.getOrDefault(e.enemyId, e.hp);
            if (e.hp < prev) {
                float cx = drawX + sz[0] * 0.5f;
                float cy = drawY + sz[1] * 0.5f;  // centre of the displayed sprite
                particles.emitHitSpark(cx, cy);
            }
            prevHealth.put(e.enemyId, e.hp);
        }
    }

    // ── Pickups ───────────────────────────────────────────────────────────────

    /** Returns a distinct RGBA colour for each pickup type so placeholders are recognisable. */
    private static float[] pickupColor(String type) {
        return switch (type != null ? type : "") {
            case "coin"             -> new float[]{1.00f, 0.85f, 0.00f, 1f};  // gold
            case "health_potion"    -> new float[]{0.90f, 0.15f, 0.15f, 1f};  // red
            case "rare_potion"      -> new float[]{0.80f, 0.00f, 0.90f, 1f};  // purple
            case "gem"              -> new float[]{0.10f, 0.90f, 0.90f, 1f};  // cyan
            case "yin_fragment"     -> new float[]{0.30f, 0.50f, 1.00f, 1f};  // blue
            case "yang_fragment"    -> new float[]{1.00f, 0.50f, 0.10f, 1f};  // orange
            case "lantern_fragment" -> new float[]{1.00f, 1.00f, 0.40f, 1f};  // bright yellow
            default                 -> new float[]{0.70f, 0.70f, 0.70f, 1f};  // grey
        };
    }

    private void renderPickup(SpriteBatch batch, PickupState p, float dt) {
        if (!p.alive) return;

        String type    = p.pickupType != null ? p.pickupType : "generic";
        String animKey = "pickup_" + type;
        float stateTime = tickStateTime(p.pickupId, animKey, dt);
        TextureRegion frame = anims.getFrame(animKey, stateTime, PICKUP_ANIM_FPS);

        float[] c = pickupColor(type);
        batch.setColor(c[0], c[1], c[2], c[3]);
        batch.draw(frame, p.x - PICKUP_SIZE / 2f, p.y, PICKUP_SIZE, PICKUP_SIZE);
        batch.setColor(Color.WHITE);
    }

    // ── NPCs ──────────────────────────────────────────────────────────────────

    /**
     * Render a single NPC using the "npc_{type}_{animState}" atlas key.
     * Falls back to a violet placeholder (same for all NPC types) when no
     * sprite is loaded.  When isInteractable, draws a small yellow "!" above.
     *
     * Python parity: entities/npc.py NPC drawing + interaction indicator.
     */
    private void renderNpc(SpriteBatch batch, NPCState n, float dt, String hubState) {
        String typeKey = resolveNpcRenderType(n.npcType, hubState);
        String state   = (n.animState != null && !n.animState.isEmpty()) ? n.animState : "idle";
        String animKey = "npc_" + typeKey + "_" + state;
        int npcW = n.width > 0 ? n.width : NPC_W;
        int npcH = n.height > 0 ? n.height : NPC_H;

        float stateTime = tickStateTime(n.npcId, animKey, dt);
        float fps       = "walk".equals(state) ? 8f : 6f;
        TextureRegion frame = anims.getFrame(animKey, stateTime, fps);

        boolean wantFlipX = (n.facing == -1);
        if (wantFlipX != frame.isFlipX()) frame.flip(true, false);
        batch.draw(frame, n.x, n.y, npcW, npcH);
        if (wantFlipX != frame.isFlipX()) frame.flip(true, false);

        // Interaction "!" indicator — yellow square above the NPC head
        if (n.isInteractable) {
            batch.setColor(1f, 0.9f, 0.1f, 1f);
            TextureRegion dot = anims.getFrame("__dot__", 0f, 1f);
            float ix = n.x + npcW * 0.5f - INDICATOR_SIZE * 0.5f;
            float iy = n.y - INDICATOR_SIZE - 4f;
            batch.draw(dot, ix, iy, INDICATOR_SIZE, INDICATOR_SIZE);
            batch.setColor(Color.WHITE);
        }
    }

    private static String resolveNpcRenderType(String npcType, String hubState) {
        String type = (npcType != null && !npcType.isEmpty()) ? npcType : "lore";
        if (type.startsWith("siren_phase")) return type;
        if (!"siren".equals(type)) return type;

        String hs = hubState != null
            ? hubState.trim().toUpperCase(java.util.Locale.ROOT)
            : "";
        return switch (hs) {
            case "CORRUPTED" -> "siren_phase2";
            case "EMPTY"     -> "siren_phase3";
            default          -> "siren_phase1";
        };
    }

    // ── Bosses ────────────────────────────────────────────────────────────────

    /**
     * Render a boss entity with a large placeholder body (coloured by phase)
     * and a phase indicator label.  Falls back to a coloured quad when no boss
     * atlas key is registered — same pattern as enemy rendering.
     *
     * Bosses are 64×96 px physics; we render at 2× scale (128×192 display).
     */
    private void renderBoss(SpriteBatch batch, BossState boss, float dt) {
        if (!boss.alive) return;

        int bw = 64, bh = 96;      // physics dims (BossType.width/height)
        int dw = bw * 2, dh = bh * 2; // display at 2×

        String animKey;
        if ("boss_siren".equals(boss.bossType)) {
            int phase = Math.max(1, Math.min(4, boss.phase));
            animKey = "boss_siren_phase" + phase;
        } else {
            // Map AI state → animation key fragment
            String aiKey = switch (boss.aiState) {
                case "attack_melee", "attack_ranged", "attack_special" -> "attack";
                case "phase_transition", "vulnerable"                  -> "stunned";
                case "dead"                                            -> "dead";
                default                                                -> "idle";
            };
            animKey = boss.bossType + "_" + aiKey;
        }
        float stateTime = tickStateTime(boss.bossId, animKey, dt);
        TextureRegion frame = anims.getFrame(animKey, stateTime, 8f);

        // Phase-tinted colour: phase1=white, phase2=yellow, phase3=orange, phase4=red
        Color tint = "boss_siren".equals(boss.bossType)
            ? Color.WHITE
            : switch (boss.phase) {
                case 2  -> new Color(1f, 0.9f, 0.3f, 1f);
                case 3  -> new Color(1f, 0.55f, 0.1f, 1f);
                case 4  -> new Color(1f, 0.2f, 0.2f, 1f);
                default -> Color.WHITE;
            };
        batch.setColor(tint);

        float drawX = boss.x + bw * 0.5f - dw * 0.5f;
        float drawY = boss.y - (dh - bh);          // align feet to physics bottom
        if (!boss.facingRight) {
            // Flip horizontally
            batch.draw(frame, drawX + dw, drawY, -dw, dh);
        } else {
            batch.draw(frame, drawX, drawY, dw, dh);
        }
        batch.setColor(Color.WHITE);

        // Phase label above boss
        // (BitmapFont not available here — HudRenderer renders the HP bar separately)
    }

    // ── Portals ───────────────────────────────────────────────────────────────

    /**
     * Render a pulsing portal column.
     * Physics size: 64×96 px. Display: same.
     * Locked portals render in dark red; open portals pulse blue→cyan.
     * Python parity: game/portal_system.py Portal.get_color_with_pulse().
     */
    private void renderPortal(SpriteBatch batch, PortalState p, float dt) {
        if (!p.isActive) return;

        // Advance local pulse timer
        float t = tickStateTime(p.portalId, "portal_pulse", dt);
        float pulse = 0.5f + 0.5f * (float) Math.sin(t * 2 * Math.PI * 2f); // 2 Hz

        // Colour: locked=dark red, hub=blue→cyan, mission=gold
        if (p.isLocked || (p.requiredAbility != null && !p.requiredAbility.isEmpty())) {
            batch.setColor(0.6f, 0.1f, 0.1f, 0.5f + pulse * 0.3f);
        } else if ("mission".equals(p.portalType)) {
            batch.setColor(0.9f, 0.8f * pulse, 0.1f, 0.6f + pulse * 0.3f);
        } else {
            batch.setColor(0.2f + pulse * 0.2f, 0.5f + pulse * 0.4f, 1f, 0.6f + pulse * 0.3f);
        }

        TextureRegion frame = anims.getFrame("portal", t, 8f);
        batch.draw(frame, p.x, p.y, p.width, p.height);
        batch.setColor(Color.WHITE);

        // "E" interaction indicator (always show for active portals)
        batch.setColor(1f, 1f, 0.3f, 0.8f);
        TextureRegion dot = anims.getFrame("__dot__", 0f, 1f);
        float ix = p.x + p.width * 0.5f - INDICATOR_SIZE * 0.5f;
        float iy = p.y - INDICATOR_SIZE - 4f;
        batch.draw(dot, ix, iy, INDICATOR_SIZE, INDICATOR_SIZE);
        batch.setColor(Color.WHITE);
    }

    // ── Companion orbs ────────────────────────────────────────────────────────

    /**
     * Render Yin (blue) and Yang (gold) companion orbs orbiting the player.
     *
     * Orb size scales with the Yin/Yang value: 6px at 0.0 → 14px at 1.0.
     * Brightness/alpha scales similarly.  Flow Mode (balanced state) doubles
     * the orbit speed and adds a white inner glow drawn behind each orb.
     *
     * Yin leads at angle θ, Yang trails at θ+π.
     */
    private void renderCompanions(SpriteBatch batch, PlayerState p, float dt) {
        if (p.isDead) return;

        // Flow Mode doubles orbit speed
        float speed = p.flowMode ? COMPANION_SPEED * 2.0f : COMPANION_SPEED;
        float angle = companionAngle.getOrDefault(p.playerId, 0f);
        angle += speed * dt;
        if (angle > (float)(2 * Math.PI)) angle -= (float)(2 * Math.PI);
        companionAngle.put(p.playerId, angle);

        float cx = p.posX + PW * 0.5f;
        float cy = p.posY + PH * 0.5f;
        TextureRegion dot = anims.getFrame("__dot__", 0f, 1f);

        // Yin orb — sky blue, leads at angle θ
        float yinSize  = 6f + p.yinValue * 8f;            // 6–14 px
        float yinAlpha = 0.55f + p.yinValue * 0.40f;      // 0.55–0.95
        float yinHalf  = yinSize * 0.5f;
        float yinX     = cx + (float) Math.cos(angle) * COMPANION_RADIUS - yinHalf;
        float yinY     = cy + (float) Math.sin(angle) * COMPANION_RADIUS - yinHalf;

        // Glow ring behind Yin orb when value > 0.7
        if (p.yinValue > 0.7f) {
            float glowSize = yinSize + 6f;
            batch.setColor(0.5f, 0.8f, 1f, 0.25f);
            batch.draw(dot, yinX - 3f, yinY - 3f, glowSize, glowSize);
        }
        // Core Yin orb — pale blue → bright sky blue
        batch.setColor(0.55f + p.yinValue * 0.3f, 0.7f + p.yinValue * 0.25f, 1f, yinAlpha);
        batch.draw(dot, yinX, yinY, yinSize, yinSize);

        // Yang orb — orange-gold, trails at θ+π
        float yangSize  = 6f + p.yangValue * 8f;
        float yangAlpha = 0.55f + p.yangValue * 0.40f;
        float yangHalf  = yangSize * 0.5f;
        float yangX     = cx + (float) Math.cos(angle + Math.PI) * COMPANION_RADIUS - yangHalf;
        float yangY     = cy + (float) Math.sin(angle + Math.PI) * COMPANION_RADIUS - yangHalf;

        // Glow ring behind Yang orb when value > 0.7
        if (p.yangValue > 0.7f) {
            float glowSize = yangSize + 6f;
            batch.setColor(1f, 0.7f, 0.1f, 0.25f);
            batch.draw(dot, yangX - 3f, yangY - 3f, glowSize, glowSize);
        }
        // Core Yang orb — dark gold → bright amber
        batch.setColor(1f, 0.45f + p.yangValue * 0.45f, 0.05f * p.yangValue, yangAlpha);
        batch.draw(dot, yangX, yangY, yangSize, yangSize);

        // Flow Mode: draw a faint white line connecting the two orbs
        if (p.flowMode) {
            batch.setColor(1f, 1f, 1f, 0.18f);
            // Approximate a line with a thin elongated rect; skip for simplicity —
            // the doubled speed is the primary visual cue.
        }

        batch.setColor(Color.WHITE);
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
        snap.npcs.forEach(n     -> live.add(n.npcId));
        snap.bosses.forEach(b   -> live.add(b.bossId));
        snap.portals.forEach(p  -> live.add(p.portalId));
        stateTimes.keySet().retainAll(live);
        lastState.keySet().retainAll(live);
        prevVelY.keySet().retainAll(live);
        prevHealth.keySet().retainAll(live);
        dustTimers.keySet().retainAll(live);
        prevTeleport.keySet().retainAll(live);
        companionAngle.keySet().retainAll(snap.players.stream()
            .map(p -> p.playerId).collect(java.util.stream.Collectors.toSet()));
    }

    // ── Debug: physics AABB hitbox overlay ───────────────────────────────────

    /**
     * Draw wireframe AABB rectangles over all entity physics boxes.
     * Toggle with H key in GameScreen.
     *
     * Colours:
     *   Cyan   — player AABB
     *   Red    — enemy AABB
     *   Orange — NPC AABB
     *   Yellow — pickup AABB
     *
     * The ShapeRenderer must be in Line mode and sharing the game camera's
     * combined projection matrix before this method is called.
     */
    public void renderHitboxes(com.badlogic.gdx.graphics.glutils.ShapeRenderer sr,
                                WorldSnapshot snap) {
        if (snap == null) return;

        // Players — cyan
        sr.setColor(0f, 1f, 1f, 1f);
        for (PlayerState p : snap.players) {
            sr.rect(p.posX, p.posY, PW, PH);
        }

        // Enemies: red body hitbox and amber attack zones (when attacking)
        for (EnemyState e : snap.enemies) {
            drawEnemyDebugHitboxes(sr, e);
        }
        for (EnemyState e : snap.overflowEnemies) {
            drawEnemyDebugHitboxes(sr, e);
        }

        // NPCs — orange
        sr.setColor(1f, 0.55f, 0.05f, 1f);
        for (com.indieniinja.network.NPCState n : snap.npcs) {
            float w = n.width > 0 ? n.width : NPC_W;
            float h = n.height > 0 ? n.height : NPC_H;
            sr.rect(n.x, n.y, w, h);
        }

        // Pickups — yellow
        sr.setColor(1f, 1f, 0.1f, 1f);
        for (com.indieniinja.network.PickupState p : snap.pickups) {
            if (p.alive) sr.rect(p.x, p.y, PhysicsConstants.TILE_SIZE, PhysicsConstants.TILE_SIZE);
        }
    }

    private void drawEnemyDebugHitboxes(com.badlogic.gdx.graphics.glutils.ShapeRenderer sr, EnemyState e) {
        String t = (e.enemyType != null && !e.enemyType.isEmpty()) ? e.enemyType : "skeleton";
        int pw = enemyPhysicsW(t);
        int ph = enemyPhysicsH(t);
        EnemyAttackGeometry.Rect hurt = EnemyAttackGeometry.hurtboxRect(t, e.x, e.y, pw, ph);

        // Enemy hurtbox (what player attacks can hit).
        sr.setColor(1f, 0.15f, 0.15f, 1f);
        sr.rect(hurt.x, hurt.y, hurt.w, hurt.h);

        // Physics body AABB (movement/collision) in dim red.
        sr.setColor(0.75f, 0.25f, 0.25f, 0.6f);
        sr.rect(e.x, e.y, pw, ph);

        // Attack zone preview while the enemy is in ATTACK state.
        if ("attack".equals(e.aiState)) {
            EnemyAttackGeometry.Rect[] rects = EnemyAttackGeometry.debugAttackRects(
                t,
                e.x, e.y,
                pw, ph,
                EnemyAttackGeometry.defaultAttackRange(t),
                e.facingRight
            );
            sr.setColor(1f, 0.72f, 0.15f, 1f);
            for (EnemyAttackGeometry.Rect r : rects) {
                sr.rect(r.x, r.y, r.w, r.h);
            }
        }
    }
}
