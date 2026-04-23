package com.indieniinja.client.game;

import com.badlogic.gdx.Gdx;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Dialogue conversation state machine.
 *
 * Java port of Python game/dialogue_system.py DialogueManager.
 *
 * Usage:
 *   dialogueManager.startDialogue("tutorial_elder");
 *   DialogueNode node = dialogueManager.currentNode();
 *   List<DialogueChoice> choices = dialogueManager.availableChoices();
 *   dialogueManager.selectChoice(0);          // navigates to choices.get(0).nextNodeId
 *   dialogueManager.advance();                // auto-advance (no choices)
 *   dialogueManager.isActive();               // false when dialogue ended
 */
public final class DialogueManager {

    private final Map<String, DialogueTree> trees;
    private Map<String, String>             storyContext = java.util.Collections.emptyMap();

    // Runtime state
    private DialogueTree    currentTree = null;
    private DialogueNode    currentNode = null;
    private final List<String> history  = new ArrayList<>();

    // Callback for game events emitted from dialogue choices / node exits
    // Format: "event_key" or "event_key:arg" — interpreted by GameScreen
    private java.util.function.Consumer<String> eventCallback;

    public DialogueManager() {
        if (Gdx.app == null || Gdx.files == null) {
            this.trees = java.util.Map.of();
            return;
        }
        // Prefer .yarn directory if present; fall back to monolithic dialogues.json.
        com.badlogic.gdx.files.FileHandle yarnDir = Gdx.files.internal("data/dialogues");
        if (yarnDir.exists() && yarnDir.isDirectory()) {
            Map<String, DialogueTree> fromYarn = DialogueTree.loadAllFromYarn(yarnDir);
            if (!fromYarn.isEmpty()) {
                this.trees = fromYarn;
                return;
            }
        }
        this.trees = DialogueTree.loadAll(Gdx.files.internal("data/dialogues.json"));
    }

    // ── Story context ─────────────────────────────────────────────────────────

    /**
     * Provide the story state context used by condition evaluation.
     * Should be updated whenever the StoryManager state changes.
     */
    public void setStoryContext(Map<String, String> context) {
        this.storyContext = context != null ? context : java.util.Collections.emptyMap();
    }

    public void setEventCallback(java.util.function.Consumer<String> cb) {
        this.eventCallback = cb;
    }

    // ── Conversation control ──────────────────────────────────────────────────

    /**
     * Begin a dialogue by ID (Python: DialogueManager.start_dialogue).
     * Returns false if the dialogue ID is not found.
     */
    public boolean startDialogue(String dialogueId) {
        DialogueTree tree = trees.get(dialogueId);
        if (tree == null) return false;
        currentTree = tree;
        currentNode = tree.rootNode();
        history.clear();
        if (currentNode != null) history.add(currentNode.nodeId);
        return currentNode != null;
    }

    /**
     * Act-aware dialogue start — tries "npcId_actN" variants first,
     * falling back to "npcId" (Python: DialogueManager.get_npc_dialogue_id).
     */
    public boolean startNpcDialogue(String npcId) {
        // Try act-specific variant first (e.g. "elder_act2")
        String actStr = storyContext.getOrDefault("act", "0");
        String actKey = npcId + "_act" + actStr;
        if (trees.containsKey(actKey)) return startDialogue(actKey);
        // Fall back to base dialogue id
        return startDialogue(npcId);
    }

    public boolean isActive()                { return currentNode != null; }
    public DialogueNode currentNode()        { return currentNode; }
    public DialogueTree currentTree()        { return currentTree; }

    /**
     * Choices available given the current story context
     * (Python: DialogueManager.get_available_choices).
     */
    public List<DialogueChoice> availableChoices() {
        if (currentNode == null) return List.of();
        List<DialogueChoice> out = new ArrayList<>();
        for (DialogueChoice c : currentNode.choices) {
            if (checkCondition(c.requires)) out.add(c);
        }
        return out;
    }

    /**
     * Select a choice by index in availableChoices() list.
     * Emits the choice's onSelectEvent if present, then navigates.
     */
    public void selectChoice(int index) {
        List<DialogueChoice> choices = availableChoices();
        if (index < 0 || index >= choices.size()) return;
        DialogueChoice choice = choices.get(index);
        if (choice.onSelectEvent != null && eventCallback != null)
            eventCallback.accept(choice.onSelectEvent);
        navigateTo(choice.nextNodeId);
    }

    /**
     * Advance through a node that has no choices (auto-advance or click-through).
     * Python: DialogueManager.advance().
     */
    public void advance() {
        if (currentNode == null) return;
        if (!currentNode.choices.isEmpty()) return;  // choices present — use selectChoice
        // Emit node exit event
        if (currentNode.onExitEvent != null && eventCallback != null)
            eventCallback.accept(currentNode.onExitEvent);
        navigateTo(currentNode.nextNodeId);
    }

    /** End dialogue immediately (e.g. player pressed ESC). */
    public void endDialogue() {
        currentTree = null;
        currentNode = null;
        history.clear();
    }

    // ── Condition evaluation ──────────────────────────────────────────────────

    /**
     * Evaluate a condition string against storyContext.
     *
     * Format: "key:value" (== check) or "key:op:value" (comparison).
     * Null / empty condition → always true.
     *
     * Python parity: DialogueManager.check_condition()
     */
    public boolean checkCondition(String condition) {
        if (condition == null || condition.isBlank()) return true;
        String[] parts = condition.split(":", 3);
        String key = parts[0].trim();
        String ctxVal = storyContext.getOrDefault(key, "");

        if (parts.length == 2) {
            // "key:value" — equality check
            return ctxVal.equals(parts[1].trim());
        }
        if (parts.length == 3) {
            String op  = parts[1].trim();
            String rhs = parts[2].trim();
            try {
                float lhsF = Float.parseFloat(ctxVal);
                float rhsF = Float.parseFloat(rhs);
                return switch (op) {
                    case "==" -> lhsF == rhsF;
                    case "!=" -> lhsF != rhsF;
                    case ">"  -> lhsF >  rhsF;
                    case ">=" -> lhsF >= rhsF;
                    case "<"  -> lhsF <  rhsF;
                    case "<=" -> lhsF <= rhsF;
                    default   -> ctxVal.equals(rhs);
                };
            } catch (NumberFormatException e) {
                // String comparison fallback
                return switch (op) {
                    case "==" -> ctxVal.equals(rhs);
                    case "!=" -> !ctxVal.equals(rhs);
                    default   -> false;
                };
            }
        }
        return true;
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private void navigateTo(String nodeId) {
        if (nodeId == null) {
            endDialogue();
            return;
        }
        DialogueNode next = currentTree.node(nodeId);
        if (next == null) {
            endDialogue();
            return;
        }
        currentNode = next;
        history.add(nodeId);
    }
}
