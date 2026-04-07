package com.indieniinja.client.game;

import com.badlogic.gdx.Gdx;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Manages mission lifecycle (start, objective progress, complete, fail).
 *
 * Java port of Python game/mission_manager.py MissionManager.
 *
 * Loads all MissionDefinitions from data/missions.json at startup.
 * Tracks per-mission progress in memory (save/load wired to SaveSystem later).
 */
public final class MissionManager {

    private final Map<String, MissionDefinition> definitions;
    private final Map<String, MissionState>      states      = new HashMap<>();
    private final Map<String, Integer>           attempts    = new HashMap<>();
    private final Map<String, Float>             bestTimes   = new HashMap<>();

    // Active mission state
    private String activeMissionId = null;
    private float  missionTimer    = 0f;         // seconds elapsed in active mission
    private final Map<String, Integer> objectiveProgress = new HashMap<>();  // key → count
    private boolean exitLocked = false;

    // Callbacks (set by GameScreen)
    private Runnable onMissionComplete;
    private Runnable onMissionFail;
    private java.util.function.Consumer<String> onObjectiveComplete;

    public MissionManager() {
        this.definitions = MissionDefinition.loadAll(
            Gdx.files.internal("data/missions.json"));
        // Mark all missions as NOT_STARTED initially; availability resolved on request
        for (String id : definitions.keySet()) states.put(id, MissionState.NOT_STARTED);
    }

    // ── Query ─────────────────────────────────────────────────────────────────

    public MissionDefinition getDefinition(String id)    { return definitions.get(id); }
    public MissionState      getState(String id)         { return states.getOrDefault(id, MissionState.NOT_STARTED); }
    public boolean           isActive()                  { return activeMissionId != null; }
    public String            getActiveMissionId()        { return activeMissionId; }
    public boolean           isExitLocked()              { return exitLocked; }
    public float             getMissionTimer()           { return missionTimer; }

    /** All available mission definitions ordered by difficulty (for mission menu UI). */
    public List<MissionDefinition> availableMissions(int currentAct) {
        List<MissionDefinition> out = new ArrayList<>();
        for (MissionDefinition d : definitions.values()) {
            MissionState s = states.getOrDefault(d.missionId, MissionState.NOT_STARTED);
            if (s != MissionState.COMPLETED && d.act <= currentAct) out.add(d);
        }
        out.sort((a, b) -> Integer.compare(a.difficulty, b.difficulty));
        return out;
    }

    // ── Lifecycle ─────────────────────────────────────────────────────────────

    /**
     * Start a mission (Python: MissionManager.start_mission).
     * Locks the exit, resets objective progress, starts the timer.
     */
    public void startMission(String missionId) {
        MissionDefinition def = definitions.get(missionId);
        if (def == null) return;
        activeMissionId   = missionId;
        missionTimer      = 0f;
        exitLocked        = true;
        objectiveProgress.clear();
        states.put(missionId, MissionState.IN_PROGRESS);
        attempts.merge(missionId, 1, Integer::sum);
    }

    /**
     * Advance objective progress (Python: MissionManager.complete_objective).
     * When all objectives are done the exit unlocks automatically.
     */
    public void progressObjective(String objectiveKey, int delta) {
        if (activeMissionId == null) return;
        MissionDefinition def = definitions.get(activeMissionId);
        if (def == null) return;

        objectiveProgress.merge(objectiveKey, delta, Integer::sum);
        if (onObjectiveComplete != null) onObjectiveComplete.accept(objectiveKey);

        if (checkAllObjectivesMet(def)) {
            exitLocked = false;
        }
    }

    /**
     * Complete the active mission (Python: MissionManager.complete_mission).
     * Records best time, distributes rewards, emits callback.
     */
    public void completeMission() {
        if (activeMissionId == null) return;
        String id = activeMissionId;
        states.put(id, MissionState.COMPLETED);
        float prev = bestTimes.getOrDefault(id, Float.MAX_VALUE);
        bestTimes.put(id, Math.min(prev, missionTimer));
        activeMissionId = null;
        exitLocked      = false;
        objectiveProgress.clear();
        if (onMissionComplete != null) onMissionComplete.run();
    }

    /**
     * Fail / abandon the active mission (Python: MissionManager.fail_mission).
     */
    public void failMission() {
        if (activeMissionId == null) return;
        states.put(activeMissionId, MissionState.FAILED);
        activeMissionId = null;
        exitLocked      = false;
        objectiveProgress.clear();
        if (onMissionFail != null) onMissionFail.run();
    }

    /**
     * Advance mission timer each game tick (call from GameScreen.render with delta).
     */
    public void tick(float delta) {
        if (activeMissionId == null) return;
        missionTimer += delta;
        // Auto-fail on time limit
        MissionDefinition def = definitions.get(activeMissionId);
        if (def != null && def.timeLimit > 0f && missionTimer >= def.timeLimit) {
            failMission();
        }
    }

    // ── Callbacks ─────────────────────────────────────────────────────────────

    public void setOnMissionComplete(Runnable cb)                              { onMissionComplete   = cb; }
    public void setOnMissionFail(Runnable cb)                                  { onMissionFail       = cb; }
    public void setOnObjectiveComplete(java.util.function.Consumer<String> cb) { onObjectiveComplete = cb; }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private boolean checkAllObjectivesMet(MissionDefinition def) {
        for (MissionObjective obj : def.objectives) {
            int needed = switch (obj.type) {
                case COLLECT_ITEMS     -> obj.count;
                case KILL_ALL_ENEMIES,
                     ACTIVATE_SWITCHES -> obj.target;
                default                -> 1;
            };
            String key = obj.type.name().toLowerCase() + "_" + (obj.item != null ? obj.item : "");
            if (objectiveProgress.getOrDefault(key, 0) < needed) return false;
        }
        return true;
    }
}
