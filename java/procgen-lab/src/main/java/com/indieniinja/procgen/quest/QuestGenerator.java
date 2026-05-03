package com.indieniinja.procgen.quest;

import com.indieniinja.procgen.dungeon.DungeonPlan;
import com.indieniinja.procgen.dungeon.RoomNode;
import com.indieniinja.procgen.model.Ability;
import com.indieniinja.procgen.model.QuestObjectiveType;
import com.indieniinja.procgen.model.QuestType;
import com.indieniinja.procgen.model.RewardType;
import com.indieniinja.procgen.model.RoomType;
import com.indieniinja.procgen.model.Tile;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class QuestGenerator {

    public QuestPlan generate(DungeonPlan dungeon) {
        List<Quest> quests   = new ArrayList<>();
        Map<String, List<FeatureRequest>> features = new LinkedHashMap<>();

        RoomNode boss     = dungeon.roomGraph.firstByType(RoomType.BOSS);
        RoomNode exit     = dungeon.roomGraph.firstByType(RoomType.EXIT);
        RoomNode treasure = dungeon.roomGraph.firstByType(RoomType.TREASURE);
        RoomNode save     = dungeon.roomGraph.firstByType(RoomType.SAVE);

        // Main quest: defeat boss (if present) then reach exit
        if (exit != null) {
            List<QuestObjective> objectives = new ArrayList<>();
            if (boss != null) {
                objectives.add(new QuestObjective(
                        QuestObjectiveType.DEFEAT_BOSS, boss.id, "Defeat the Guardian"));
            }
            objectives.add(new QuestObjective(
                    QuestObjectiveType.REACH_ROOM, exit.id, "Reach the Exit"));
            Ability reward = dungeon.intent.abilityFocus != null
                    ? dungeon.intent.abilityFocus : Ability.DASH;
            quests.add(new Quest("main_quest", "Trial of the Depths", QuestType.MAIN,
                    objectives, new QuestReward(RewardType.ABILITY_UNLOCK, reward, "Ability unlock")));
        }

        // Side quest: collect hidden treasure
        if (treasure != null) {
            quests.add(new Quest("side_treasure", "Hidden Riches", QuestType.SIDE,
                    List.of(new QuestObjective(
                            QuestObjectiveType.COLLECT_PICKUP, treasure.id,
                            "Collect the hidden treasure")),
                    new QuestReward(RewardType.ITEM, null, "Rare item")));
            features.computeIfAbsent(treasure.id, k -> new ArrayList<>())
                    .add(new FeatureRequest(treasure.id, Tile.PICKUP, "quest: treasure pickup"));
        }

        // Optional quest: find the save point
        if (save != null) {
            quests.add(new Quest("opt_sanctuary", "The Sanctuary", QuestType.OPTIONAL,
                    List.of(new QuestObjective(
                            QuestObjectiveType.FIND_SAVE, save.id, "Find the respawn shrine")),
                    new QuestReward(RewardType.LORE_FRAGMENT, null, "Lore: the Veil")));
        }

        return new QuestPlan(dungeon.intent, quests, features);
    }
}
