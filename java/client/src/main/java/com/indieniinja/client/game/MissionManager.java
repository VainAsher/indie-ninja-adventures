package com.indieniinja.client.game;

import com.badlogic.gdx.Gdx;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
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
        this(MissionDefinition.loadAll(Gdx.files.internal("data/missions.json")));
    }

    /** Test-friendly constructor for injecting mission definitions directly. */
    public MissionManager(Map<String, MissionDefinition> definitions) {
        this.definitions = new LinkedHashMap<>(definitions);
        // Mark all missions as NOT_STARTED initially; availability resolved on request
        for (String id : definitions.keySet()) states.put(id, MissionState.NOT_STARTED);
    }

    // ── Query ─────────────────────────────────────────────────────────────────

    public MissionDefinition     getDefinition(String id)  { return definitions.get(id); }
    public MissionDefinition     getActiveDefinition()     { return activeMissionId != null ? definitions.get(activeMissionId) : null; }
    public MissionState          getState(String id)       { return states.getOrDefault(id, MissionState.NOT_STARTED); }
    public boolean               isActive()               { return activeMissionId != null; }
    public String                getActiveMissionId()     { return activeMissionId; }
    public boolean               isExitLocked()           { return exitLocked; }
    public float                 getMissionTimer()        { return missionTimer; }
    public java.util.Set<String> getAllDefinitionIds()    { return definitions.keySet(); }
    public Map<String, Float>    getBestTimes()           { return java.util.Collections.unmodifiableMap(bestTimes); }
    public Map<String, Integer>  getAttempts()            { return java.util.Collections.unmodifiableMap(attempts); }
    public Map<String, MissionState> getStatesSnapshot()   { return new HashMap<>(states); }
    public Map<String, Integer>  getObjectiveProgressSnapshot() { return new HashMap<>(objectiveProgress); }

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

        String key = normalizeObjectiveKey(objectiveKey);
        objectiveProgress.merge(key, delta, Integer::sum);
        if (onObjectiveComplete != null) onObjectiveComplete.accept(objectiveKey);

        if (checkAllObjectivesMet(def)) {
            exitLocked = false;
        }
    }

    /** Objective adapter used by gameplay systems when enemies are defeated. */
    public void onEnemyKilled(int count) {
        if (count > 0) progressObjective(objectiveKey(ObjectiveType.KILL_ALL_ENEMIES, null), count);
    }

    /** Objective adapter used by gameplay systems when bosses are defeated. */
    public void onBossDefeated(String bossId) {
        progressObjective(objectiveKey(ObjectiveType.DEFEAT_BOSS, null), 1);
        if (bossId != null && !bossId.isBlank()) {
            progressObjective(objectiveKey(ObjectiveType.DEFEAT_BOSS, bossId), 1);
        }
    }

    /** Objective adapter used by gameplay systems when items are acquired. */
    public void onItemCollected(String itemId, int count) {
        if (itemId == null || itemId.isBlank() || count <= 0) return;
        progressObjective(objectiveKey(ObjectiveType.COLLECT_ITEMS, itemId), count);
    }

    /** Objective adapter used by gameplay systems when a switch is activated. */
    public void onSwitchActivated(String switchId) {
        if (activeMissionId == null) return;
        String active = normalizeObjectiveKey(activeMissionId);
        String tag = normalizeObjectiveKey(switchId);

        // Only mission-tagged switch activations should count.
        // Accepted forms:
        //   <missionId>
        //   <missionId>:<switchId>
        if (!(tag.equals(active) || tag.startsWith(active + ":"))) return;

        progressObjective(objectiveKey(ObjectiveType.ACTIVATE_SWITCHES, null), 1);
        if (!tag.isBlank()) progressObjective(objectiveKey(ObjectiveType.ACTIVATE_SWITCHES, tag), 1);
    }

    /** Objective adapter used by gameplay systems when a named location is reached. */
    public void onReachLocation(String locationId) {
        if (locationId == null || locationId.isBlank()) return;
        progressObjective(objectiveKey(ObjectiveType.REACH_LOCATION, locationId), 1);
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

    // ── Save/restore ─────────────────────────────────────────────────────────

    /** Mark a mission as completed without going through the full lifecycle. Used on load. */
    public void markCompleted(String missionId) {
        states.put(missionId, MissionState.COMPLETED);
    }

    /** Restore all known mission states (used during load). */
    public void restoreStates(Map<String, MissionState> restoredStates) {
        states.clear();
        for (String id : definitions.keySet()) {
            states.put(id, MissionState.NOT_STARTED);
        }
        if (restoredStates == null) return;
        for (Map.Entry<String, MissionState> e : restoredStates.entrySet()) {
            String id = e.getKey();
            MissionState state = e.getValue();
            if (id == null || state == null) continue;
            if (!definitions.containsKey(id)) continue;
            states.put(id, state);
        }
    }

    /**
     * Restore an active in-progress mission exactly as it was saved.
     * Objective progress is optional for backward compatibility.
     */
    public void restoreActiveMission(String missionId, float timer, Map<String, Integer> savedObjectiveProgress) {
        activeMissionId = null;
        missionTimer = 0f;
        exitLocked = false;
        objectiveProgress.clear();

        if (missionId == null || missionId.isBlank()) return;
        MissionDefinition def = definitions.get(missionId);
        if (def == null) return;

        activeMissionId = missionId;
        missionTimer = Math.max(0f, timer);
        if (savedObjectiveProgress != null) {
            for (Map.Entry<String, Integer> e : savedObjectiveProgress.entrySet()) {
                String key = normalizeObjectiveKey(e.getKey());
                if (key.isBlank()) continue;
                int value = Math.max(0, e.getValue() == null ? 0 : e.getValue());
                if (value > 0) objectiveProgress.put(key, value);
            }
        }
        states.put(missionId, MissionState.IN_PROGRESS);
        exitLocked = !checkAllObjectivesMet(def);
    }

    public void restoreBestTimes(Map<String, Float> data) {
        bestTimes.clear();
        if (data != null) bestTimes.putAll(data);
    }

    public void restoreAttempts(Map<String, Integer> data) {
        attempts.clear();
        if (data != null) attempts.putAll(data);
    }

    // ── Callbacks ─────────────────────────────────────────────────────────────

    public void setOnMissionComplete(Runnable cb)                              { onMissionComplete   = cb; }
    public void setOnMissionFail(Runnable cb)                                  { onMissionFail       = cb; }
    public void setOnObjectiveComplete(java.util.function.Consumer<String> cb) { onObjectiveComplete = cb; }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private boolean checkAllObjectivesMet(MissionDefinition def) {
        for (MissionObjective obj : def.objectives) {
            if (obj.type == ObjectiveType.TIME_CHALLENGE) {
                float limit = obj.timeLimit > 0f ? obj.timeLimit : def.timeLimit;
                if (limit > 0f && missionTimer > limit) return false;
                continue;
            }

            int needed = switch (obj.type) {
                case COLLECT_ITEMS     -> Math.max(1, obj.count);
                case KILL_ALL_ENEMIES  -> Math.max(1, obj.target);
                case ACTIVATE_SWITCHES -> Math.max(1, obj.count > 0 ? obj.count : obj.target);
                case REACH_LOCATION,
                     DEFEAT_BOSS       -> 1;
                default                -> 1;
            };
            String key = objectiveKeyForDefinition(obj);
            if (objectiveProgress.getOrDefault(key, 0) < needed) return false;
        }
        return true;
    }

    private String objectiveKeyForDefinition(MissionObjective obj) {
        return switch (obj.type) {
            case COLLECT_ITEMS     -> objectiveKey(obj.type, obj.item);
            case REACH_LOCATION    -> objectiveKey(obj.type, obj.location);
            case DEFEAT_BOSS       -> objectiveKey(obj.type, obj.boss);
            default                -> objectiveKey(obj.type, null);
        };
    }

    private String objectiveKey(ObjectiveType type, String qualifier) {
        String q = qualifier == null ? "" : qualifier.trim().toLowerCase(Locale.ROOT);
        return type.name().toLowerCase(Locale.ROOT) + "_" + q;
    }

    private String normalizeObjectiveKey(String key) {
        return key == null ? "" : key.trim().toLowerCase(Locale.ROOT);
    }
}
