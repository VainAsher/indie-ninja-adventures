package com.indieniinja.procgen.quest;

import com.indieniinja.procgen.dungeon.DungeonPlan;
import com.indieniinja.procgen.dungeon.DungeonPlanner;
import com.indieniinja.procgen.intent.DungeonIntent;
import com.indieniinja.procgen.model.Ability;
import com.indieniinja.procgen.model.Biome;
import com.indieniinja.procgen.model.QuestType;
import com.indieniinja.procgen.validation.ValidationResult;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class QuestGeneratorTest {

    @Test
    void generatesNonNullPlan() {
        assertThat(new QuestGenerator().generate(dungeon())).isNotNull();
    }

    @Test
    void planHasAtLeastOneQuest() {
        assertThat(new QuestGenerator().generate(dungeon()).quests).isNotEmpty();
    }

    @Test
    void mainQuestExists() {
        QuestPlan plan = new QuestGenerator().generate(dungeon());
        assertThat(plan.quests).anyMatch(q -> q.type == QuestType.MAIN);
        assertThat(plan.mainQuest()).isNotNull();
    }

    @Test
    void allQuestsHaveObjectives() {
        for (Quest q : new QuestGenerator().generate(dungeon()).quests) {
            assertThat(q.objectives)
                    .as("Quest '%s' must have objectives", q.id)
                    .isNotEmpty();
        }
    }

    @Test
    void sideQuestPresentWhenTreasureBranchExists() {
        QuestPlan plan = new QuestGenerator().generate(dungeon());
        assertThat(plan.quests).anyMatch(q -> q.type == QuestType.SIDE);
    }

    @Test
    void validatorPassesForGeneratedPlan() {
        DungeonPlan dungeon = dungeon();
        QuestPlan plan = new QuestGenerator().generate(dungeon);
        ValidationResult result = new QuestValidator().validate(plan, dungeon);
        assertThat(result.valid)
                .as("validator errors: %s", result.errors)
                .isTrue();
    }

    // -------------------------------------------------------------------------

    private static DungeonPlan dungeon() {
        DungeonIntent intent = new DungeonIntent(
                "test", "Test Dungeon", Biome.DUNGEON, "test",
                Ability.DASH, 8, 1, true, true, true);
        return new DungeonPlanner().plan(intent);
    }
}
