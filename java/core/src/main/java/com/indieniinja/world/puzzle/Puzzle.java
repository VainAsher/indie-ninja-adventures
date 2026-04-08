package com.indieniinja.world.puzzle;

/**
 * Descriptor for a single puzzle element within a room.
 *
 * PuzzlePlanner produces these; PuzzleLayer stamps them as tiles/entity markers.
 * A puzzle may be standalone or paired with another via linkedPuzzleId
 * (e.g., a key in room A linked to a locked door in room B).
 */
public final class Puzzle {

    public final String     puzzleId;
    public final PuzzleType type;

    /**
     * Id of the paired puzzle element, or null if standalone.
     * Example: lever.linkedPuzzleId == door.puzzleId.
     */
    public final String  linkedPuzzleId;

    /**
     * True if this puzzle must be solved to progress through the room.
     * False = optional challenge / reward chamber.
     */
    public final boolean isBlocker;

    public Puzzle(String puzzleId, PuzzleType type, String linkedPuzzleId, boolean isBlocker) {
        this.puzzleId       = puzzleId;
        this.type           = type;
        this.linkedPuzzleId = linkedPuzzleId;
        this.isBlocker      = isBlocker;
    }

    @Override
    public String toString() {
        return "Puzzle(" + puzzleId + " " + type
            + (linkedPuzzleId != null ? " → " + linkedPuzzleId : "")
            + (isBlocker ? " BLOCKER" : "") + ")";
    }
}
