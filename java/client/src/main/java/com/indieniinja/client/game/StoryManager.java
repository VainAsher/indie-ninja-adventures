package com.indieniinja.client.game;

import com.indieniinja.world.HubState;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/**
 * Client-side story progression state for Shadow Ascent (GDD §5).
 *
 * Drives the 7-act narrative arc. Acts advance based on:
 *   - Hub state transitions received in WorldSnapshot.hubState
 *   - Boss defeats signalled by server dialogue events
 *   - Fragment collection milestones (tracked via inventory)
 *
 * Acts map to rendering parameters via the {@link Act} enum:
 *   hudAlpha, lanternDefault — consumed by HudRenderer and ChunkRenderer.
 *
 * Hub state is cached here so GameScreen can pass it to overlay systems
 * without re-parsing the snapshot every frame.
 */
public final class StoryManager {

    private static final Logger log = LoggerFactory.getLogger(StoryManager.class);

    // ── Acts (GDD §5) ─────────────────────────────────────────────────────────

    private Act     currentAct      = Act.ACT_I_RISE;
    private HubState currentHubState = HubState.FULL;

    // ── Legacy fields (kept for DialogueManager condition evaluation) ─────────

    private int     hubDegradationLevel = 0;   // 0-9 as hub empties in Act II
    private int     lanternsMetCount    = 0;   // 0-5 in Act V
    private boolean veilMaidenEncountered   = false;
    private boolean veilMaidenDefeatedAct1  = false;
    private boolean veilMaidenDefeatedFinal = false;
    private boolean yinYangPresent     = true;

    // Arbitrary flags for condition evaluation (key → value string)
    private final Map<String, String> flags = new HashMap<>();

    // Completed missions this session
    private final Set<String> completedMissions = new HashSet<>();

    // ── Public API ────────────────────────────────────────────────────────────

    public Act      currentAct()          { return currentAct; }
    public HubState currentHubState()     { return currentHubState; }
    public boolean  yinYangPresent()      { return yinYangPresent; }

    /** Called by GameScreen each frame when a new snapshot arrives. */
    public void onHubStateUpdate(String hubStateWire) {
        if (hubStateWire == null || hubStateWire.isEmpty()) return;
        HubState incoming;
        try {
            incoming = HubState.valueOf(hubStateWire);
        } catch (IllegalArgumentException e) {
            return;
        }
        if (incoming == currentHubState) return;

        log.info("[StoryManager] hub state: {} → {}", currentHubState, incoming);
        currentHubState = incoming;
        syncActFromHubState();
    }

    /**
     * Advance to a specific act (called from dialogue events or debug commands).
     */
    public void setAct(Act act) {
        if (act != currentAct) {
            log.info("[StoryManager] act: {} → {}", currentAct, act);
            currentAct = act;
            syncFlags();
        }
    }

    /** Step to the next act (capped at ACT_VII). */
    public void advanceAct() {
        Act[] vals = Act.values();
        int next = Math.min(currentAct.ordinal() + 1, vals.length - 1);
        setAct(vals[next]);
    }

    public void setFlag(String key, String value)  { flags.put(key, value); }
    public String getFlag(String key, String def)  { return flags.getOrDefault(key, def); }

    public void missionCompleted(String missionId) { completedMissions.add(missionId); }
    public boolean isMissionCompleted(String id)   { return completedMissions.contains(id); }

    /**
     * Restore persisted story state values from SaveData.
     * Keeps backward compatibility with older saves that only provided custom flags.
     */
    public void restoreSnapshot(
        int actWire,
        String savedHubState,
        int savedHubDegradationLevel,
        int savedLanternsMetCount,
        boolean savedVeilMaidenEncountered,
        boolean savedVeilMaidenDefeatedAct1,
        boolean savedVeilMaidenDefeatedFinal,
        boolean savedYinYangPresent,
        Map<String, String> savedFlags
    ) {
        currentHubState = parseHubState(savedHubState, currentHubState);
        setAct(Act.fromWire(actWire));
        hubDegradationLevel   = Math.max(0, savedHubDegradationLevel);
        lanternsMetCount      = Math.max(0, savedLanternsMetCount);
        veilMaidenEncountered = savedVeilMaidenEncountered;
        veilMaidenDefeatedAct1  = savedVeilMaidenDefeatedAct1;
        veilMaidenDefeatedFinal = savedVeilMaidenDefeatedFinal;
        yinYangPresent        = savedYinYangPresent;

        flags.clear();
        if (savedFlags != null) flags.putAll(savedFlags);
        syncFlags();
        flags.put("hub_degradation_level",      String.valueOf(hubDegradationLevel));
        flags.put("lanterns_met",               String.valueOf(lanternsMetCount));
        flags.put("veil_maiden_encountered",    String.valueOf(veilMaidenEncountered));
        flags.put("veil_maiden_defeated_act1",  String.valueOf(veilMaidenDefeatedAct1));
        flags.put("veil_maiden_defeated_final", String.valueOf(veilMaidenDefeatedFinal));
        flags.put("yin_yang_present",           String.valueOf(yinYangPresent));
    }

