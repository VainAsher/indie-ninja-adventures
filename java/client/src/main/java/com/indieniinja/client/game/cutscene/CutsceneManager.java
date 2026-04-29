package com.indieniinja.client.game.cutscene;

import com.indieniinja.client.game.DialogueManager;
import com.indieniinja.client.game.StoryManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.function.Consumer;

/**
 * Runtime orchestrator for data-driven cutscenes.
 *
 * Responsibilities:
 *   - Start a cutscene by id (checks start conditions, rejects if one already active).
 *   - Step through CutsceneStep actions each tick.
 *   - Lock / unlock player input via a callback.
 *   - Mark completion flags in StoryManager and the completed-set.
 *   - Skip according to SkipPolicy.
 *   - Interrupt safely on map transition or load (always unlocks player).
 *
 * Phase 1 step types handled: LOCK_PLAYER, UNLOCK_PLAYER, DIALOGUE, WAIT, SET_FLAG.
 * Phase 2 step types (CAMERA_*, ENTITY_*) are forwarded to extension hooks
 * and logged as unimplemented; they do not crash the sequencer.
 */
public final class CutsceneManager {

    private static final Logger log = LoggerFactory.getLogger(CutsceneManager.class);

    // ── Injected dependencies ─────────────────────────────────────────────────

    private final Map<String, CutsceneDefinition> definitions;
    private final StoryManager   story;
    private final DialogueManager dialogue;
    private final CutsceneCameraController camera;
    private final CutsceneMarkerRegistry markers;
    private final CutsceneEntityController entities;

    /** Called with true to lock player input, false to unlock. */
    private final Consumer<Boolean> playerLockCallback;

    /** Called when a cutscene completes (with the cutscene id). */
    private Consumer<String> onCompleteCallback = id -> {};

    // ── Persistent completed set ──────────────────────────────────────────────

    /** Ids of cutscenes that have been fully completed. Persisted via SaveData. */
    private final Set<String> completedIds;

    // ── Active-scene state ────────────────────────────────────────────────────

    private CutsceneDefinition active     = null;
    private int                stepIndex  = 0;
    private float              waitTimer  = 0f;
    private boolean            waitingForDialogue = false;
    private boolean            waitingForCameraPan = false;
    private String             waitingForEntityMove = null;
    private boolean            firstViewComplete  = false; // tracks first-view for ALLOW_AFTER_FIRST_VIEW

    public CutsceneManager(Map<String, CutsceneDefinition> definitions,
                           StoryManager story,
                           DialogueManager dialogue,
                           Consumer<Boolean> playerLockCallback,
                           Set<String> completedIds) {
        this(definitions, story, dialogue, playerLockCallback, completedIds,
                null, CutsceneMarkerRegistry.empty(), null);
    }

    public CutsceneManager(Map<String, CutsceneDefinition> definitions,
                           StoryManager story,
                           DialogueManager dialogue,
                           Consumer<Boolean> playerLockCallback,
                           Set<String> completedIds,
                           CutsceneCameraController camera) {
        this(definitions, story, dialogue, playerLockCallback, completedIds,
                camera, CutsceneMarkerRegistry.empty(), null);
    }

    public CutsceneManager(Map<String, CutsceneDefinition> definitions,
                           StoryManager story,
                           DialogueManager dialogue,
                           Consumer<Boolean> playerLockCallback,
                           Set<String> completedIds,
                           CutsceneCameraController camera,
                           CutsceneMarkerRegistry markers) {
        this(definitions, story, dialogue, playerLockCallback, completedIds, camera, markers, null);
    }

    public CutsceneManager(Map<String, CutsceneDefinition> definitions,
                           StoryManager story,
                           DialogueManager dialogue,
                           Consumer<Boolean> playerLockCallback,
                           Set<String> completedIds,
                           CutsceneCameraController camera,
                           CutsceneMarkerRegistry markers,
                           CutsceneEntityController entities) {
        this.definitions        = definitions;
        this.story              = story;
        this.dialogue           = dialogue;
        this.playerLockCallback = playerLockCallback;
        this.completedIds       = completedIds;
        this.camera             = camera;
        this.markers            = markers != null ? markers : CutsceneMarkerRegistry.empty();
        this.entities           = entities;
    }

    public void setOnCompleteCallback(Consumer<String> cb) {
        this.onCompleteCallback = cb != null ? cb : id -> {};
    }

    // ── Public API ────────────────────────────────────────────────────────────

    /** Returns true while a cutscene is playing. */
    public boolean isActive() { return active != null; }

    /** Returns the id of the currently active cutscene, or null. */
    public String activeId() { return active != null ? active.id : null; }

    public Set<String> completedIds() { return Collections.unmodifiableSet(completedIds); }

    public Map<String, CutsceneDefinition> definitions() {
        return Collections.unmodifiableMap(definitions);
    }

