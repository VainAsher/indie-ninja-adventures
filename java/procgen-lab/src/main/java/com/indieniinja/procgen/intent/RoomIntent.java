package com.indieniinja.procgen.intent;

import com.indieniinja.procgen.model.Ability;
import com.indieniinja.procgen.model.Biome;
import com.indieniinja.procgen.model.Direction;
import com.indieniinja.procgen.model.RoomType;

import java.util.Set;

public final class RoomIntent {
    public final RoomType       type;
    public final Biome          biome;
    public final int            difficulty;
    public final Set<Ability>   requiredAbilities;
    public final Set<Direction> connections;
    public final String         emotionalTone;
    public final String         traversalGoal;
    public final boolean        criticalPath;

    public RoomIntent(
            RoomType       type,
            Biome          biome,
            int            difficulty,
            Set<Ability>   requiredAbilities,
            Set<Direction> connections,
            String         emotionalTone,
            String         traversalGoal,
            boolean        criticalPath) {
        this.type              = type;
        this.biome             = biome;
        this.difficulty        = difficulty;
        this.requiredAbilities = Set.copyOf(requiredAbilities);
        this.connections       = Set.copyOf(connections);
        this.emotionalTone     = emotionalTone;
        this.traversalGoal     = traversalGoal;
        this.criticalPath      = criticalPath;
    }
}
