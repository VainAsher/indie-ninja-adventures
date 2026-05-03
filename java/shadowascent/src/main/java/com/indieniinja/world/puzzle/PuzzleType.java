package com.indieniinja.world.puzzle;

/**
 * Types of puzzle interactable that PuzzlePlanner can assign to a room.
 *
 * KEY_DOOR               — key pickup in one room unlocks a DOOR_LOCKED tile in another
 * LEVER_DOOR             — lever entity in an adjacent room opens a DOOR_LOCKED tile
 * BUTTON_SEQUENCE        — optional challenge: press N buttons to open a reward door
 * ECHO_TRIGGER           — interact trigger spawns an echo and unlocks a linked echo door
 * ASYMMETRIC_ABILITY_LOCK — echo auto-loops at a position; door unlocks when player jumps
 *                           within proximity of the echo (player needs echo as a step)
 * SIMULTANEOUS_TIMING    — echo replays past actions; door unlocks when player matches
 *                           the echo's jump input 3 times within ±4 ticks tolerance
 * TIMED_PLATFORM         — time-pressure platform sequence (future use)
 */
public enum PuzzleType {
    KEY_DOOR,
    LEVER_DOOR,
    BUTTON_SEQUENCE,
    ECHO_TRIGGER,
    ASYMMETRIC_ABILITY_LOCK,
    SIMULTANEOUS_TIMING,
    TIMED_PLATFORM
}
