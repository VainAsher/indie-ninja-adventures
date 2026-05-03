package com.indieniinja.procgen.quest;

import com.indieniinja.procgen.model.QuestStatus;
import com.indieniinja.procgen.model.QuestType;

import java.util.List;

public final class Quest {
    public final String               id;
    public final String               title;
    public final QuestType            type;
    public final List<QuestObjective> objectives;
    public final QuestReward          reward;
    public QuestStatus status = QuestStatus.INACTIVE;

    public Quest(String id, String title, QuestType type,
                 List<QuestObjective> objectives, QuestReward reward) {
        this.id         = id;
        this.title      = title;
        this.type       = type;
        this.objectives = List.copyOf(objectives);
        this.reward     = reward;
    }
}
