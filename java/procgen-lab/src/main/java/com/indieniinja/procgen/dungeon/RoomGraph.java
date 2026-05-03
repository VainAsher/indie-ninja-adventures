package com.indieniinja.procgen.dungeon;

import com.indieniinja.procgen.model.RoomType;

import java.util.*;

public final class RoomGraph {
    private final List<RoomNode>        nodes     = new ArrayList<>();
    private final Map<String, RoomNode> byId      = new LinkedHashMap<>();
    private RoomNode                    startNode;

    public void add(RoomNode node) {
        nodes.add(node);
        byId.put(node.id, node);
        if (node.intent.type == RoomType.START && startNode == null) {
            startNode = node;
        }
    }

    public RoomNode start() {
        return startNode;
    }

    public RoomNode byId(String id) {
        return byId.get(id);
    }

    public List<RoomNode> nodes() {
        return Collections.unmodifiableList(nodes);
    }

    public RoomNode firstByType(RoomType type) {
        return nodes.stream()
                .filter(n -> n.intent.type == type)
                .findFirst()
                .orElse(null);
    }

    public List<RoomNode> allByType(RoomType type) {
        return nodes.stream()
                .filter(n -> n.intent.type == type)
                .toList();
    }

    /**
     * Returns true when every node in the graph is reachable from the start node.
     */
    public boolean isConnected() {
        if (startNode == null || nodes.isEmpty()) return false;
        Set<RoomNode> visited = new HashSet<>();
        Deque<RoomNode> queue = new ArrayDeque<>();
        queue.add(startNode);
        visited.add(startNode);
        while (!queue.isEmpty()) {
            for (RoomNode nb : queue.poll().neighbors) {
                if (visited.add(nb)) queue.add(nb);
            }
        }
        return visited.size() == nodes.size();
    }
}
