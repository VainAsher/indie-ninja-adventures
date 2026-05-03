package com.indieniinja.procgen.dungeon;

import com.indieniinja.procgen.intent.RoomIntent;

import java.util.ArrayList;
import java.util.List;

public final class RoomNode {
    public final String          id;
    public final RoomIntent      intent;
    public final int             graphX;
    public final int             graphY;
    public final List<RoomNode>  neighbors = new ArrayList<>();

    public RoomNode(String id, RoomIntent intent, int graphX, int graphY) {
        this.id     = id;
        this.intent = intent;
        this.graphX = graphX;
        this.graphY = graphY;
    }

    public void connect(RoomNode other) {
        if (!neighbors.contains(other)) neighbors.add(other);
        if (!other.neighbors.contains(this)) other.neighbors.add(this);
    }

    @Override
    public String toString() {
        return id + "[" + intent.type + "]";
    }
}
