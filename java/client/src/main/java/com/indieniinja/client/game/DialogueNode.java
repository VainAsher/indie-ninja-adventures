package com.indieniinja.client.game;

import java.util.List;

/**
 * A single node in a dialogue tree.
 *
 * Java port of Python game/dialogue_system.py DialogueNode dataclass.
 *
 * If {@code choices} is empty the node auto-advances to {@code nextNodeId}.
 * If both {@code choices} is empty and {@code nextNodeId} is null, the
 * dialogue ends after this node.
 */
public final class DialogueNode {

    public final String              nodeId;
    public final String              speaker;
    public final String              text;
    public final List<DialogueChoice> choices;
    /** Auto-advance target when there are no choices. */
    public final String              nextNodeId;
    /** Optional event key emitted when leaving this node. */
    public final String              onExitEvent;

    public DialogueNode(String nodeId, String speaker, String text,
                        List<DialogueChoice> choices,
                        String nextNodeId, String onExitEvent) {
        this.nodeId     = nodeId;
        this.speaker    = speaker;
        this.text       = text;
        this.choices    = choices;
        this.nextNodeId = nextNodeId;
        this.onExitEvent = onExitEvent;
    }
}
