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
 * Slot layout (slots 1–3):
 *   Save file: user_data/saves/slot_N/savegame.json
 *   Checksum:  user_data/saves/slot_N/savegame.sha256
 *   Backups:   user_data/saves/slot_N/backups/savegame_<timestamp>.json  (last 3 kept)
 *
 * Legacy single-slot migration: if slot 1 is empty and the old
 *   user_data/saves/savegame.json exists, it is migrated automatically on first load.
 *
 * Format:    JSON via libGDX Json
 * Auto-save: every AUTO_SAVE_SECS seconds when dirty flag is set
 *
 * Usage:
 *   saveManager = new SaveManager(1, story, missions);
 *   saveManager.load();           // call once at startup
 *   saveManager.markDirty();      // whenever game state changes
 *   saveManager.tick(delta);      // each frame — drives auto-save
 *   saveManager.save();           // force save (on exit / level complete)
 */
public final class SaveManager {

    private static final Logger log = LoggerFactory.getLogger(SaveManager.class);

    public static final int MAX_SLOTS  = 3;

    /** Legacy single-slot path — only used for migration. */
    private static final String LEGACY_SAVE_PATH     = "user_data/saves/savegame.json";
    private static final String LEGACY_CHECKSUM_PATH = "user_data/saves/savegame.sha256";

    private static final int    MAX_BACKUPS    = 3;
    private static final float  AUTO_SAVE_SECS = 60f;

    private final int            slotIndex;
    private final String         savePath;
    private final String         checksumPath;
    private final String         backupDir;
    private final StoryManager   story;
    private final MissionManager missions;
    private final Json           json;

    private boolean  needsSave  = false;
    private float    saveTimer  = 0f;
    private boolean  saveExists = false;
    /** Live in-memory save data — updated each session; merged into capture() on write. */
    private SaveData liveData   = new SaveData();
    /** Optional callback invoked immediately before serializing save data. */
    private Runnable preSaveSync;

    /**
     * Create a SaveManager for the given slot (1–MAX_SLOTS).
     * Backward-compatible constructor kept for existing call sites that use slot 1.
     */
    public SaveManager(StoryManager story, MissionManager missions) {
        this(1, story, missions);
    }

    public SaveManager(int slotIndex, StoryManager story, MissionManager missions) {
        if (slotIndex < 1 || slotIndex > MAX_SLOTS) {
            throw new IllegalArgumentException("slotIndex must be 1–" + MAX_SLOTS);
        }
        this.slotIndex    = slotIndex;
        this.savePath     = "user_data/saves/slot_" + slotIndex + "/savegame.json";
        this.checksumPath = "user_data/saves/slot_" + slotIndex + "/savegame.sha256";
        this.backupDir    = "user_data/saves/slot_" + slotIndex + "/backups/";
        this.story        = story;
        this.missions     = missions;

        this.json = new Json();
        this.json.setOutputType(JsonWriter.OutputType.json);
    }

    // ── Slot discovery ────────────────────────────────────────────────────────

    /** Lightweight summary of an existing slot — shown on the slot-select screen. */
    public record SlotInfo(int slot, String saveDate, float totalPlaytime, String currentLevel) {
        public boolean isEmpty() { return saveDate == null || saveDate.isBlank(); }
    }

    /**
     * Return info for all slots without constructing full managers.
     * Safe to call before any game systems are initialised.
     */
    public static SlotInfo[] listSlots() {
        SlotInfo[] result = new SlotInfo[MAX_SLOTS];
        if (Gdx.app == null || Gdx.files == null) {
            for (int i = 0; i < MAX_SLOTS; i++) {
                result[i] = new SlotInfo(i + 1, null, 0f, null);
            }
            return result;
        }
        Json json = new Json();
        json.setOutputType(JsonWriter.OutputType.json);
        for (int i = 1; i <= MAX_SLOTS; i++) {
            String path = "user_data/saves/slot_" + i + "/savegame.json";
            FileHandle fh = Gdx.files.local(path);
            if (!fh.exists()) {
                result[i - 1] = new SlotInfo(i, null, 0f, null);
                continue;
            }
            try {
                SaveData d = json.fromJson(SaveData.class, fh.readString("UTF-8"));
                if (d == null) { result[i - 1] = new SlotInfo(i, null, 0f, null); continue; }
                result[i - 1] = new SlotInfo(i, d.saveDate, d.totalPlaytime, d.currentLevel);
            } catch (Exception ex) {
                result[i - 1] = new SlotInfo(i, "[corrupt]", 0f, null);
            }
        }
        return result;
    }

