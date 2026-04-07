package com.indieniinja.client.game;

import com.badlogic.gdx.files.FileHandle;
import com.badlogic.gdx.utils.JsonReader;
import com.badlogic.gdx.utils.JsonValue;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * A complete branching dialogue tree.
 *
 * Java port of Python game/dialogue_system.py DialogueTree dataclass.
 * Loaded from data/dialogues.json; immutable at runtime.
 */
public final class DialogueTree {

    public final String                    dialogueId;
    public final String                    rootNodeId;
    public final Map<String, DialogueNode> nodes;

    public DialogueTree(String dialogueId, String rootNodeId,
                        Map<String, DialogueNode> nodes) {
        this.dialogueId = dialogueId;
        this.rootNodeId = rootNodeId;
        this.nodes      = nodes;
    }

    public DialogueNode rootNode()              { return nodes.get(rootNodeId); }
    public DialogueNode node(String nodeId)     { return nodes.get(nodeId); }

    // ── JSON loading ─────────────────────────────────────────────────────────

    /**
     * Load all dialogue trees from data/dialogues.json.
     * Returns a map of dialogueId → DialogueTree.
     */
    public static Map<String, DialogueTree> loadAll(FileHandle file) {
        Map<String, DialogueTree> out = new HashMap<>();
        if (!file.exists()) return out;

        JsonValue root = new JsonReader().parse(file);
        for (JsonValue treeVal : root) {
            DialogueTree tree = parseTree(treeVal);
            out.put(tree.dialogueId, tree);
        }
        return out;
    }

    private static DialogueTree parseTree(JsonValue v) {
        String id       = str(v, "dialogue_id", v.name());
        String rootId   = str(v, "root_node_id", "");
        Map<String, DialogueNode> nodes = new HashMap<>();

        JsonValue nodesObj = v.get("nodes");
        if (nodesObj != null) {
            for (JsonValue nv : nodesObj) {
                DialogueNode node = parseNode(nv);
                nodes.put(node.nodeId, node);
            }
        }
        return new DialogueTree(id, rootId, nodes);
    }

    private static DialogueNode parseNode(JsonValue v) {
        String nodeId      = str(v, "node_id",      v.name());
        String speaker     = str(v, "speaker",      "");
        String text        = str(v, "text",         "");
        String nextNodeId  = str(v, "next_node_id", null);
        String onExitEvent = str(v, "on_exit_event",null);

        List<DialogueChoice> choices = new ArrayList<>();
        JsonValue choicesArr = v.get("choices");
        if (choicesArr != null) {
            for (JsonValue cv : choicesArr) {
                String choiceText    = str(cv, "choice_text",    "");
                String choiceNext    = str(cv, "next_node_id",   null);
                String requires      = str(cv, "requires",       null);
                String onSelectEvent = str(cv, "on_select_event",null);
                choices.add(new DialogueChoice(choiceText, choiceNext, requires, onSelectEvent));
            }
        }
        return new DialogueNode(nodeId, speaker, text, choices, nextNodeId, onExitEvent);
    }

    private static String str(JsonValue v, String key, String def) {
        JsonValue c = v.get(key);
        return (c != null && !c.isNull()) ? c.asString() : def;
    }
}
