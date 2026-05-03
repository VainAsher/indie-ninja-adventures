package com.indieniinja.procgen.quest;

import com.indieniinja.procgen.model.QuestObjectiveType;

public final class QuestObjective {
    public final QuestObjectiveType type;
    public final String             targetRoomId;
    public final String             description;
    public boolean completed = false;

    public QuestObjective(QuestObjectiveType type, String targetRoomId, String description) {
        this.type         = type;
        this.targetRoomId = targetRoomId;
        this.description  = description;
    }
}
