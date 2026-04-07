package com.indieniinja.client.game;

/**
 * Mission lifecycle state — Java port of Python game/mission_manager.py MissionState enum.
 */
public enum MissionState {
    NOT_STARTED,
    AVAILABLE,
    IN_PROGRESS,
    COMPLETED,
    FAILED;

    public String wire() { return name().toLowerCase(); }
}
