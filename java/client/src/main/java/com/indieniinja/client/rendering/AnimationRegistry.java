package com.indieniinja.client.rendering;

import com.badlogic.gdx.files.FileHandle;
import com.badlogic.gdx.graphics.Pixmap;
import com.badlogic.gdx.graphics.Texture;
import com.badlogic.gdx.graphics.g2d.TextureAtlas;
import com.badlogic.gdx.graphics.g2d.TextureRegion;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Loads animation frames from either a TextureAtlas or individual spritesheet PNGs,
 * and provides O(1) frame lookup.
 *
 * Direct equivalent of Python's rendering/animation_system.py AnimationRegistry.
 *
 * Spritesheet convention: uniform 80×80 px frames, top-left origin.
 * All sheets in assets/sprites/player/ use this uniform format.
 *
 * Fallback: if no assets are present, a 1×1 magenta placeholder is used so the
 * client can run during development without the full asset pack.
 */
public final class AnimationRegistry {

    /** Sprite display size — all new template sheets are 80×80 px per frame. */
    public static final int SPRITE_W = 80;
    public static final int SPRITE_H = 80;

    /** Frames keyed by "<entity>_<state>" → TextureRegion[frameIndex] */
    private final Map<String, TextureRegion[]> frames = new HashMap<>();

    /** Textures owned by this registry (loaded from spritesheets). */
    private final List<Texture> ownedTextures = new ArrayList<>();

    /** Cache: filename → Texture, so shared sheets are loaded once. */
    private final Map<String, Texture> textureCache = new HashMap<>();

    /** Fallback region used when an animation key is not found. */
    private TextureRegion fallback;

    // ── Atlas loading ─────────────────────────────────────────────────────────

    /**
     * Load all animations from a TextureAtlas.
     * Regions named "<entity>_<state>" are grouped by that key.
     */
    public void loadAtlas(TextureAtlas atlas) {
        Map<String, Integer> maxIndex = new HashMap<>();

        for (TextureAtlas.AtlasRegion r : atlas.getRegions()) {
            maxIndex.merge(r.name, r.index, Math::max);
        }

        for (TextureAtlas.AtlasRegion r : atlas.getRegions()) {
            String key = r.name;
            int max = maxIndex.get(key);
            TextureRegion[] arr = frames.computeIfAbsent(key, k -> new TextureRegion[max + 1]);
            if (r.index >= 0 && r.index < arr.length) arr[r.index] = r;
        }

        // Replace any nulls with the first non-null frame in each strip
        for (TextureRegion[] arr : frames.values()) {
            TextureRegion first = null;
            for (TextureRegion f : arr) { if (f != null) { first = f; break; } }
            if (first != null)
                for (int i = 0; i < arr.length; i++)
                    if (arr[i] == null) arr[i] = first;
        }
    }

    // ── Spritesheet loading ───────────────────────────────────────────────────

