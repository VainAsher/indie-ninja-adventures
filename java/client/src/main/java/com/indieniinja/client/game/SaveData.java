package com.indieniinja.client.game;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Top-level save data model.
 *
 * Java port of Python systems/save_system.py SaveData dataclass.
 * Serialized as JSON to user_data/saves/savegame.json.
 *
 * Structure mirrors Python's save file:
 *   version, save_date, player_progress, settings, statistics, campaign
 */
public final class SaveData {

    // ── Constants ─────────────────────────────────────────────────────────────
    public static final String CURRENT_VERSION = "0.10.63";

    // ── Fields ────────────────────────────────────────────────────────────────
    public String version  = CURRENT_VERSION;
    public String saveDate = "";

    // ── Player progress ───────────────────────────────────────────────────────
    public List<String>          levelsCompleted    = new ArrayList<>();
    public String                currentLevel       = "level_1";
    public float                 totalPlaytime      = 0f;   // seconds
    public int                   totalCoins         = 0;
    public int                   totalCollectibles  = 0;
    public int                   totalDeaths        = 0;
    public Map<String, Float>    bestTimes          = new HashMap<>();  // missionId → seconds
    public List<String>          tutorialsSeen      = new ArrayList<>();

    // ── Settings ──────────────────────────────────────────────────────────────
    public float   masterVolume   = 1.0f;
    public float   musicVolume    = 0.7f;
    public float   sfxVolume      = 0.8f;
    public boolean fullscreen     = false;
    public int     windowWidth    = 1280;
    public int     windowHeight   = 720;
    public boolean vsync          = true;
    public boolean showFps        = false;
    public boolean cameraShake    = true;
    public boolean screenFlash    = true;
    public boolean particles      = true;
    public String  controlScheme  = "keyboard";

    // ── Statistics ────────────────────────────────────────────────────────────
    public float totalPlaytimeStat       = 0f;
    public int   totalLevelsCompleted    = 0;
    public int   totalDeathsStat         = 0;
    public int   totalCoinsCollected     = 0;
    public int   totalCollectiblesFound  = 0;
    public int   totalDamageTaken        = 0;
    public int   totalJumps              = 0;
    public int   totalDashes             = 0;
    public float fastestLevelTime        = 0f;
    public int   perfectRuns             = 0;

    // ── Campaign ──────────────────────────────────────────────────────────────
    public long              worldSeed           = 0L;
    public String            currentHubId        = "central_hub";
    public float             currentHubX         = 0f;
    public float             currentHubY         = 0f;
    public List<String>      unlockedRegions     = new ArrayList<>();
    public List<String>      completedMissions   = new ArrayList<>();
    public List<String>      unlockedAbilities   = new ArrayList<>();
    public Map<String,Integer> missionAttempts   = new HashMap<>();
    public Map<String,Float>   missionBestTimes  = new HashMap<>();
    public Map<String,Integer> playerInventory   = new HashMap<>();
    public String            equippedWeapon      = null;
    public String            equippedArmor       = null;
    public int               currency            = 0;
    public List<String>      defeatedBosses      = new ArrayList<>();
    /** Set of "gridX,gridY" room keys the player has visited (per world seed). */
    public List<String>      visitedRoomKeys     = new ArrayList<>();
    /** Total enemies killed across all sessions. */
    public int               totalEnemiesKilled  = 0;
    /** Unlocked achievements by id. */
    public List<String>      achievements        = new ArrayList<>();

    // ── Story state ───────────────────────────────────────────────────────────
    /** Serialized StoryManager flags — matches Python story_manager.to_dict(). */
    public int               storyAct            = 0;
    public int               hubDegradationLevel = 0;
    public int               lanternsMetCount    = 0;
    public boolean           veilMaidenEncountered = false;
    public Map<String,String> storyFlags         = new HashMap<>();

    // ── Mission manager state ─────────────────────────────────────────────────
    /** Active mission id at time of save, or null. */
    public String            activeMissionId     = null;
    public float             missionTimer        = 0f;
    public Map<String,MissionState> missionStates= new HashMap<>();

    // ── Serialization helpers ─────────────────────────────────────────────────

    /**
     * Build a SaveData from the current state of the three managers.
     * Python equivalent: SaveData is populated by calling save_to_dict() on each manager.
     */
    public static SaveData capture(StoryManager story, MissionManager missions) {
        SaveData d = new SaveData();
        d.saveDate = java.time.LocalDateTime.now()
                         .format(java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));

        // Story
        d.storyAct = story.currentAct().wire();
        Map<String,String> ctx = story.toConditionContext();
        d.hubDegradationLevel = parseInt(ctx, "hub_degradation_level", 0);
        d.lanternsMetCount    = parseInt(ctx, "lanterns_met", 0);
        d.veilMaidenEncountered = Boolean.parseBoolean(
            ctx.getOrDefault("veil_maiden_encountered", "false"));
        ctx.remove("act");
        ctx.remove("hub_degradation_level");
        ctx.remove("lanterns_met");
        ctx.remove("veil_maiden_encountered");
        ctx.remove("veil_maiden_defeated_act1");
        ctx.remove("veil_maiden_defeated_final");
        ctx.remove("yin_yang_present");
        d.storyFlags = new HashMap<>(ctx);

        // Missions
        d.completedMissions = new ArrayList<>();
        d.missionStates     = new HashMap<>();
        d.missionBestTimes  = new HashMap<>(missions.getBestTimes());
        d.missionAttempts   = new HashMap<>(missions.getAttempts());
        for (String id : missions.getAllDefinitionIds()) {
            MissionState ms = missions.getState(id);
            d.missionStates.put(id, ms);
            if (ms == MissionState.COMPLETED) d.completedMissions.add(id);
        }
        d.activeMissionId = missions.getActiveMissionId();
        d.missionTimer    = missions.getMissionTimer();

        return d;
    }

    /**
     * Restore the three managers from a loaded SaveData.
     */
    public void restore(StoryManager story, MissionManager missions) {
        // Restore story
        Act[] acts = Act.values();
        if (storyAct >= 0 && storyAct < acts.length) story.setAct(acts[storyAct]);
        for (Map.Entry<String,String> e : storyFlags.entrySet())
            story.setFlag(e.getKey(), e.getValue());

        // Restore missions
        for (Map.Entry<String,MissionState> e : missionStates.entrySet()) {
            if (e.getValue() == MissionState.COMPLETED) missions.markCompleted(e.getKey());
        }
        missions.restoreBestTimes(missionBestTimes);
        missions.restoreAttempts(missionAttempts);
    }

    private static int parseInt(Map<String,String> m, String key, int def) {
        try { return Integer.parseInt(m.getOrDefault(key, String.valueOf(def))); }
        catch (NumberFormatException e) { return def; }
    }
}
