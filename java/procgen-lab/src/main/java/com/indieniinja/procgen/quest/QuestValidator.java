package com.indieniinja.procgen.quest;

import com.indieniinja.procgen.dungeon.DungeonPlan;
import com.indieniinja.procgen.model.QuestType;
import com.indieniinja.procgen.validation.ValidationResult;

public final class QuestValidator {

    public ValidationResult validate(QuestPlan plan, DungeonPlan dungeon) {
        ValidationResult result = new ValidationResult();

        if (plan.quests.isEmpty()) {
            result.error("QuestPlan has no quests.");
            return result;
        }

        long mainCount = plan.quests.stream()
                .filter(q -> q.type == QuestType.MAIN).count();
        if (mainCount == 0) result.error("No MAIN quest found.");
        if (mainCount > 1)  result.warn("Multiple MAIN quests — first is authoritative.");

        for (Quest q : plan.quests) {
            if (q.objectives.isEmpty()) {
                result.error("Quest '" + q.id + "' has no objectives.");
                continue;
            }
            for (QuestObjective obj : q.objectives) {
                if (obj.targetRoomId != null
                        && dungeon.roomGraph.byId(obj.targetRoomId) == null) {
                    result.error("Quest '" + q.id + "' objective references unknown room '"
                            + obj.targetRoomId + "'.");
                }
            }
        }

        return result;
    }
}