    /**
     * Load all player animations from uniform 80×80 px spritesheets in baseDir.
     *
     * Sheet → frame counts (all 80×80 uniform):
     *   idle_spritesheet.png            8f  → player_idle, player_crouch (fallback)
     *   walk_spritesheet.png            8f  → player_walk, player_slow_walk
     *   run_spritesheet.png             8f  → player_run
     *   dash_spritesheet.png            7f  → player_dash
     *   jumpfall_spritesheet.png       10f  → player_jump (f0-4), player_fall (f5-9)
     *                                        player_air_spin (f0-4), player_wall_hang (f0-4)
     *   crouch_idle_spritesheet.png     9f  → player_crouch
     *   crouch_walk_spritesheet.png     8f  → player_crouch_walk
     *   wall_slide_spritesheet.png      4f  → player_wall_slide, player_wall_hang
     *   attack1_spritesheet.png         4f  → player_slash1, player_jump_slash,
     *                                        player_throw, player_throw_ground,
     *                                        player_throw_air, player_throw_crouch
     *   attack2_spritesheet.png         7f  → player_slash2, player_slash_air,
     *                                        player_teleport
     *   attack3_spritesheet.png        12f  → player_attack, player_slash3
     *   death_spritesheet.png           7f  → player_death
     *   hurt_spritesheet.png            4f  → player_hurt, player_hurt2
     *
     * Missing files are silently skipped; the placeholder is used as fallback.
     */
    public void loadSpriteSheets(FileHandle baseDir) {
        // Idle
        sliceAndRegister(baseDir, "player_idle",   "idle_spritesheet.png", 8);

        // Walk / run / dash
        sliceAndRegister(baseDir, "player_walk",       "walk_spritesheet.png", 8);
        sliceAndRegister(baseDir, "player_slow_walk",  "walk_spritesheet.png", 8);
        sliceAndRegister(baseDir, "player_run",        "run_spritesheet.png",  8);
        sliceAndRegister(baseDir, "player_dash",       "dash_spritesheet.png", 7);

        // Jump / fall — split 10-frame sheet: f0-4 = jump, f5-9 = fall
        registerJumpFall(baseDir, "jumpfall_spritesheet.png");
        sliceSubsetAndRegister(baseDir, "player_air_spin",  "jumpfall_spritesheet.png", 10, 0, 5);
        sliceSubsetAndRegister(baseDir, "player_wall_hang", "jumpfall_spritesheet.png", 10, 0, 5);

        // Crouch
        sliceAndRegister(baseDir, "player_crouch",      "crouch_idle_spritesheet.png", 9);
        sliceAndRegister(baseDir, "player_crouch_walk", "crouch_walk_spritesheet.png", 8);

        // Wall slide
        sliceAndRegister(baseDir, "player_wall_slide", "wall_slide_spritesheet.png", 4);

        // Attack — 3 combos of increasing length
        sliceAndRegister(baseDir, "player_attack",      "attack3_spritesheet.png", 12);
        sliceAndRegister(baseDir, "player_slash3",      "attack3_spritesheet.png", 12);
        sliceAndRegister(baseDir, "player_slash2",      "attack2_spritesheet.png",  7);
        sliceAndRegister(baseDir, "player_slash_air",   "attack2_spritesheet.png",  7);
        sliceAndRegister(baseDir, "player_slash1",      "attack1_spritesheet.png",  4);
        sliceAndRegister(baseDir, "player_jump_slash",  "attack1_spritesheet.png",  4);

        // Throw / teleport reuse attack sheets
        sliceAndRegister(baseDir, "player_throw",        "attack1_spritesheet.png", 4);
        sliceAndRegister(baseDir, "player_throw_ground", "attack1_spritesheet.png", 4);
        sliceAndRegister(baseDir, "player_throw_air",    "attack1_spritesheet.png", 4);
        sliceAndRegister(baseDir, "player_throw_crouch", "attack1_spritesheet.png", 4);
        sliceAndRegister(baseDir, "player_teleport",     "attack2_spritesheet.png", 7);

        // Hurt / death
        sliceAndRegister(baseDir, "player_hurt",  "hurt_spritesheet.png",  4);
        sliceAndRegister(baseDir, "player_hurt2", "hurt_spritesheet.png",  4);
        sliceAndRegister(baseDir, "player_death", "death_spritesheet.png", 7);
    }

    // ── Unarmed / Sword template sheet loading ────────────────────────────────

