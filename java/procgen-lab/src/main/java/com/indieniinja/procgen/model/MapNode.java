package com.indieniinja.procgen.model;

public final class MapNode {
    public final String      id;
    public final String      name;
    public final MapNodeType type;
    public final int         mapX;
    public final int         mapY;

    public boolean discovered;
    public boolean locked;
    public Ability requiredAbility;

    public MapNode(String id, String name, MapNodeType type, int mapX, int mapY) {
        this.id   = id;
        this.name = name;
        this.type = type;
        this.mapX = mapX;
        this.mapY = mapY;
    }
}
