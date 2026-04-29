package com.indieniinja.client.game.cutscene;

/**
 * Narrow camera surface used by CutsceneManager.
 *
 * CS-12 resolves coordinate targets now; marker and entity resolution are added
 * by later Phase 2 slices without widening the sequencer's dependency on
 * GameScreen.
 */
public interface CutsceneCameraController {
    void setCutsceneFocus(float worldX, float worldY);

    void panTo(float worldX, float worldY, float duration);

    void updateCutscene(float delta);

    boolean isCutscenePanActive();

    void restorePlayerFollow();
}