    /**
     * Load all unarmed player animations from assets/sprites/player/unarmed/.
     *
     * Supersedes loadSpriteSheets() — call after it (or instead of it) when the
     * extracted template sheets are present.  All keys use the "player_" prefix.
     *
     * Frame counts are authoritative from the extracted PNG dimensions (80×80 px).
     */
    public void loadUnarmedSheets(FileHandle d) {
        // Core locomotion
        sliceAndRegister(d, "player_idle",          "idle_spritesheet.png",         8);
        sliceAndRegister(d, "player_combat_idle",   "combat_idle_spritesheet.png",  8);
        sliceAndRegister(d, "player_walk",          "walk_spritesheet.png",         8);
        sliceAndRegister(d, "player_slow_walk",     "walk_spritesheet.png",         8);
        sliceAndRegister(d, "player_run",           "run_spritesheet.png",          8);
        sliceAndRegister(d, "player_dash",          "dash_spritesheet.png",         7);
        sliceAndRegister(d, "player_run_stop",      "run_stop_spritesheet.png",     3);
        sliceAndRegister(d, "player_skid",          "skid_spritesheet.png",         4);
        sliceAndRegister(d, "player_flip",          "flip_spritesheet.png",         6);
        sliceAndRegister(d, "player_roll",          "roll_spritesheet.png",         8);
        sliceAndRegister(d, "player_slide",         "slide_spritesheet.png",        6);

        // Jump / fall (split from 10-frame sheet)
        registerJumpFall(d, "jumpfall_spritesheet.png");
        sliceSubsetAndRegister(d, "player_air_spin",  "jumpfall_spritesheet.png", 10, 0, 5);
        sliceSubsetAndRegister(d, "player_wall_hang", "jumpfall_spritesheet.png", 10, 0, 5);

        // Crouch
        sliceAndRegister(d, "player_crouch",        "crouch_idle_spritesheet.png",  9);
        sliceAndRegister(d, "player_crouch_walk",   "crouch_walk_spritesheet.png",  8);
        sliceAndRegister(d, "player_crouch_punch",  "crouch_punch_spritesheet.png", 5);
        sliceAndRegister(d, "player_crouch_kick",   "crouch_kick_spritesheet.png",  6);

        // Wall / climb
        sliceAndRegister(d, "player_wall_slide",    "wall_slide_spritesheet.png",   4);
        sliceAndRegister(d, "player_wall_land",     "wall_land_spritesheet.png",    4);
        sliceAndRegister(d, "player_climb",         "climb_side_spritesheet.png",   6);
        sliceAndRegister(d, "player_climb_idle",    "climb_idle_side_spritesheet.png", 8);
        sliceAndRegister(d, "player_climb_left",    "climb_left_spritesheet.png",   6);
        sliceAndRegister(d, "player_climb_right",   "climb_right_spritesheet.png",  6);
        sliceAndRegister(d, "player_climb_back",    "climb_back_spritesheet.png",   6);

        // Ledge
        sliceAndRegister(d, "player_ledge",         "ledge_idle_spritesheet.png",   8);
        sliceAndRegister(d, "player_ledge_idle",    "ledge_idle_spritesheet.png",   8);
        sliceAndRegister(d, "player_ledge_grab",    "ledge_grab_spritesheet.png",   2);
        sliceAndRegister(d, "player_ledge_climb",   "ledge_climb_spritesheet.png",  4);

        // Rope
        sliceAndRegister(d, "player_rope",          "rope_idle_spritesheet.png",    4);
        sliceAndRegister(d, "player_rope_idle",     "rope_idle_spritesheet.png",    4);
        sliceAndRegister(d, "player_rope_swing",    "rope_swing_spritesheet.png",   7);

        // Swim
        sliceAndRegister(d, "player_swim",               "swim_spritesheet.png",          6);
        sliceAndRegister(d, "player_swim_idle",           "swim_idle_spritesheet.png",     8);
        sliceAndRegister(d, "player_swim_up",             "swim_up_spritesheet.png",       6);
        sliceAndRegister(d, "player_swim_down",           "swim_down_spritesheet.png",     6);
        sliceAndRegister(d, "player_swim_surface",        "swim_surface_spritesheet.png",  6);
        sliceAndRegister(d, "player_swim_surface_idle",   "swim_surface_idle_spritesheet.png", 8);

        // Unarmed combat
        sliceAndRegister(d, "player_punch1",        "punch1_spritesheet.png",        6);
        sliceAndRegister(d, "player_punch2",        "punch2_spritesheet.png",        8);
        sliceAndRegister(d, "player_air_punch1",    "air_punch1_spritesheet.png",    6);
        sliceAndRegister(d, "player_air_punch2",    "air_punch2_spritesheet.png",    8);
        sliceAndRegister(d, "player_kick",          "kick_spritesheet.png",          6);
        sliceAndRegister(d, "player_air_kick",      "air_kick_spritesheet.png",      6);
        sliceAndRegister(d, "player_run_kick",      "run_kick_spritesheet.png",      6);
        sliceAndRegister(d, "player_crouch_punch",  "crouch_punch_spritesheet.png",  5);
        sliceAndRegister(d, "player_crouch_kick",   "crouch_kick_spritesheet.png",   6);
        // Map engine attack aliases to unarmed combo punches
        sliceAndRegister(d, "player_attack",        "punch2_spritesheet.png",        8);
        sliceAndRegister(d, "player_slash1",        "punch1_spritesheet.png",        6);
        sliceAndRegister(d, "player_slash2",        "punch2_spritesheet.png",        8);
        sliceAndRegister(d, "player_slash3",        "punch2_spritesheet.png",        8);
        sliceAndRegister(d, "player_slash_air",     "air_punch2_spritesheet.png",    8);
        sliceAndRegister(d, "player_jump_slash",    "air_punch1_spritesheet.png",    6);
        sliceAndRegister(d, "player_throw",         "pickup_spritesheet.png",        5);
        sliceAndRegister(d, "player_throw_ground",  "pickup_spritesheet.png",        5);
        sliceAndRegister(d, "player_throw_air",     "pickup_spritesheet.png",        5);
        sliceAndRegister(d, "player_throw_crouch",  "pickup_crouch_spritesheet.png", 4);
        sliceAndRegister(d, "player_teleport",      "roll_spritesheet.png",          8);

        // Block stances
        sliceAndRegister(d, "player_block",             "block_idle_spritesheet.png",       8);
        sliceAndRegister(d, "player_block_idle",        "block_idle_spritesheet.png",       8);
        sliceAndRegister(d, "player_block_hit",         "block_hit_normal_spritesheet.png", 3);
        sliceAndRegister(d, "player_block_hit_hard",    "block_hit_hard_spritesheet.png",   6);
        sliceAndRegister(d, "player_air_block",         "air_block_spritesheet.png",       10);
        sliceAndRegister(d, "player_air_block_hit",     "air_block_hit_spritesheet.png",    3);
        sliceAndRegister(d, "player_crouch_block",      "crouch_block_spritesheet.png",     8);
        sliceAndRegister(d, "player_crouch_block_hit",  "crouch_block_hit_spritesheet.png", 3);

        // Hurt / death
        sliceAndRegister(d, "player_hurt",          "hurt_upper_spritesheet.png",    4);
        sliceAndRegister(d, "player_hurt2",         "hurt_lower_spritesheet.png",    4);
        sliceAndRegister(d, "player_crouch_hurt",   "crouch_hurt_spritesheet.png",   4);
        sliceAndRegister(d, "player_death",         "death_spritesheet.png",         7);
        sliceAndRegister(d, "player_death2",        "death2_spritesheet.png",        7);
        sliceAndRegister(d, "player_prone_hurt",    "prone_hurt_spritesheet.png",    4);
        sliceAndRegister(d, "player_prone_death",   "prone_death_spritesheet.png",   5);
        sliceAndRegister(d, "player_prone_idle",    "prone_idle_spritesheet.png",    9);
        sliceAndRegister(d, "player_prone_revive",  "prone_revive_spritesheet.png",  5);
        sliceAndRegister(d, "player_prone_walk",    "prone_walk_spritesheet.png",    8);

        // Interactive / pickup
        sliceAndRegister(d, "player_pickup",        "pickup_spritesheet.png",        5);
        sliceAndRegister(d, "player_pickup_crouch", "pickup_crouch_spritesheet.png", 4);
        sliceAndRegister(d, "player_pull",          "pull_spritesheet.png",          8);
        sliceAndRegister(d, "player_push",          "push_spritesheet.png",          8);
        sliceAndRegister(d, "player_push_idle",     "push_idle_spritesheet.png",     8);
        sliceAndRegister(d, "player_drink",         "drink_spritesheet.png",         8);
        sliceAndRegister(d, "player_revive",        "revive_spritesheet.png",        6);
        sliceAndRegister(d, "player_revive2",       "revive2_spritesheet.png",       6);
        sliceAndRegister(d, "player_button",        "button_spritesheet.png",        5);
        sliceAndRegister(d, "player_lever",         "lever_spritesheet.png",         9);
        sliceAndRegister(d, "player_chest_back",    "chest_back_spritesheet.png",    6);
        sliceAndRegister(d, "player_chest_side",    "chest_side_spritesheet.png",    5);
        sliceAndRegister(d, "player_door_enter",    "door_enter_spritesheet.png",   10);
        sliceAndRegister(d, "player_door_exit",     "door_exit_spritesheet.png",    10);

        // Social / emote
        sliceAndRegister(d, "player_sit",           "sit_spritesheet.png",          12);
        sliceAndRegister(d, "player_sleep",         "sleep_spritesheet.png",        15);
        sliceAndRegister(d, "player_talk",          "talk_spritesheet.png",          9);
        sliceAndRegister(d, "player_dance",         "dance_spritesheet.png",        12);
        sliceAndRegister(d, "player_fidget",        "fidget_spritesheet.png",        8);
        sliceAndRegister(d, "player_victory",       "victory_spritesheet.png",      10);
    }

