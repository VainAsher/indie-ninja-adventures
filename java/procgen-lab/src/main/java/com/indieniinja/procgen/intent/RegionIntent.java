package com.indieniinja.procgen.intent;

import com.indieniinja.procgen.model.Ability;
import com.indieniinja.procgen.model.Biome;

import java.util.Set;

public final class RegionIntent {
    public final String       id;
    public final String       displayName;
    public final Biome        primaryBiome;
    public final String       emotionalTone;
    public final Set<Ability> requiredAbilities;
    public final Set<Ability> unlocks;
    public final int          difficulty;
    public final boolean      hasVillage;
    public final boolean      hasMainDungeon;
    public final boolean      hasOptionalCave;

    public RegionIntent(
            String       id,
            String       displayName,
            Biome        primaryBiome,
            String       emotionalTone,
            Set<Ability> requiredAbilities,
            Set<Ability> unlocks,
            int          difficulty,
            boolean      hasVillage,
            boolean      hasMainDungeon,
            boolean      hasOptionalCave) {
        this.id                = id;
        this.displayName       = displayName;
        this.primaryBiome      = primaryBiome;
        this.emotionalTone     = emotionalTone;
        this.requiredAbilities = Set.copyOf(requiredAbilities);
        this.unlocks           = Set.copyOf(unlocks);
        this.difficulty        = difficulty;
        this.hasVillage        = hasVillage;
        this.hasMainDungeon    = hasMainDungeon;
        this.hasOptionalCave   = hasOptionalCave;
    }
}
