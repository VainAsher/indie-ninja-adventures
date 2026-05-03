package com.indieniinja.procgen.quest;

import com.indieniinja.procgen.model.Ability;
import com.indieniinja.procgen.model.RewardType;

public final class QuestReward {
    public final RewardType type;
    public final Ability    abilityUnlock; // non-null only when type == ABILITY_UNLOCK
    public final String     label;

    public QuestReward(RewardType type, Ability abilityUnlock, String label) {
        this.type          = type;
        this.abilityUnlock = abilityUnlock;
        this.label         = label;
    }
}