    /**
     * Load sword weapon-state animations from assets/sprites/player/sword/.
     *
     * Registers keys with the "player_sword_" prefix used by EntityRenderer's
     * weapon-routing logic.  Only keys where the sword animation differs from
     * unarmed are registered here; all other states fall through to unarmed
     * automatically.
     *
     * Must be called after loadUnarmedSheets() or loadSpriteSheets() so the
     * unarmed fallback keys exist.
     */
    public void loadSwordSheets(FileHandle d) {
        // Locomotion — sword-specific idle/movement frames
        sliceAndRegister(d, "player_sword_idle",        "idle_spritesheet.png",       8);
        sliceAndRegister(d, "player_sword_combat_idle", "combat_idle_spritesheet.png",8);
        sliceAndRegister(d, "player_sword_walk",        "walk_spritesheet.png",       8);
        sliceAndRegister(d, "player_sword_slow_walk",   "walk_spritesheet.png",       8);
        sliceAndRegister(d, "player_sword_run",         "run_spritesheet.png",        8);
        sliceAndRegister(d, "player_sword_dash",        "dash_spritesheet.png",       7);

        // Jump / fall split
        registerJumpFallPrefixed(d, "jumpfall_spritesheet.png", "player_sword");

        // Crouch
        sliceAndRegister(d, "player_sword_crouch",      "crouch_idle_spritesheet.png",9);
        sliceAndRegister(d, "player_sword_crouch_walk", "crouch_walk_spritesheet.png",8);

        // Sword attack combos  (d0/d1/d2 = hit 1/2/3 of standing combo)
        sliceAndRegister(d, "player_sword_attack",         "attack_combo_d0_spritesheet.png", 4);
        sliceAndRegister(d, "player_sword_slash1",         "attack_combo_d0_spritesheet.png", 4);
        sliceAndRegister(d, "player_sword_slash2",         "attack_combo_d1_spritesheet.png", 7);
        sliceAndRegister(d, "player_sword_slash3",         "attack_combo_d2_spritesheet.png",12);
        sliceAndRegister(d, "player_sword_air_attack",     "air_attack_d0_spritesheet.png",   4);
        sliceAndRegister(d, "player_sword_air_slash",      "air_attack_d1_spritesheet.png",   7);
        sliceAndRegister(d, "player_sword_slash_air",      "air_attack_d1_spritesheet.png",   7);
        sliceAndRegister(d, "player_sword_jump_slash",     "air_attack_d0_spritesheet.png",   4);
        sliceAndRegister(d, "player_sword_crouch_attack",  "crouch_attack_d0_spritesheet.png",4);
        sliceAndRegister(d, "player_sword_crouch_slash",   "crouch_attack_d1_spritesheet.png",7);
        sliceAndRegister(d, "player_sword_dash_attack",    "dash_attack_spritesheet.png",     7);
        sliceAndRegister(d, "player_sword_stab",           "stab_combo_spritesheet.png",      4);

        // Hurt / death — sword variant looks the same as unarmed but use the
        // sword directory so artists can override per-weapon later
        sliceAndRegister(d, "player_sword_hurt",   "hurt_upper_spritesheet.png", 4);
        sliceAndRegister(d, "player_sword_hurt2",  "hurt_lower_spritesheet.png", 4);
        sliceAndRegister(d, "player_sword_death",  "death_spritesheet.png",      7);
    }