    /**
     * Attempt to start a cutscene by id.
     *
     * @param id  the cutscene id
     * @param force  if true, bypass start conditions (DevConsole use)
     * @return true if the cutscene started successfully
     */
    public boolean start(String id, boolean force) {
        CutsceneDefinition def = definitions.get(id);
        if (def == null) {
            log.warn("[CutsceneManager] unknown cutscene id '{}'", id);
            return false;
        }
        if (active != null) {
            log.warn("[CutsceneManager] rejecting '{}' — '{}' already active", id, active.id);
            return false;
        }
        if (!force) {
            if (completedIds.contains(id) &&
                    def.skipPolicy != SkipPolicy.ALWAYS) {
                // One-shot check: already seen and not configured to replay
                if (def.skipPolicy != SkipPolicy.DEBUG_ONLY) {
                    log.debug("[CutsceneManager] '{}' already completed, skipping", id);
                    return false;
                }
            }
            if (!def.conditionsMet(story)) {
                log.debug("[CutsceneManager] '{}' start conditions not met", id);
                return false;
            }
        }
        active            = def;
        stepIndex         = 0;
        waitTimer         = 0f;
        waitingForDialogue = false;
        waitingForCameraPan = false;
        waitingForEntityMove = null;
        firstViewComplete = completedIds.contains(id);
        log.info("[CutsceneManager] starting '{}'", id);
        advanceToNextReady();
        return true;
    }

    /** Convenience: start with conditions checked (normal gameplay path). */
    public boolean start(String id) { return start(id, false); }

    /**
     * Advance the active cutscene by {@code delta} seconds.
     * Call once per render/logic tick from GameScreen.
     */
    public void tick(float delta) {
        if (active == null) return;

        // DIALOGUE step: wait for player to advance the dialogue
        if (waitingForDialogue) {
            if (!dialogue.isActive()) {
                waitingForDialogue = false;
                stepIndex++;
                advanceToNextReady();
            }
            return;
        }

        if (waitingForCameraPan) {
            if (camera != null) {
                camera.updateCutscene(delta);
                if (!camera.isCutscenePanActive()) {
                    waitingForCameraPan = false;
                    stepIndex++;
                    advanceToNextReady();
                }
            } else {
                waitingForCameraPan = false;
                stepIndex++;
                advanceToNextReady();
            }
            return;
        }

        if (waitingForEntityMove != null) {
            if (entities != null) {
                entities.updateCutsceneEntities(delta);
                if (!entities.isEntityMoveActive(waitingForEntityMove)) {
                    waitingForEntityMove = null;
                    stepIndex++;
                    advanceToNextReady();
                }
            } else {
                waitingForEntityMove = null;
                stepIndex++;
                advanceToNextReady();
            }
            return;
        }

        // WAIT step: count down
        if (waitTimer > 0f) {
            waitTimer -= delta;
            if (waitTimer <= 0f) {
                waitTimer = 0f;
                stepIndex++;
                advanceToNextReady();
            }
            return;
        }
    }

    /**
     * Skip the active cutscene if its policy allows it.
     * Always writes completion flags and restores player control.
     */
    public boolean skip() {
        if (active == null) return false;
        SkipPolicy policy = active.skipPolicy;

        boolean allowed = switch (policy) {
            case ALWAYS                -> true;
            case NEVER                 -> false;
            case ALLOW_AFTER_FIRST_VIEW -> firstViewComplete;
            case DEBUG_ONLY            -> false; // honour at runtime; DevConsole bypasses
        };

        if (!allowed) {
            log.debug("[CutsceneManager] skip blocked by policy {} for '{}'", policy, active.id);
            return false;
        }
        log.info("[CutsceneManager] skipping '{}'", active.id);
        complete();
        return true;
    }

    /**
     * Interrupt the active cutscene without writing completion flags.
     * Use on map transition or save/load. Always unlocks player.
     */
    public void interrupt() {
        if (active == null) return;
        log.info("[CutsceneManager] interrupting '{}'", active.id);
        emergencyStop();
    }

    /**
     * Forcibly stop everything and release player input lock.
     * Safe to call at any time — even when no cutscene is active.
     */
    public void emergencyStop() {
        if (active != null) {
            log.warn("[CutsceneManager] emergency stop on '{}'", active.id);
        }
        dialogue.endDialogue();
        playerLockCallback.accept(false);
        restoreCamera();
        active            = null;
        stepIndex         = 0;
        waitTimer         = 0f;
        waitingForDialogue = false;
        waitingForCameraPan = false;
        waitingForEntityMove = null;
    }

    /** Remove a completed id so the cutscene can replay. (DevConsole reset.) */
    public void resetCompleted(String id) {
        completedIds.remove(id);
        log.info("[CutsceneManager] reset completed flag for '{}'", id);
    }

    // ── Internal sequencing ───────────────────────────────────────────────────

    private void advanceToNextReady() {
        while (active != null && stepIndex < active.steps.size()) {
            CutsceneStep step = active.steps.get(stepIndex);
            boolean consumed = executeStep(step);
            if (!consumed) break; // step is async — return and wait for tick()
        }
        if (active != null && stepIndex >= active.steps.size()) {
            complete();
        }
    }

