package com.indieniinja.world.puzzle;

/**
 * Types of puzzle interactable that PuzzlePlanner can assign to a room.
 *
 * KEY_DOOR        — key pickup in one room unlocks a DOOR_LOCKED tile in another
 * LEVER_DOOR      — lever entity in an adjacent room opens a DOOR_LOCKED tile
 * BUTTON_SEQUENCE — optional challenge: press N buttons to open a reward door
 * TIMED_PLATFORM  — time-pressure platform sequence (future use)
 */
public enum PuzzleType {
    KEY_DOOR,
    LEVER_DOOR,
    BUTTON_SEQUENCE,
    TIMED_PLATFORM
}