    /**
     * Variant of registerJumpFall that writes to "{prefix}_jump" / "{prefix}_fall"
     * keys instead of always "player_jump" / "player_fall".
     */
    private void registerJumpFallPrefixed(FileHandle baseDir, String filename,
                                           String prefix) {
        Texture tex = loadCached(baseDir, filename);
        if (tex == null) return;
        int fw = tex.getWidth() / 10;
        int fh = tex.getHeight();
        TextureRegion[] jump = new TextureRegion[5];
        TextureRegion[] fall = new TextureRegion[5];
        for (int i = 0; i < 5; i++) {
            jump[i] = new TextureRegion(tex, i * fw, 0, fw, fh);
            jump[i].flip(false, true);
        }
        for (int i = 0; i < 5; i++) {
            fall[i] = new TextureRegion(tex, (i + 5) * fw, 0, fw, fh);
            fall[i].flip(false, true);
        }
        frames.put(prefix + "_jump", jump);
        frames.put(prefix + "_fall", fall);
    }

    // ── Enemy sprite loading ──────────────────────────────────────────────────

    /**
     * Load enemy animations from the stitched spritesheet directory produced by
     * tools/stitch_enemy_frames.py.
     *
     * Expected structure: baseDir/<type>/<state>.png  (horizontal strips)
     *   swordsman/ idle.png walk.png attack_a.png attack_b.png hit.png dead.png jump.png
     *   skeleton/  idle.png walk.png attack_a.png attack_b.png hit.png dead.png jump.png shield_block.png
     *   slime/     idle.png walk.png attack_a.png attack_b.png attack_c.png hit.png dead.png
     *   grunt/     idle.png walk.png attack_a.png attack_b.png hit.png dead.png jump.png
     *   wolf/      idle.png run.png  attack_a.png attack_b.png hit.png dead.png jump.png
     *
     * Registered keys: "enemy_<type>_<aiState>" — consumed by EntityRenderer.renderEnemy().
     * AI states covered: idle, patrol, chase, flee, attack, guard (skeleton), stunned, dead, jump.
     *
     * Missing files are silently skipped; colored placeholders remain for that key.
     * Must be called after loadEnemySprites() so the placeholder fallbacks exist.
     */
    public void loadEnemySheets(FileHandle baseDir) {
        // Frame counts per type+state (from dimension audit after stitch script runs)
        loadEnemySheetType(baseDir, "swordsman", new int[]{2, 6, 6, 0, 6, 10, 0, 3, 4, 5});
        loadEnemySheetType(baseDir, "skeleton",  new int[]{4, 6, 6, 0, 12, 7, 2, 3, 4, 5});
        loadEnemySheetType(baseDir, "slime",     new int[]{4, 4, 4, 0, 10, 11, 8, 3, 5, 0});
        loadEnemySheetType(baseDir, "grunt",     new int[]{4, 6, 6, 0, 6, 10, 0, 3, 4, 5});
        loadEnemySheetType(baseDir, "wolf",      new int[]{2, 12, 12, 0, 8, 11, 0, 4, 4, 6});
        // "goblin" alias → swordsman art (backward compat with existing snapshots)
        loadEnemySheetType(baseDir, "swordsman", "goblin", new int[]{2, 6, 6, 0, 6, 10, 0, 3, 4, 5});
    }

    /**
     * Load one enemy type's animated states from baseDir/<type>/.
     * frameCounts index: [idle, walk/patrol, run/chase, flee, attack_a, attack_b,
     *                     shield_block/guard, hit/stunned, dead, jump]
     */
    private void loadEnemySheetType(FileHandle baseDir, String type, int[] fc) {
        loadEnemySheetType(baseDir, type, type, fc);
    }