    // ── Signal handlers (called by GameScreen event callbacks) ────────────────

    /** Veil Maiden / Siren encountered — hub starts corrupting. */
    public void onVeilMaidenEncountered() {
        veilMaidenEncountered = true;
        flags.put("veil_maiden_encountered", "true");
    }

    /** Scripted loss to Siren in Act II — hub collapses to EMPTY. */
    public void onVeilMaidenDefeatedAct1() {
        veilMaidenDefeatedAct1 = true;
        yinYangPresent = false;
        hubDegradationLevel = Math.max(hubDegradationLevel, 9);
        currentHubState = HubState.EMPTY;
        if (currentAct.ordinal() < Act.ACT_III_LABYRINTH.ordinal()) {
            setAct(Act.ACT_III_LABYRINTH);
        } else {
            syncFlags();
        }
        flags.put("veil_maiden_defeated_act1", "true");
        flags.put("yin_yang_present", "false");
        flags.put("hub_degradation_level", String.valueOf(hubDegradationLevel));
    }

    /** Increments NPC-met counter used to track Act V progress. */
    public void onNpcMet(String npcId) {
        lanternsMetCount = Math.min(5, lanternsMetCount + 1);
        flags.put("lanterns_met", String.valueOf(lanternsMetCount));
    }

    // ── Condition context for DialogueManager ─────────────────────────────────

    /**
     * Returns a string-keyed map consumed by DialogueManager.checkCondition().
     * Keys mirror Python StoryManager.to_dict().
     */
    public Map<String, String> toConditionContext() {
        Map<String, String> ctx = new HashMap<>(flags);
        ctx.put("act",                         String.valueOf(currentAct.wire()));
        ctx.put("hub_state",                   currentHubState.name());
        ctx.put("hub_degradation_level",       String.valueOf(hubDegradationLevel));
        ctx.put("lanterns_met",                String.valueOf(lanternsMetCount));
        ctx.put("veil_maiden_encountered",     String.valueOf(veilMaidenEncountered));
        ctx.put("veil_maiden_defeated_act1",   String.valueOf(veilMaidenDefeatedAct1));
        ctx.put("veil_maiden_defeated_final",  String.valueOf(veilMaidenDefeatedFinal));
        ctx.put("yin_yang_present",            String.valueOf(yinYangPresent));
        return ctx;
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    /**
     * Derive the correct act from the current hub state.
     * Hub 1: FULL→Act I, CORRUPTED→Act II, EMPTY→Act II end (Act III entry)
     * Hub 2: FRACTURED→Act IV, RECOVERING→Act V, WHOLE→Act VI
     */
    private void syncActFromHubState() {
        Act target = switch (currentHubState) {
            case FULL       -> Act.ACT_I_RISE;
            case CORRUPTED  -> Act.ACT_II_FALL;
            case EMPTY      -> Act.ACT_III_LABYRINTH;
            case FRACTURED  -> Act.ACT_IV_BREAK;
            case RECOVERING -> Act.ACT_V_HEARTH;
            case WHOLE      -> Act.ACT_VI_ASCENT;
        };
        // Never go backward — narrative only advances
        if (target.ordinal() > currentAct.ordinal()) setAct(target);

        // Sync degradation level for legacy conditions
        hubDegradationLevel = switch (currentHubState) {
            case FULL       -> 0;
            case CORRUPTED  -> 5;
            case EMPTY      -> 9;
            default         -> hubDegradationLevel;
        };
        flags.put("hub_degradation_level", String.valueOf(hubDegradationLevel));
    }

    private void syncFlags() {
        flags.put("act",       String.valueOf(currentAct.wire()));
        flags.put("hub_state", currentHubState.name());
    }

    private static HubState parseHubState(String wire, HubState fallback) {
        if (wire == null || wire.isBlank()) return fallback;
        try {
            return HubState.valueOf(wire.trim().toUpperCase(java.util.Locale.ROOT));
        } catch (IllegalArgumentException ex) {
            return fallback;
        }
    }
}