    // ── Public API ────────────────────────────────────────────────────────────

    /**
     * Load save data from disk and restore all managers.
     * For slot 1, migrates the legacy single-slot file if the slot directory is empty.
     * Returns true if a save was found and loaded.
     * Python parity: SaveManager.load()
     */
    public boolean load() {
        // Legacy migration: slot 1 is empty but old single-file save exists → copy it over.
        if (slotIndex == 1) {
            FileHandle legacy = Gdx.files.local(LEGACY_SAVE_PATH);
            FileHandle slotFh = Gdx.files.local(savePath);
            if (legacy.exists() && !slotFh.exists()) {
                try {
                    slotFh.writeString(legacy.readString("UTF-8"), false, "UTF-8");
                    FileHandle legacyCsum = Gdx.files.local(LEGACY_CHECKSUM_PATH);
                    if (legacyCsum.exists()) {
                        Gdx.files.local(checksumPath).writeString(legacyCsum.readString("UTF-8"), false, "UTF-8");
                    }
                    log.info("[Save] Migrated legacy save to slot 1");
                } catch (Exception ex) {
                    log.warn("[Save] Legacy migration failed: {}", ex.getMessage());
                }
            }
        }

        FileHandle fh = Gdx.files.local(savePath);
        if (!fh.exists()) {
            log.info("[Save] No save at {} — starting fresh", savePath);
            return false;
        }
        try {
            String content = fh.readString("UTF-8");

            // Checksum verification — reject corrupt saves before applying data.
            FileHandle checksumFh = Gdx.files.local(checksumPath);
            if (checksumFh.exists()) {
                String expected = checksumFh.readString("UTF-8").trim();
                String actual   = sha256Hex(content);
                if (!actual.equals(expected)) {
                    log.error("[Save] Checksum mismatch — save file may be corrupt. "
                        + "Expected {} got {}. Starting fresh.", expected, actual);
                    return false;
                }
            }

            SaveData data = json.fromJson(SaveData.class, content);
            if (data == null) { log.warn("[Save] Empty save file"); return false; }
            applyLoadedData(data);
            saveExists = true;
            log.info("[Save] Loaded v{} slot {} from {}", data.version, slotIndex, savePath);
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
            SaveData data = buildSaveSnapshotForWrite();

            // Rotate backups before overwriting
            FileHandle existing = Gdx.files.local(savePath);
            if (existing.exists()) rotateBackup(existing);

            // Write new save + checksum sidecar
            String jsonStr = json.prettyPrint(data);
            Gdx.files.local(savePath).writeString(jsonStr, false, "UTF-8");
            Gdx.files.local(checksumPath).writeString(sha256Hex(jsonStr), false, "UTF-8");
            liveData = deepCopy(data);
            saveExists = true;
            needsSave  = false;
            saveTimer  = 0f;
            log.debug("[Save] Saved slot {} to {} (checksum written)", slotIndex, savePath);
            return true;
        } catch (Exception ex) {
            log.error("[Save] Save failed: {}", ex.getMessage());
            return false;
        }
    }

    /** The slot index (1–MAX_SLOTS) this manager operates on. */
    public int getSlotIndex() { return slotIndex; }

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

    /** Set an optional callback used to refresh liveData immediately before save writes. */
    public void setPreSaveSync(Runnable preSaveSync) { this.preSaveSync = preSaveSync; }

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
            Gdx.files.local(backupDir + "savegame_" + ts + ".json")
                .writeString(source.readString("UTF-8"), false, "UTF-8");

            // Prune oldest backups beyond MAX_BACKUPS
            FileHandle backupDirFh = Gdx.files.local(backupDir);
            if (backupDirFh.exists()) {
                FileHandle[] backups = backupDirFh.list(".json");
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
        if (d.activeMissionObjectiveProgress == null) d.activeMissionObjectiveProgress = new java.util.HashMap<>();
        if (d.storyFlags        == null) d.storyFlags        = new java.util.HashMap<>();
        if (d.hubState == null || d.hubState.isBlank()) d.hubState = "FULL";
        else {
            try {
                d.hubState = com.indieniinja.world.HubState
                    .valueOf(d.hubState.trim().toUpperCase(java.util.Locale.ROOT))
                    .name();
            } catch (IllegalArgumentException ex) {
                d.hubState = "FULL";
            }
        }

        d.currency      = Math.min(d.currency,      999_999);
        d.totalPlaytime = Math.min(d.totalPlaytime,  360_000f);
        d.storyAct      = clampStoryActOrdinal(d.storyAct);
        return d;
    }