    /**
     * Execute one step.
     * @return true if the step completed synchronously and the loop should advance;
     *         false if the step is async (WAIT, DIALOGUE) and the loop must pause.
     */
    private boolean executeStep(CutsceneStep step) {
        log.debug("[CutsceneManager] '{}' step[{}] {}", active.id, stepIndex, step.type);
        return switch (step.type) {

            case LOCK_PLAYER -> {
                playerLockCallback.accept(true);
                stepIndex++;
                yield true;
            }
            case UNLOCK_PLAYER -> {
                playerLockCallback.accept(false);
                stepIndex++;
                yield true;
            }

            case SET_FLAG -> {
                if (step.flag != null) {
                    String val = step.value != null ? step.value : "true";
                    story.setFlag(step.flag, val);
                    log.debug("[CutsceneManager] set flag '{}' = '{}'", step.flag, val);
                }
                stepIndex++;
                yield true;
            }

            case DIALOGUE -> {
                String speaker = step.speaker != null ? step.speaker : "";
                String text    = step.textKey  != null ? step.textKey  : "";
                dialogue.startInline(speaker, text);
                waitingForDialogue = true;
                yield false; // async — tick() handles the wait
            }

            case WAIT -> {
                waitTimer = step.duration > 0f ? step.duration : 0f;
                if (waitTimer <= 0f) {
                    stepIndex++;
                    yield true;
                }
                yield false; // async
            }

            case CAMERA_FOCUS -> {
                float[] target = coordinateTarget(step.target);
                if (camera != null && target != null) {
                    camera.setCutsceneFocus(target[0], target[1]);
                } else {
                    log.warn("[CutsceneManager] camera_focus target '{}' could not be resolved", step.target);
                }
                stepIndex++;
                yield true;
            }

            case CAMERA_PAN -> {
                float[] target = coordinateTarget(step.target);
                if (camera != null && target != null) {
                    camera.panTo(target[0], target[1], step.duration);
                    if (camera.isCutscenePanActive()) {
                        waitingForCameraPan = true;
                        yield false;
                    }
                } else {
                    log.warn("[CutsceneManager] camera_pan target '{}' could not be resolved", step.target);
                }
                stepIndex++;
                yield true;
            }

            case CAMERA_RESTORE_PLAYER -> {
                restoreCamera();
                stepIndex++;
                yield true;
            }

            case ENTITY_FACE -> {
                float[] target = coordinateTarget(step.target);
                if (entities != null && step.entity != null && target != null) {
                    entities.faceEntity(step.entity, target[0], target[1]);
                } else {
                    log.warn("[CutsceneManager] entity_face target '{}' for '{}' could not be resolved",
                            step.target, step.entity);
                }
                stepIndex++;
                yield true;
            }

            case ENTITY_MOVE_TO -> {
                float[] target = coordinateTarget(step.target);
                if (entities != null && step.entity != null && target != null) {
                    entities.moveEntityTo(step.entity, target[0], target[1], step.duration);
                    if (entities.isEntityMoveActive(step.entity)) {
                        waitingForEntityMove = step.entity;
                        yield false;
                    }
                } else {
                    log.warn("[CutsceneManager] entity_move_to target '{}' for '{}' could not be resolved",
                            step.target, step.entity);
                }
                stepIndex++;
                yield true;
            }

            case ENTITY_SET_VISIBLE -> {
                if (entities != null && step.entity != null) {
                    entities.setVisible(step.entity, Boolean.parseBoolean(step.value));
                }
                stepIndex++;
                yield true;
            }

            case ENTITY_PLAY_ANIM -> {
                if (entities != null && step.entity != null && step.value != null) {
                    entities.playAnimation(step.entity, step.value);
                }
                stepIndex++;
                yield true;
            }

            case FADE_IN, FADE_OUT, TITLE_CARD, HUB_CHANGE, START_MISSION -> {
                log.warn("[CutsceneManager] step type {} not yet implemented — skipping", step.type);
                stepIndex++;
                yield true;
            }
        };
    }

    private void complete() {
        String id = active.id;
        // Write completion flags to StoryManager
        for (String flag : active.completionFlags) {
            story.setFlag(flag, "true");
        }
        completedIds.add(id);
        playerLockCallback.accept(false);
        restoreCamera();
        dialogue.endDialogue();
        active            = null;
        stepIndex         = 0;
        waitTimer         = 0f;
        waitingForDialogue = false;
        waitingForCameraPan = false;
        waitingForEntityMove = null;
        log.info("[CutsceneManager] completed '{}'", id);
        onCompleteCallback.accept(id);
    }

    private void restoreCamera() {
        if (camera != null) {
            camera.restorePlayerFollow();
        }
    }

    private float[] coordinateTarget(String target) {
        if (target == null || target.isBlank()) return null;
        String[] parts = target.split(",");
        if (parts.length != 2) return markerTarget(target);
        try {
            return new float[] {
                    Float.parseFloat(parts[0].trim()),
                    Float.parseFloat(parts[1].trim())
            };
        } catch (NumberFormatException e) {
            return markerTarget(target);
        }
    }

    private float[] markerTarget(String target) {
        return markers.resolve(target)
                .map(marker -> new float[] { marker.worldX(), marker.worldY() })
                .orElse(null);
    }
}