    private void loadEnemySheetType(FileHandle baseDir, String srcType, String regType, int[] fc) {
        FileHandle d = baseDir.child(srcType);
        String p = "enemy_" + regType + "_";

        // idle
        if (fc[0] > 0) loadIfExistsEnemy(d, p + "idle",    "idle.png",          fc[0]);
        // patrol → walk sheet
        if (fc[1] > 0) loadIfExistsEnemy(d, p + "patrol",  "walk.png",          fc[1]);
        // chase → run sheet, else walk
        boolean hasRun = d.child("run.png").exists();
        int chaseF = hasRun ? (fc[2] > 0 ? fc[2] : fc[1]) : fc[1];
        loadIfExistsEnemy(d, p + "chase", hasRun ? "run.png" : "walk.png", chaseF);
        // flee → same sheet as chase (direction flip handled by renderer)
        loadIfExistsEnemy(d, p + "flee",  hasRun ? "run.png" : "walk.png", chaseF);
        // attack_a
        if (fc[4] > 0) loadIfExistsEnemy(d, p + "attack",   "attack_a.png",     fc[4]);
        // attack_b (secondary; renderer can query "enemy_<type>_attack_b" explicitly)
        if (fc[5] > 0) loadIfExistsEnemy(d, p + "attack_b", "attack_b.png",     fc[5]);
        // attack_c (slime only)
        if (d.child("attack_c.png").exists())
            loadIfExistsEnemy(d, p + "attack_c", "attack_c.png", 8);
        // guard → shield_block sheet (skeleton); falls back to idle for others
        if (fc[6] > 0) loadIfExistsEnemy(d, p + "guard", "shield_block.png",    fc[6]);
        // stunned → hit sheet
        if (fc[7] > 0) loadIfExistsEnemy(d, p + "stunned", "hit.png",           fc[7]);
        // dead → death sheet
        if (fc[8] > 0) loadIfExistsEnemy(d, p + "dead",    "dead.png",          fc[8]);
        // jump (airborne)
        if (fc[9] > 0) loadIfExistsEnemy(d, p + "jump",    "jump.png",          fc[9]);
    }

    /** Load a spritesheet only if the file exists; silently skip otherwise. */
    private void loadIfExistsEnemy(FileHandle dir, String key, String filename, int frameCount) {
        Texture tex = loadCached(dir, filename);
        if (tex == null) return;
        frames.put(key, sliceSheet(tex, frameCount));
    }

    /**
     * Load per-enemy-type animations from assets/sprites/characters/{type}/.
     *
     * Expected sheets (all uniform horizontal strips, same 80×80 frame format):
     *   idle_spritesheet.png, walk_spritesheet.png, run_spritesheet.png,
     *   attack_spritesheet.png, hurt_spritesheet.png, death_spritesheet.png
     *
     * Registered keys: "enemy_{type}_{aiState}" where aiState ∈ {idle, patrol,
     * chase, attack, stunned, dead} — maps patrol→walk, chase→run (or walk),
     * stunned→hurt (or idle), dead→death (or hurt).
     *
     * Missing sheets fall back to a per-type solid-color placeholder so different
     * enemy types are visually distinct before the full asset pack is available:
     *   goblin=green, slime=blue, skeleton=gray, wolf=orange
     */
    public void loadEnemySprites(FileHandle charactersDir) {
        // type, placeholder color (r,g,b), sprite-states[], frame-counts[]
        loadEnemyType(charactersDir, "goblin",   0.2f, 0.8f, 0.2f,
            new String[]{"idle","walk","run","attack","hurt","death"},
            new int[]   {2,     4,     4,    4,       2,     4});
        loadEnemyType(charactersDir, "slime",    0.2f, 0.4f, 1.0f,
            new String[]{"idle","walk","attack"},
            new int[]   {2,     4,     4});
        loadEnemyType(charactersDir, "skeleton", 0.85f, 0.85f, 0.85f,
            new String[]{"idle","walk","attack"},
            new int[]   {2,     4,     4});
        loadEnemyType(charactersDir, "wolf",     1.0f, 0.5f, 0.1f,
            new String[]{"idle","walk","run","attack"},
            new int[]   {2,     4,     6,    4});
    }

    /**
     * Register all AI-state animations for one enemy type.
     * For each AI state, tries the primary sprite, falls back to a secondary, then
     * registers a solid-color placeholder if neither sheet exists.
     *
     * AI state → primary sprite → fallback sprite:
     *   idle    → idle   → (none)
     *   patrol  → walk   → idle
     *   chase   → run    → walk
     *   attack  → attack → idle
     *   stunned → hurt   → idle
     *   dead    → death  → hurt
     */
    private void loadEnemyType(FileHandle charactersDir, String type,
            float r, float g, float b,
            String[] spriteStates, int[] frameCounts) {
        FileHandle typeDir = charactersDir.child(type);

        // Build sprite-state → frame-count lookup
        java.util.Map<String, Integer> fcMap = new java.util.HashMap<>();
        for (int i = 0; i < spriteStates.length; i++) fcMap.put(spriteStates[i], frameCounts[i]);

        // AI state mappings: {aiState, primarySprite, fallbackSprite (or null)}
        String[][] mappings = {
            {"idle",    "idle",   null   },
            {"patrol",  "walk",   "idle" },
            {"chase",   "run",    "walk" },
            {"attack",  "attack", "idle" },
            {"stunned", "hurt",   "idle" },
            {"dead",    "death",  "hurt" },
        };

        for (String[] m : mappings) {
            String aiState      = m[0];
            String primary      = m[1];
            String fallbackSprite = m[2];
            String animKey      = "enemy_" + type + "_" + aiState;

            boolean loaded = tryLoadEnemyAnim(typeDir, animKey, primary, fcMap);
            if (!loaded && fallbackSprite != null)
                loaded = tryLoadEnemyAnim(typeDir, animKey, fallbackSprite, fcMap);
            if (!loaded)
                registerColoredPlaceholder(animKey, r, g, b);
        }
    }