    static int clampStoryActOrdinal(int raw) {
        return Math.max(0, Math.min(raw, Act.values().length - 1));
    }

    /**
     * Apply loaded save data to runtime managers + liveData without filesystem access.
     * Package-private so roundtrip tests can validate load/write symmetry directly.
     */
    void applyLoadedData(SaveData loaded) {
        SaveData migrated = migrate(deepCopy(loaded));
        migrated.restore(story, missions);
        liveData = deepCopy(migrated);
    }

    /**
     * Build the next save snapshot by combining liveData with fresh manager state.
     * Package-private for direct roundtrip assertions in unit tests.
     */
    SaveData buildSaveSnapshotForWrite() {
        if (preSaveSync != null) {
            try { preSaveSync.run(); }
            catch (Exception e) { log.warn("[Save] pre-save sync hook failed: {}", e.getMessage()); }
        }
        SaveData data = deepCopy(liveData);
        SaveData captured = SaveData.capture(story, missions);
        overlayCapturedManagerState(data, captured);
        return data;
    }

    private static String sha256Hex(String content) {
        try {
            java.security.MessageDigest md = java.security.MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(content.getBytes(java.nio.charset.StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder(64);
            for (byte b : digest) sb.append(String.format("%02x", b));
            return sb.toString();
        } catch (java.security.NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 not available", e);
        }
    }

    private SaveData deepCopy(SaveData src) {
        if (src == null) return new SaveData();
        // libGDX Json cannot round-trip immutable collection impls from Map.of/List.of
        // because it serializes their concrete runtime type names (no default ctor).
        // Normalize to mutable JDK collections before JSON cloning.
        normalizeCollectionsForSerialization(src);
        SaveData copy = json.fromJson(SaveData.class, json.toJson(src));
        return copy != null ? copy : new SaveData();
    }

    private static void normalizeCollectionsForSerialization(SaveData d) {
        d.levelsCompleted = mutableList(d.levelsCompleted);
        d.bestTimes = mutableMap(d.bestTimes);
        d.tutorialsSeen = mutableList(d.tutorialsSeen);
        d.unlockedRegions = mutableList(d.unlockedRegions);
        d.completedMissions = mutableList(d.completedMissions);
        d.unlockedAbilities = mutableList(d.unlockedAbilities);
        d.missionAttempts = mutableMap(d.missionAttempts);
        d.missionBestTimes = mutableMap(d.missionBestTimes);
        d.playerInventory = mutableMap(d.playerInventory);
        d.defeatedBosses = mutableList(d.defeatedBosses);
        d.visitedRoomKeys = mutableList(d.visitedRoomKeys);
        d.achievements = mutableList(d.achievements);
        d.storyFlags = mutableMap(d.storyFlags);
        d.missionStates = mutableMap(d.missionStates);
        d.activeMissionObjectiveProgress = mutableMap(d.activeMissionObjectiveProgress);
    }

    private static <T> java.util.ArrayList<T> mutableList(java.util.List<T> in) {
        return in == null ? new java.util.ArrayList<>() : new java.util.ArrayList<>(in);
    }

    private static <K, V> java.util.HashMap<K, V> mutableMap(java.util.Map<K, V> in) {
        return in == null ? new java.util.HashMap<>() : new java.util.HashMap<>(in);
    }

    private static void overlayCapturedManagerState(SaveData base, SaveData captured) {
        base.version = captured.version;
        base.saveDate = captured.saveDate;

        base.storyAct = captured.storyAct;
        base.hubState = captured.hubState;
        base.hubDegradationLevel = captured.hubDegradationLevel;
        base.lanternsMetCount = captured.lanternsMetCount;
        base.veilMaidenEncountered = captured.veilMaidenEncountered;
        base.veilMaidenDefeatedAct1 = captured.veilMaidenDefeatedAct1;
        base.veilMaidenDefeatedFinal = captured.veilMaidenDefeatedFinal;
        base.yinYangPresent = captured.yinYangPresent;
        base.storyFlags = new java.util.HashMap<>(captured.storyFlags);

        base.completedMissions = new java.util.ArrayList<>(captured.completedMissions);
        base.missionStates = new java.util.HashMap<>(captured.missionStates);
        base.missionBestTimes = new java.util.HashMap<>(captured.missionBestTimes);
        base.missionAttempts = new java.util.HashMap<>(captured.missionAttempts);
        base.activeMissionId = captured.activeMissionId;
        base.missionTimer = captured.missionTimer;
        base.activeMissionObjectiveProgress =
            new java.util.HashMap<>(captured.activeMissionObjectiveProgress);
    }
}
