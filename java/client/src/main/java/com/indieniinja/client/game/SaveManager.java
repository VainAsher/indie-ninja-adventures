package com.indieniinja.client.game;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.files.FileHandle;
import com.badlogic.gdx.utils.Json;
import com.badlogic.gdx.utils.JsonWriter;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Manages save/load lifecycle for the campaign, missions, and story systems.
 *
 * Java port of Python systems/save_system.py SaveManager.
 *
 * Save file: user_data/saves/savegame.json  (same path as Python)
 * Backups:   user_data/saves/backups/savegame_<timestamp>.json  (last 3 kept)
 * Format:    JSON via libGDX Json
 * Auto-save: every AUTO_SAVE_SECS seconds when dirty flag is set
 *
 * Usage:
 *   saveManager = new SaveManager(story, missions);
 *   saveManager.load();           // call once at startup
 *   saveManager.markDirty();      // whenever game state changes
 *   saveManager.tick(delta);      // each frame — drives auto-save
 *   saveManager.save();           // force save (on exit / level complete)
 */
public final class SaveManager {

    private static final Logger log = LoggerFactory.getLogger(SaveManager.class);

    private static final String SAVE_PATH     = "user_data/saves/savegame.json";
    private static final String BACKUP_DIR    = "user_data/saves/backups/";
    private static final int    MAX_BACKUPS   = 3;
    private static final float  AUTO_SAVE_SECS = 60f;  // Python: 60s interval

    private final StoryManager   story;
    private final MissionManager missions;
    private final Json           json;

    private boolean  needsSave  = false;
    private float    saveTimer  = 0f;
    private boolean  saveExists = false;
    /** Live in-memory save data — updated each session; merged into capture() on write. */
    private SaveData liveData   = new SaveData();

    public SaveManager(StoryManager story, MissionManager missions) {
        this.story    = story;
        this.missions = missions;

        // Standard JSON output (not libGDX's minimal format)
        this.json = new Json();
        this.json.setOutputType(JsonWriter.OutputType.json);
    }

    // ── Public API ────────────────────────────────────────────────────────────

    /**
     * Load save data from disk and restore all managers.
     * Returns true if a save was found and loaded.
     * Python parity: SaveManager.load()
     */
    public boolean load() {
        FileHandle fh = Gdx.files.local(SAVE_PATH);
        if (!fh.exists()) {
            log.info("[Save] No save at {} — starting fresh", SAVE_PATH);
            return false;
        }
        try {
            SaveData data = json.fromJson(SaveData.class, fh.readString("UTF-8"));
            if (data == null) { log.warn("[Save] Empty save file"); return false; }
            data = migrate(data);
            data.restore(story, missions);
            // Sync runtime-tracked fields into liveData
            liveData.totalEnemiesKilled = data.totalEnemiesKilled;
            liveData.visitedRoomKeys    = data.visitedRoomKeys   != null ? data.visitedRoomKeys    : new java.util.ArrayList<>();
            liveData.achievements       = data.achievements       != null ? data.achievements       : new java.util.ArrayList<>();
            saveExists = true;
            log.info("[Save] Loaded v{} from {}", data.version, SAVE_PATH);
            return true;
        } catch (Exception ex) {
            log.error("[Save] Load failed: {} — starting fresh", ex.getMessage());
            return false;
        }
    }

    /**
     * Immediately serialize and write the save file, rotating backups first.
     * Python parity: SaveManager.save(force=True)
     */
    public boolean save() {
        try {
            SaveData data = SaveData.capture(story, missions);
            // Merge all runtime-tracked state from liveData (populated by GameScreen.syncSaveState())
            data.totalEnemiesKilled = liveData.totalEnemiesKilled;
            data.visitedRoomKeys    = new java.util.ArrayList<>(liveData.visitedRoomKeys);
            data.achievements       = new java.util.ArrayList<>(liveData.achievements);
            // Campaign / player state not accessible to SaveData.capture()
            if (liveData.worldSeed != 0)             data.worldSeed          = liveData.worldSeed;
            if (liveData.currency  != 0)             data.currency           = liveData.currency;
            if (liveData.playerInventory   != null)  data.playerInventory    = new java.util.HashMap<>(liveData.playerInventory);
            if (liveData.equippedWeapon    != null)  data.equippedWeapon     = liveData.equippedWeapon;
            if (liveData.equippedArmor     != null)  data.equippedArmor      = liveData.equippedArmor;
            if (liveData.unlockedAbilities != null && !liveData.unlockedAbilities.isEmpty())
                                                     data.unlockedAbilities  = new java.util.ArrayList<>(liveData.unlockedAbilities);
            if (liveData.defeatedBosses    != null && !liveData.defeatedBosses.isEmpty())
                                                     data.defeatedBosses     = new java.util.ArrayList<>(liveData.defeatedBosses);

            // Rotate backups before overwriting
            FileHandle existing = Gdx.files.local(SAVE_PATH);
            if (existing.exists()) rotateBackup(existing);

            // Write new save
            String jsonStr = json.prettyPrint(data);
            Gdx.files.local(SAVE_PATH).writeString(jsonStr, false, "UTF-8");
            saveExists = true;
            needsSave  = false;
            saveTimer  = 0f;
            log.debug("[Save] Saved to {}", SAVE_PATH);
            return true;
        } catch (Exception ex) {
            log.error("[Save] Save failed: {}", ex.getMessage());
            return false;
        }
    }

