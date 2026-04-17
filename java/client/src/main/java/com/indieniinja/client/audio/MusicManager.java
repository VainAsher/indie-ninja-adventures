package com.indieniinja.client.audio;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.audio.Music;
import com.badlogic.gdx.files.FileHandle;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.Map;

/**
 * Zone-based BGM manager with linear cross-fade.
 *
 * Tracks are keyed "zone" or "zone_act{N}" so Act-specific variants
 * (e.g. "hollow_depths_act2") override the generic zone track.
 * If an asset file is missing the transition is silently skipped.
 *
 * Call update(delta) every render frame. Call playZone(hubId, act) on
 * hub transitions or act changes.
 */
public final class MusicManager {

    private static final Logger log = LoggerFactory.getLogger(MusicManager.class);

    private static final float FADE_DURATION = 1.5f;

    private final Map<String, Music> tracks = new HashMap<>();

    private Music  current;
    private Music  incoming;
    private String currentKey = "";
    private String incomingKey = "";

    private float  fadeOutTimer  = 0f;
    private float  fadeInTimer   = 0f;
    private boolean crossFading  = false;

    private float masterVolume = 0.7f;

    // ── Loading ───────────────────────────────────────────────────────────────

    /**
     * Load BGM files from musicDir. Expected filenames: {zoneId}.ogg (or .mp3/.wav).
     * Act variants: {zoneId}_act{N}.ogg (e.g. hollow_depths_act2.ogg).
     * Silently skips missing files.
     */
    public void loadTracks(FileHandle musicDir) {
        if (!musicDir.exists()) {
            log.info("[Music] Music directory absent — all BGM silent: {}", musicDir.path());
            return;
        }
        for (FileHandle fh : musicDir.list()) {
            String name = fh.nameWithoutExtension();
            try {
                Music m = Gdx.audio.newMusic(fh);
                m.setLooping(true);
                m.setVolume(0f);
                tracks.put(name, m);
            } catch (Exception ex) {
                log.warn("[Music] Failed to load {}: {}", fh.path(), ex.getMessage());
            }
        }
        log.info("[Music] Loaded {} track(s) from {}", tracks.size(), musicDir.path());
    }

    // ── Zone transitions ──────────────────────────────────────────────────────

    /**
     * Request a zone BGM change. Resolves act-specific variant first, then
     * falls back to generic zone track. No-op if the resolved key is already
     * playing.
     */
    public void playZone(String hubId, int act) {
        if (hubId == null || hubId.isBlank()) return;

        String zoneKey = hubId.toLowerCase().replace("-", "_").replace(" ", "_");
        String actKey  = zoneKey + "_act" + act;

        String resolvedKey = tracks.containsKey(actKey) ? actKey
                           : tracks.containsKey(zoneKey) ? zoneKey
                           : null;

        if (resolvedKey == null) {
            // No track for this zone — silence current after fade
            if (!currentKey.isEmpty()) startCrossFadeTo(null, "");
            return;
        }

        if (resolvedKey.equals(currentKey) && !crossFading) return;

        startCrossFadeTo(tracks.get(resolvedKey), resolvedKey);
    }

    /** Stop all music immediately (used on pause/menu transitions). */
    public void stop() {
        crossFading = false;
        if (incoming != null) { incoming.stop(); incoming.setVolume(0f); }
        if (current  != null) { current.stop();  current.setVolume(0f); }
        incoming   = null;
        incomingKey = "";
    }

    // ── Update ────────────────────────────────────────────────────────────────

    /**
     * Drive cross-fade progress. Call every render frame with the frame delta.
     */
    public void update(float delta) {
        if (!crossFading) return;

        fadeOutTimer  = Math.min(fadeOutTimer  + delta, FADE_DURATION);
        fadeInTimer   = Math.min(fadeInTimer   + delta, FADE_DURATION);

        float outFrac = fadeOutTimer  / FADE_DURATION;
        float inFrac  = fadeInTimer   / FADE_DURATION;

        if (current  != null) current.setVolume(masterVolume * (1f - outFrac));
        if (incoming != null) incoming.setVolume(masterVolume * inFrac);

        if (fadeOutTimer >= FADE_DURATION) {
            if (current != null) { current.stop(); current.setVolume(0f); }
            current    = incoming;
            currentKey = incomingKey;
            incoming   = null;
            incomingKey = "";
            crossFading = false;

            if (current != null) current.setVolume(masterVolume);
        }
    }

    // ── Volume ────────────────────────────────────────────────────────────────

    public void setVolume(float vol) {
        masterVolume = Math.max(0f, Math.min(1f, vol));
        if (current != null && !crossFading) current.setVolume(masterVolume);
    }

    public float getVolume() { return masterVolume; }

    // ── Lifecycle ─────────────────────────────────────────────────────────────

    public void dispose() {
        for (Music m : tracks.values()) m.dispose();
        tracks.clear();
        current  = null;
        incoming = null;
    }

    // ── Internal ──────────────────────────────────────────────────────────────

    private void startCrossFadeTo(Music next, String key) {
        if (crossFading && incoming != null) {
            incoming.stop();
            incoming.setVolume(0f);
        }

        incoming    = next;
        incomingKey = key;
        fadeOutTimer = 0f;
        fadeInTimer  = 0f;
        crossFading  = true;

        if (incoming != null && !incoming.isPlaying()) {
            incoming.setVolume(0f);
            incoming.play();
        }
    }
}