    /**
     * Attempt to load a specific sprite-state sheet and register it under animKey.
     * Returns true if the sheet was found and registered.
     */
    private boolean tryLoadEnemyAnim(FileHandle typeDir, String animKey,
            String spriteState, java.util.Map<String, Integer> fcMap) {
        String filename = spriteState + "_spritesheet.png";
        int fc = fcMap.getOrDefault(spriteState, 2);
        Texture tex = loadCached(typeDir, filename);
        if (tex == null) return false;
        frames.put(animKey, sliceSheet(tex, fc));
        return true;
    }

    /**
     * Register a 1×1 solid-color placeholder for animKey (if not already registered).
     * Used so different enemy types render with distinct colors before assets are loaded.
     */
    private void registerColoredPlaceholder(String animKey, float r, float g, float b) {
        if (frames.containsKey(animKey)) return;
        Pixmap pix = new Pixmap(1, 1, Pixmap.Format.RGBA8888);
        pix.setColor(r, g, b, 1f);
        pix.fill();
        Texture tex = new Texture(pix);
        pix.dispose();
        ownedTextures.add(tex);
        frames.put(animKey, new TextureRegion[]{ new TextureRegion(tex) });
    }

    // ── Placeholder ───────────────────────────────────────────────────────────

    // ── NPC sprite loading ────────────────────────────────────────────────────

    /**
     * Load per-NPC-type animations from assets/sprites/npc/{type}/.
     *
     * Expected sheets (uniform horizontal strips, 80×80 px per frame):
     *   idle_spritesheet.png (2 frames), walk_spritesheet.png (4 frames)
     *
     * Registered keys: "npc_{type}_{aiState}" where aiState ∈ {idle, walk}.
     * Falls back to a violet solid-color placeholder for all NPC types when
     * sheets are absent, so NPCs render visibly before assets are available.
     *
     * Also registers the "__dot__" key used for interaction indicators and
     * companion orbs (1×1 white pixel, tinted at draw time via batch.setColor).
     */
    public void loadNpcSprites(FileHandle npcBaseDir) {
        registerDotTexture();

        String[] npcTypes = {"lore", "shop", "mission_giver", "tutorial"};
        for (String type : npcTypes) {
            FileHandle typeDir = npcBaseDir.child(type);
            boolean loadedIdle = tryLoadEnemyAnim(typeDir, "npc_" + type + "_idle", "idle",
                java.util.Map.of("idle", 2, "walk", 4));
            boolean loadedWalk = tryLoadEnemyAnim(typeDir, "npc_" + type + "_walk", "walk",
                java.util.Map.of("idle", 2, "walk", 4));
            // Violet placeholder for any missing state
            if (!loadedIdle) registerColoredPlaceholder("npc_" + type + "_idle", 0.6f, 0.2f, 0.9f);
            if (!loadedWalk) registerColoredPlaceholder("npc_" + type + "_walk", 0.6f, 0.2f, 0.9f);
        }
    }

    /**
     * Register a 1×1 white texture under "__dot__" for use as a tintable rect.
     * Used by: interaction indicator "!", companion orbs (Yin/Yang).
     */
    private void registerDotTexture() {
        if (frames.containsKey("__dot__")) return;
        Pixmap pix = new Pixmap(1, 1, Pixmap.Format.RGBA8888);
        pix.setColor(1f, 1f, 1f, 1f);
        pix.fill();
        Texture tex = new Texture(pix);
        pix.dispose();
        ownedTextures.add(tex);
        frames.put("__dot__", new TextureRegion[]{ new TextureRegion(tex) });
    }

    // ── Placeholder ───────────────────────────────────────────────────────────

    /**
     * Create a 1×1 magenta placeholder.  Called automatically when a key is
     * missing, so explicit calls are only needed for pre-warming.
     */
    public void loadPlaceholder() {
        if (fallback != null) return;
        Pixmap pix = new Pixmap(1, 1, Pixmap.Format.RGBA8888);
        pix.setColor(1f, 0f, 1f, 1f);
        pix.fill();
        fallback = new TextureRegion(new Texture(pix));
        pix.dispose();
    }

    // ── Query ─────────────────────────────────────────────────────────────────

