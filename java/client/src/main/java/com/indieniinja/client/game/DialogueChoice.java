package com.indieniinja.client.game;

/**
 * A single player choice within a dialogue node.
 *
 * Java port of Python game/dialogue_system.py DialogueChoice dataclass.
 */
public final class DialogueChoice {

    /** Text shown to the player in the choice list. */
    public final String choiceText;
    /** Next node to navigate to, or null to end the dialogue. */
    public final String nextNodeId;
    /**
     * Optional condition string in "key:value" or "key:op:value" format.
     * Null means always available.
     */
    public final String requires;
    /**
     * Optional event key to emit when this choice is selected.
     * Interpreted by the game layer (e.g. "open_shop", "start_mission:forest_1").
     */
    public final String onSelectEvent;

    public DialogueChoice(String choiceText, String nextNodeId,
                          String requires, String onSelectEvent) {
        this.choiceText    = choiceText;
        this.nextNodeId    = nextNodeId;
        this.requires      = requires;
        this.onSelectEvent = onSelectEvent;
    }
}
