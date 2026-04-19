package com.indieniinja.world;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

/**
 * Per-hub evolution state machine (GDD §4).
 *
 * Tracks which narrative state the hub is in and exposes the active NPC roster
 * for that state. ZoneSimulationLoop calls this once per second to sync live NPCs.
 *
 * <p>Hub 1 (Bamboo Courtyard) progression:</p>
 * <pre>
 *   FULL  ──► CORRUPTED (first boss defeated)
 *             ──► EMPTY (Siren scripted loss completes)
 * </pre>
 *
 * <p>Hub 2 (Chasm of Still Shadows) progression:</p>
 * <pre>
 *   FRACTURED ──► RECOVERING (2+ fragments collected)
 *                 ──► WHOLE (4+ fragments collected)
 * </pre>
 *
 * Persistence: {@link #toMap()} / {@link #fromMap(Map)} for JSONB storage in
 * {@code player_progress.hub_state}.
 */
public final class HubStateMachine {

    private static final Logger log = LoggerFactory.getLogger(HubStateMachine.class);

    // ── NPC roster definitions ────────────────────────────────────────────────

    /**
     * NPC types present in Hub 1 at each state.
     *
     * Each entry is a pair: (npcType, visible-from-state).
     * An NPC is active when the current state is at or before the hidden threshold.
     */
    private static final List<NpcSlot> HUB1_ROSTER = List.of(
        new NpcSlot("vendor",         Set.of(HubState.FULL, HubState.CORRUPTED)),
        new NpcSlot("mentor",         Set.of(HubState.FULL, HubState.CORRUPTED)),
        new NpcSlot("ally",           Set.of(HubState.FULL)),
        new NpcSlot("training_dummy", Set.of(HubState.FULL, HubState.CORRUPTED)),
        new NpcSlot("siren",          Set.of(HubState.FULL, HubState.CORRUPTED, HubState.EMPTY)),
        new NpcSlot("tutorial",       Set.of(HubState.FULL))
    );

    /** NPC types active in Hub 2. */
    private static final List<NpcSlot> HUB2_ROSTER = List.of(
        new NpcSlot("lore",           Set.of(HubState.FRACTURED, HubState.RECOVERING, HubState.WHOLE)),
        new NpcSlot("mentor",         Set.of(HubState.RECOVERING, HubState.WHOLE)),
        new NpcSlot("vendor",         Set.of(HubState.RECOVERING, HubState.WHOLE)),
        new NpcSlot("ally",           Set.of(HubState.WHOLE)),
        new NpcSlot("training_dummy", Set.of(HubState.WHOLE))
    );

    /** An NPC slot entry — type and the set of hub states where it is active. */
    public record NpcSlot(String npcType, Set<HubState> activeIn) {}

    // ── State ─────────────────────────────────────────────────────────────────

    private final String   hubId;
    private HubState       state;
    private int            bossesDefeated;
    private final Set<String> fragmentsCollected = new LinkedHashSet<>();

    // ── Construction ──────────────────────────────────────────────────────────

    public HubStateMachine(String hubId) {
        this.hubId = hubId;
        // Hub 2 starts FRACTURED; all others start FULL
        this.state = hubId.contains("chasm") || hubId.contains("hub2")
            ? HubState.FRACTURED : HubState.FULL;
        this.bossesDefeated = 0;
    }

    private HubStateMachine(String hubId, HubState state, int bossesDefeated,
                             Collection<String> fragments) {
        this.hubId          = hubId;
        this.state          = state;
        this.bossesDefeated = bossesDefeated;
        this.fragmentsCollected.addAll(fragments);
    }

    // ── Public API ────────────────────────────────────────────────────────────

    public String    hubId()          { return hubId; }
    public HubState  getState()       { return state; }
    public int       bossesDefeated() { return bossesDefeated; }

    /**
     * Called when a boss in this hub is defeated.
     * May trigger a hub state transition.
     */
    public void onBossDefeated(String bossId) {
        bossesDefeated++;
        log.info("[HubFSM] {} boss defeated: {} (total={})", hubId, bossId, bossesDefeated);
        tryAdvance();
    }

    /**
     * Called when a Yin/Yang/Lantern fragment is collected in this hub.
     * May trigger state transition in Hub 2.
     */
    public void onFragmentCollected(String fragId) {
        if (fragmentsCollected.add(fragId)) {
            log.info("[HubFSM] {} fragment collected: {} (total={})",
                hubId, fragId, fragmentsCollected.size());
            tryAdvance();
        }
    }

    /**
     * Called when the Siren's scripted loss sequence completes.
     * Transitions Hub 1 to EMPTY immediately.
     */
    public void onSirenDefeated() {
        if (state == HubState.CORRUPTED || state == HubState.FULL) {
            log.info("[HubFSM] {} Siren defeated — transitioning to EMPTY", hubId);
            state = HubState.EMPTY;
        }
    }

    /**
     * Returns the NPC types that should be live in the current hub state.
     * ZoneSimulationLoop compares this list against the live NPC roster to
     * spawn/despawn accordingly.
     */
    public List<String> activeNpcTypes() {
        List<NpcSlot> roster = rosterForHub();
        List<String> active = new ArrayList<>();
        for (NpcSlot slot : roster) {
            if (slot.activeIn().contains(state)) active.add(slot.npcType());
        }
        return Collections.unmodifiableList(active);
    }

    // ── Serialisation ─────────────────────────────────────────────────────────

    public Map<String, Object> toMap() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("hub_id",            hubId);
        m.put("state",             state.name());
        m.put("bosses_defeated",   bossesDefeated);
        m.put("fragments_collected", new ArrayList<>(fragmentsCollected));
        return m;
    }

    @SuppressWarnings("unchecked")
    public static HubStateMachine fromMap(Map<String, Object> m) {
        String hubId = (String) m.getOrDefault("hub_id", "central_hub");
        HubState state;
        try {
            state = HubState.valueOf((String) m.getOrDefault("state", "FULL"));
        } catch (IllegalArgumentException e) {
            state = HubState.FULL;
        }
        int bosses = ((Number) m.getOrDefault("bosses_defeated", 0)).intValue();
        List<String> frags = (List<String>) m.getOrDefault("fragments_collected", List.of());
        return new HubStateMachine(hubId, state, bosses, frags);
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private List<NpcSlot> rosterForHub() {
        if (hubId.contains("chasm") || hubId.contains("hub2")) return HUB2_ROSTER;
        return HUB1_ROSTER;
    }

    private void tryAdvance() {
        HubState next = switch (state) {
            case FULL       -> bossesDefeated >= 1 ? HubState.CORRUPTED   : null;
            case CORRUPTED  -> null;  // only Siren defeat → EMPTY (see onSirenDefeated)
            case FRACTURED  -> fragmentsCollected.size() >= 2 ? HubState.RECOVERING : null;
            case RECOVERING -> fragmentsCollected.size() >= 4 ? HubState.WHOLE       : null;
            default         -> null;
        };
        if (next != null) {
            log.info("[HubFSM] {} state: {} → {}", hubId, state, next);
            state = next;
        }
    }
}