    /**
     * @param key       "<entity>_<state>"  e.g. "player_idle"
     * @param stateTime seconds since this animation state started
     * @param fps       animation playback speed (frames per second)
     * @return          the TextureRegion to render, never null
     */
    public TextureRegion getFrame(String key, float stateTime, float fps) {
        TextureRegion[] strip = frames.get(key);
        if (strip == null || strip.length == 0) return getFallback();
        int idx = (int) (stateTime * fps) % strip.length;
        TextureRegion r = strip[idx];
        return r != null ? r : getFallback();
    }

    /** True if the animation key has been registered. */
    public boolean has(String key) {
        return frames.containsKey(key);
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    /**
     * Load (or reuse a cached) texture from baseDir/filename, slice into numFrames
     * equal horizontal strips, and register under animKey.
     */
    private void sliceAndRegister(FileHandle baseDir, String animKey,
                                   String filename, int numFrames) {
        Texture tex = loadCached(baseDir, filename);
        if (tex == null) return;
        frames.put(animKey, sliceSheet(tex, numFrames));
    }

    /**
     * Register a contiguous subset of frames from a uniformly-sliced sheet.
     *
     * @param totalFrames  total frame count in the sheet (for computing frame width)
     * @param startFrame   first frame index to include (inclusive)
     * @param count        number of frames to include
     */
    private void sliceSubsetAndRegister(FileHandle baseDir, String animKey,
                                         String filename, int totalFrames,
                                         int startFrame, int count) {
        Texture tex = loadCached(baseDir, filename);
        if (tex == null) return;
        int fw = tex.getWidth() / totalFrames;
        int fh = tex.getHeight();
        TextureRegion[] regions = new TextureRegion[count];
        for (int i = 0; i < count; i++) {
            regions[i] = new TextureRegion(tex, (startFrame + i) * fw, 0, fw, fh);
            regions[i].flip(false, true);
        }
        frames.put(animKey, regions);
    }

    /**
     * Split a 10-frame jumpfall sheet into player_jump (f0-4) and player_fall (f5-9).
     */
    private void registerJumpFall(FileHandle baseDir, String filename) {
        Texture tex = loadCached(baseDir, filename);
        if (tex == null) return;
        int fw = tex.getWidth() / 10;
        int fh = tex.getHeight();
        TextureRegion[] jump = new TextureRegion[5];
        TextureRegion[] fall = new TextureRegion[5];
        for (int i = 0; i < 5; i++) {
            jump[i] = new TextureRegion(tex, i * fw, 0, fw, fh);
            jump[i].flip(false, true);
        }
        for (int i = 0; i < 5; i++) {
            fall[i] = new TextureRegion(tex, (i + 5) * fw, 0, fw, fh);
            fall[i].flip(false, true);
        }
        frames.put("player_jump", jump);
        frames.put("player_fall", fall);
    }

    /**
     * Slice a texture into numFrames equal-width horizontal frames.
     *
     * Regions are flipped vertically (flip Y) because the game uses a Y-DOWN camera
     * (setToOrtho(true)).  In Y-DOWN mode SpriteBatch maps V=0 (image top) to the
     * world-bottom of the quad, which would render every sprite upside-down.
     * Pre-flipping the UV here is the standard fix.
     */
    private static TextureRegion[] sliceSheet(Texture tex, int numFrames) {
        int fw = tex.getWidth() / numFrames;
        int fh = tex.getHeight();
        TextureRegion[] regions = new TextureRegion[numFrames];
        for (int i = 0; i < numFrames; i++) {
            regions[i] = new TextureRegion(tex, i * fw, 0, fw, fh);
            regions[i].flip(false, true);  // correct orientation for Y-DOWN camera
        }
        return regions;
    }

    /**
     * Load a texture from baseDir/filename, caching it so shared sheets
     * (e.g. walk/slow_walk, hurt/hurt2) are only loaded once.
     */
    private Texture loadCached(FileHandle baseDir, String filename) {
        // Use full path as cache key so subdirectories (e.g. characters/goblin/ vs
        // characters/skeleton/) with identically-named sheets don't collide.
        String cacheKey = baseDir.path() + "/" + filename;
        if (textureCache.containsKey(cacheKey)) {
            return textureCache.get(cacheKey);  // may be null if file absent
        }
        FileHandle fh = baseDir.child(filename);
        Texture tex = null;
        if (fh.exists()) {
            tex = new Texture(fh);
            ownedTextures.add(tex);
        }
        textureCache.put(cacheKey, tex);
        return tex;
    }

    private TextureRegion getFallback() {
        loadPlaceholder();
        return fallback;
    }

    // ── Dispose ───────────────────────────────────────────────────────────────

    public void dispose() {
        for (Texture t : ownedTextures) t.dispose();
        ownedTextures.clear();
        textureCache.clear();
        if (fallback != null) {
            fallback.getTexture().dispose();
            fallback = null;
        }
    }
}