    /** Mark the save data as dirty (triggers auto-save at next interval). */
    public void markDirty() { needsSave = true; }

    /** True if a save file was loaded or written this session. */
    public boolean hasSave() { return saveExists; }

    /**
     * Returns the live in-memory SaveData for runtime stat tracking
     * (totalEnemiesKilled, visitedRoomKeys, achievements, etc.).
     * Changes are merged into the captured data on the next save.
     */
    public SaveData getSaveData() { return liveData; }

    /**
     * Advance the auto-save timer.  Call each game frame with delta seconds.
     * Python parity: SaveManager.auto_save(current_time)
     */
    public void tick(float delta) {
        if (!needsSave) return;
        saveTimer += delta;
        if (saveTimer >= AUTO_SAVE_SECS) save();
    }

    // ── Backup rotation ───────────────────────────────────────────────────────

    private void rotateBackup(FileHandle source) {
        try {
            String ts = java.time.LocalDateTime.now()
                .format(java.time.format.DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
            Gdx.files.local(BACKUP_DIR + "savegame_" + ts + ".json")
                .writeString(source.readString("UTF-8"), false, "UTF-8");

            // Prune oldest backups beyond MAX_BACKUPS
            FileHandle backupDir = Gdx.files.local(BACKUP_DIR);
            if (backupDir.exists()) {
                FileHandle[] backups = backupDir.list(".json");
                if (backups != null && backups.length > MAX_BACKUPS) {
                    java.util.Arrays.sort(backups, (a, b) -> a.name().compareTo(b.name()));
                    for (int i = 0; i < backups.length - MAX_BACKUPS; i++) backups[i].delete();
                }
            }
        } catch (Exception ex) {
            log.warn("[Save] Backup failed: {}", ex.getMessage());
        }
    }

    // ── Migration ─────────────────────────────────────────────────────────────

    /**
     * Ensure all fields exist and sanitise suspicious values.
     * Python parity: SaveManager._migrate_save()
     */
    private SaveData migrate(SaveData d) {
        if (d.levelsCompleted   == null) d.levelsCompleted   = new java.util.ArrayList<>();
        if (d.tutorialsSeen     == null) d.tutorialsSeen     = new java.util.ArrayList<>();
        if (d.unlockedRegions   == null) d.unlockedRegions   = new java.util.ArrayList<>();
        if (d.completedMissions == null) d.completedMissions = new java.util.ArrayList<>();
        if (d.unlockedAbilities == null) d.unlockedAbilities = new java.util.ArrayList<>();
        if (d.defeatedBosses    == null) d.defeatedBosses    = new java.util.ArrayList<>();
        if (d.visitedRoomKeys   == null) d.visitedRoomKeys   = new java.util.ArrayList<>();
        if (d.achievements      == null) d.achievements      = new java.util.ArrayList<>();
        if (d.bestTimes         == null) d.bestTimes         = new java.util.HashMap<>();
        if (d.missionBestTimes  == null) d.missionBestTimes  = new java.util.HashMap<>();
        if (d.missionAttempts   == null) d.missionAttempts   = new java.util.HashMap<>();
        if (d.playerInventory   == null) d.playerInventory   = new java.util.HashMap<>();
        if (d.missionStates     == null) d.missionStates     = new java.util.HashMap<>();
        if (d.storyFlags        == null) d.storyFlags        = new java.util.HashMap<>();

        d.currency      = Math.min(d.currency,      999_999);
        d.totalPlaytime = Math.min(d.totalPlaytime,  360_000f);
        d.storyAct      = Math.max(0, Math.min(d.storyAct, 4));
        return d;
    }
}
