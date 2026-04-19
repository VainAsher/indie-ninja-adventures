package com.indieniinja.sim;

import com.indieniinja.core.EntityType;
import com.indieniinja.core.EntityTypeRegistry;

/**
 * Registers all Shadow Ascent entity types into an EntityTypeRegistry.
 *
 * Call {@link #register(EntityTypeRegistry)} once at game/server startup before
 * any simulation ticks run. Types mirror the enemy IDs in data/entities/enemies/,
 * NPC IDs in data/entities/npcs/, boss wire strings from BossType, and well-known
 * projectile/pickup names used in GameSimulator.
 */
public final class ShadowAscentEntityTypeBootstrap {

    private ShadowAscentEntityTypeBootstrap() {}

    public static void register(EntityTypeRegistry registry) {
        // ── Player ───────────────────────────────────────────────────────────
        registry.register("player",              EntityType.PLAYER);

        // ── NPCs (mirror data/entities/npcs/*.json ids) ──────────────────────
        registry.register("siren",               EntityType.NPC);
        registry.register("lore_keeper",         EntityType.NPC);
        registry.register("mission_giver",       EntityType.NPC);
        registry.register("shop_keeper",         EntityType.NPC);
        registry.register("tutorial_guide",      EntityType.NPC);

        // ── Standard enemies (mirror data/entities/enemies/*.json ids) ────────
        registry.register("skeleton",            EntityType.ENEMY);
        registry.register("archer",              EntityType.ENEMY);
        registry.register("ghost",               EntityType.ENEMY);
        registry.register("goblin",              EntityType.ENEMY);
        registry.register("slime",               EntityType.ENEMY);
        registry.register("slime_red",           EntityType.ENEMY);
        registry.register("spearman",            EntityType.ENEMY);
        registry.register("bat",                 EntityType.ENEMY);
        registry.register("time_leech",          EntityType.ENEMY);

        // ── Narrative bosses (mirror BossType.wire) ──────────────────────────
        registry.register("boss_siren",           EntityType.ENEMY);
        registry.register("boss_echo_warden",     EntityType.ENEMY);
        registry.register("boss_time_leech_lord", EntityType.ENEMY);
        registry.register("boss_memory_eater",    EntityType.ENEMY);

        // ── Campaign-authored bosses ──────────────────────────────────────────
        registry.register("boss_shadow_lord",     EntityType.ENEMY);
        registry.register("boss_fire_demon",      EntityType.ENEMY);
        registry.register("boss_ice_queen",       EntityType.ENEMY);
        registry.register("boss_necromancer",     EntityType.ENEMY);
        registry.register("boss_dragon",          EntityType.ENEMY);
        registry.register("boss_veil_maiden",     EntityType.ENEMY);

        // ── Legacy bosses (arcade/seed) ───────────────────────────────────────
        registry.register("boss_forest_guardian", EntityType.ENEMY);
        registry.register("boss_corrupt_mayor",   EntityType.ENEMY);
        registry.register("boss_crystal_golem",   EntityType.ENEMY);
        registry.register("boss_dark_knight",     EntityType.ENEMY);
        registry.register("boss_plague_rat",      EntityType.ENEMY);

        // ── Projectiles ───────────────────────────────────────────────────────
        registry.register("projectile_shuriken",  EntityType.PROJECTILE);
        registry.register("projectile_arrow",     EntityType.PROJECTILE);

        // ── Pickups ───────────────────────────────────────────────────────────
        registry.register("pickup_coin",          EntityType.PICKUP);
        registry.register("pickup_health",        EntityType.PICKUP);
        registry.register("pickup_shuriken",      EntityType.PICKUP);
        registry.register("pickup_lantern",       EntityType.PICKUP);
        registry.register("pickup_key",           EntityType.PICKUP);
        registry.register("pickup_scroll",        EntityType.PICKUP);
    }
}
