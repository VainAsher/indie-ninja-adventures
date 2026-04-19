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

    // ── Yarn loading ──────────────────────────────────────────────────────────

    /**
     * Load all .yarn files from a directory into a dialogue tree map.
     * Each .yarn file may contain multiple nodes separated by "===" markers.
     * Files that cannot be parsed are skipped with a logged warning.
     *
     * The file's stem (filename without .yarn) is used as the tree's dialogueId.
     * The node tagged "root" or listed first becomes the rootNodeId.
     *
     * @param dir libGDX FileHandle pointing to the directory containing .yarn files
     * @return map of dialogueId → DialogueTree (empty if directory absent)
     */
    public static Map<String, DialogueTree> loadAllFromYarn(FileHandle dir) {
        Map<String, DialogueTree> out = new HashMap<>();
        if (!dir.exists() || !dir.isDirectory()) return out;
        for (FileHandle fh : dir.list(".yarn")) {
            try {
                String treeName = fh.nameWithoutExtension();
                DialogueTree tree = parseYarnFile(treeName, fh.readString("UTF-8"));
                if (tree != null) out.put(treeName, tree);
            } catch (Exception e) {
                com.badlogic.gdx.Gdx.app.error("DialogueTree", "Failed to load " + fh.path() + ": " + e.getMessage());
            }
        }
        return out;
    }

    private static DialogueTree parseYarnFile(String treeId, String content) {
        Map<String, DialogueNode> nodes = new HashMap<>();
        String rootNodeId = "";
        String firstNodeId = "";

        // Split into raw node blocks by "==="
        String[] blocks = content.split("===");
        for (String block : blocks) {
            block = block.trim();
            if (block.isEmpty() || block.startsWith("//")) continue;
            int dashIdx = block.indexOf("---");
            if (dashIdx < 0) continue;

            String header = block.substring(0, dashIdx).trim();
            String body   = block.substring(dashIdx + 3).trim();

            // Parse header fields
            String nodeId  = "";
            boolean isRoot = false;
            for (String hLine : header.split("\n")) {
                hLine = hLine.trim();
                if (hLine.startsWith("title:"))
                    nodeId = hLine.substring("title:".length()).trim();
                else if (hLine.startsWith("tags:") && hLine.contains("root"))
                    isRoot = true;
            }
            if (nodeId.isEmpty()) continue;
            if (firstNodeId.isEmpty()) firstNodeId = nodeId;
            if (isRoot) rootNodeId = nodeId;

            DialogueNode node = parseYarnBody(nodeId, body);
            nodes.put(nodeId, node);
        }

        if (rootNodeId.isEmpty()) rootNodeId = firstNodeId;
        if (nodes.isEmpty()) return null;
        return new DialogueTree(treeId, rootNodeId, nodes);
    }

    private static DialogueNode parseYarnBody(String nodeId, String body) {
        String  speaker    = "";
        String  text       = "";
        String  nextNodeId = null;
        String  exitEvent  = null;
        List<DialogueChoice> choices = new ArrayList<>();

        List<String> lines = new ArrayList<>();
        for (String l : body.split("\n")) lines.add(l.stripTrailing());

        for (int i = 0; i < lines.size(); i++) {
            String line = lines.get(i);
            String trimmed = line.trim();
            if (trimmed.isEmpty()) continue;

            if (trimmed.startsWith("->")) {
                // Choice line: -> choice text [<<if $cond>>]
                String choicePart = trimmed.substring(2).trim();
                String requires = null;
                if (choicePart.contains("<<if $")) {
                    int start = choicePart.indexOf("<<if $");
                    requires   = choicePart.substring(start + 6, choicePart.indexOf(">>", start)).trim();
                    choicePart = choicePart.substring(0, start).trim();
                }
                // Read indented branch lines
                String choiceNext     = null;
                String selectEvent    = null;
                while (i + 1 < lines.size() && (lines.get(i + 1).startsWith("    ") || lines.get(i + 1).startsWith("\t"))) {
                    i++;
                    String branch = lines.get(i).trim();
                    if (branch.startsWith("<<jump "))
                        choiceNext  = branch.substring(7, branch.length() - 2).trim();
                    else if (branch.startsWith("<<stop>>"))
                        choiceNext = null;
                    else if (branch.startsWith("<<fire_event "))
                        selectEvent = branch.substring(13, branch.length() - 2).trim();
                }
                choices.add(new DialogueChoice(choicePart, choiceNext, requires, selectEvent));
            } else if (trimmed.startsWith("<<jump ")) {
                nextNodeId = trimmed.substring(7, trimmed.length() - 2).trim();
            } else if (trimmed.startsWith("<<stop>>")) {
                nextNodeId = null;
            } else if (trimmed.startsWith("<<fire_event ")) {
                exitEvent = trimmed.substring(13, trimmed.length() - 2).trim();
            } else if (trimmed.contains(": ") && speaker.isEmpty() && text.isEmpty()) {
                // "Speaker: text" — first non-command line
                int sep = trimmed.indexOf(": ");
                speaker = trimmed.substring(0, sep);
                text    = trimmed.substring(sep + 2);
            } else if (speaker.isEmpty() && text.isEmpty()) {
                text = trimmed;
            }
        }
        return new DialogueNode(nodeId, speaker, text, choices, nextNodeId, exitEvent);
    }
}
