package com.indieniinja.procgen.quest;

import com.indieniinja.procgen.intent.DungeonIntent;
import com.indieniinja.procgen.model.QuestType;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public final class QuestPlan {
    public final DungeonIntent intent;
    public final List<Quest>   quests;
    private final Map<String, List<FeatureRequest>> featuresByRoom;

    public QuestPlan(DungeonIntent intent, List<Quest> quests,
                     Map<String, List<FeatureRequest>> featuresByRoom) {
        this.intent         = intent;
        this.quests         = List.copyOf(quests);
        this.featuresByRoom = featuresByRoom;
    }

    /** Returns all FeatureRequests that should be applied when generating the given room. */
    public List<FeatureRequest> forRoom(String roomId) {
        return featuresByRoom.getOrDefault(roomId, List.of());
    }

    public Quest mainQuest() {
        return quests.stream()
                .filter(q -> q.type == QuestType.MAIN)
                .findFirst()
                .orElse(null);
    }
}
