package com.indieniinja.procgen.intent;

import com.indieniinja.procgen.model.Ability;
import com.indieniinja.procgen.model.Biome;

public final class DungeonIntent {
    public final String  id;
    public final String  displayName;
    public final Biome   biome;
    public final String  purpose;
    public final Ability abilityFocus;
    public final int     roomCount;
    public final int     difficulty;
    public final boolean hasBoss;
    public final boolean hasShortcut;
    public final boolean hasTreasureBranch;

    public DungeonIntent(
            String  id,
            String  displayName,
            Biome   biome,
            String  purpose,
            Ability abilityFocus,
            int     roomCount,
            int     difficulty,
            boolean hasBoss,
            boolean hasShortcut,
            boolean hasTreasureBranch) {
        this.id                = id;
        this.displayName       = displayName;
        this.biome             = biome;
        this.purpose           = purpose;
        this.abilityFocus      = abilityFocus;
        this.roomCount         = roomCount;
        this.difficulty        = difficulty;
        this.hasBoss           = hasBoss;
        this.hasShortcut       = hasShortcut;
        this.hasTreasureBranch = hasTreasureBranch;
    }
}
