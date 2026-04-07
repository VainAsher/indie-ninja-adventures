package com.indieniinja.client.game;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/**
 * Client-side story progression state.
 *
 * Java port of Python game/story_manager.py StoryManager.
 * Tracks the current act (0-4) and key story flags used by dialogue
 * condition evaluation and NPC dialogue ID selection.
 *
 * Acts:
 *   0 — Rising Grounds (forest/town, hub empties as Veil Maiden emerges)
 *   1 — Veil Descends (caves, scripted defeat)
 *   2 — Hollow Depths (recovery zone, The Lanterns join)
 *   3 — Ascending Paths (castle, hub restored)
 *   4 — Winding Skyroad (sewer + final boss, moral choice)
 */
public final class StoryManager {

    // ── Acts ──────────────────────────────────────────────────────────────────

    public enum Act { ACT_0, ACT_1, ACT_2, ACT_3, ACT_4;
        public int num() { return ordinal(); }
        public String wire() { return String.valueOf(ordinal()); }
    }

    private Act    currentAct = Act.ACT_0;
    private int    hubDegradationLevel = 0;   // Act 0: 0-9 (hub empties over time)
    private int    lanternsMetCount    = 0;    // Act 2: 0-5
    private boolean veilMaidenEncountered   = false;
    private boolean veilMaidenDefeatedAct1  = false;
    private boolean veilMaidenDefeatedFinal = false;
    private boolean yinYangPresent     = true;

    // Arbitrary flags for condition evaluation (key → value string)
    private final Map<String, String> flags = new HashMap<>();

    // Completed missions this session
    private final Set<String> completedMissions = new HashSet<>();

    // ── Public API ────────────────────────────────────────────────────────────

    public Act    currentAct()           { return currentAct; }
    public int    actNum()               { return currentAct.num(); }
    public boolean yinYangPresent()      { return yinYangPresent; }

    public void setAct(Act act)          { this.currentAct = act; syncFlags(); }
    public void advanceAct()             { if (currentAct.ordinal() < 4) { currentAct = Act.values()[currentAct.ordinal()+1]; syncFlags(); } }

    public void setFlag(String key, String value) { flags.put(key, value); }
    public String getFlag(String key, String def)  { return flags.getOrDefault(key, def); }

    public void missionCompleted(String missionId) { completedMissions.add(missionId); }
    public boolean isMissionCompleted(String id)   { return completedMissions.contains(id); }

    /**
     * Returns the story_state map used by DialogueManager.checkCondition().
     * Mirrors Python's StoryManager.to_dict() keys used in condition strings.
     */
    public Map<String, String> toConditionContext() {
        Map<String, String> ctx = new HashMap<>(flags);
        ctx.put("act",                         currentAct.wire());
        ctx.put("hub_degradation_level",       String.valueOf(hubDegradationLevel));
        ctx.put("lanterns_met",                String.valueOf(lanternsMetCount));
        ctx.put("veil_maiden_encountered",     String.valueOf(veilMaidenEncountered));
        ctx.put("veil_maiden_defeated_act1",   String.valueOf(veilMaidenDefeatedAct1));
        ctx.put("veil_maiden_defeated_final",  String.valueOf(veilMaidenDefeatedFinal));
        ctx.put("yin_yang_present",            String.valueOf(yinYangPresent));
        return ctx;
    }

    private void syncFlags() {
        flags.put("act", currentAct.wire());
    }
}
