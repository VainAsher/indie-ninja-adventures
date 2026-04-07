package com.indieniinja.client.audio;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.audio.Sound;
import com.badlogic.gdx.files.FileHandle;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.Map;

/**
 * SFX playback manager with silent fallback when assets are missing.
 *
 * Java port of Python audio/audio_manager.py AudioManager.
 *
 * Wraps libGDX {@link Sound}. If a sound file is missing, playback for that
 * name is silently skipped — the game never crashes due to missing audio.
 *
 * Usage:
 *   audioManager = new AudioManager(0.8f);
 *   audioManager.loadSounds(Gdx.files.internal("assets/audio/sfx"));
 *   audioManager.play("swing");
 *   audioManager.setVolume(0.5f);
 */
public final class AudioManager {

    private static final Logger log = LoggerFactory.getLogger(AudioManager.class);

    /** All expected SFX names — matches Python AudioManager._SFX_NAMES. */
    private static final String[] SFX_NAMES = {
        "swing",           // sword attack swing
        "hit_enemy",       // sword connects with enemy / boss
        "player_hurt",     // player takes non-lethal damage
        "player_death",    // player dies
        "jump",            // player jumps
        "land",            // player lands after being airborne
        "dash",            // dash ability activates
        "pickup_coin",     // coin collected
        "pickup_item",     // collectible or health pickup
        "menu_select",     // menu cursor moves
        "menu_confirm",    // menu item activated
        "inventory_open",  // inventory opened or closed
    };

    private static final String[] EXTENSIONS = { "wav", "ogg", "mp3" };

    private final Map<String, Sound> sounds = new HashMap<>();
    private float volume;

    public AudioManager(float sfxVolume) {
        this.volume = Math.max(0f, Math.min(1f, sfxVolume));
    }

    // ── Loading ───────────────────────────────────────────────────────────────

    /**
     * Load SFX files from sfxDir. Silently skips missing files.
     * Python parity: AudioManager.load_sounds(sfx_dir)
     */
    public void loadSounds(FileHandle sfxDir) {
        for (String name : SFX_NAMES) {
            for (String ext : EXTENSIONS) {
                FileHandle fh = sfxDir.child(name + "." + ext);
                if (fh.exists()) {
                    try {
                        Sound s = Gdx.audio.newSound(fh);
                        sounds.put(name, s);
                    } catch (Exception ex) {
                        log.warn("[Audio] Failed to load {}: {}", fh.path(), ex.getMessage());
                    }
                    break; // try next name once first matching ext is attempted
                }
            }
        }
        log.info("[Audio] Loaded {}/{} SFX from {}", sounds.size(), SFX_NAMES.length, sfxDir.path());
    }

    // ── Playback ──────────────────────────────────────────────────────────────

    /**
     * Play a named SFX. No-op if the sound was not loaded.
     * Python parity: AudioManager.play(name)
     */
    public void play(String name) {
        Sound s = sounds.get(name);
        if (s != null) s.play(volume);
    }

    // ── Volume ────────────────────────────────────────────────────────────────

    /**
     * Set SFX volume (0.0–1.0).
     * Already-playing sounds are not affected; new plays use the new volume.
     * Python parity: AudioManager.set_volume(vol)
     */
    public void setVolume(float vol) {
        this.volume = Math.max(0f, Math.min(1f, vol));
    }

    public float getVolume() { return volume; }

    // ── Lifecycle ─────────────────────────────────────────────────────────────

    public void dispose() {
        for (Sound s : sounds.values()) s.dispose();
        sounds.clear();
    }
}
