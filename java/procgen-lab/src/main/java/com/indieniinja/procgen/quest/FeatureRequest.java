package com.indieniinja.procgen.quest;

/** A request from the quest layer to place a specific tile in a specific room during generation. */
public final class FeatureRequest {
    public final String roomId;
    public final byte   tileType;
    public final String reason;

    public FeatureRequest(String roomId, byte tileType, String reason) {
        this.roomId   = roomId;
        this.tileType = tileType;
        this.reason   = reason;
    }
}
