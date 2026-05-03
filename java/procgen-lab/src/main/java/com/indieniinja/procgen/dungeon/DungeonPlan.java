package com.indieniinja.procgen.dungeon;

import com.indieniinja.procgen.intent.DungeonIntent;
import com.indieniinja.procgen.quest.QuestPlan;

public final class DungeonPlan {
    public final DungeonIntent intent;
    public final RoomGraph     roomGraph;

    public QuestPlan questPlan; // assigned by QuestGenerator after construction

    public DungeonPlan(DungeonIntent intent, RoomGraph roomGraph) {
        this.intent    = intent;
        this.roomGraph = roomGraph;
    }
}
