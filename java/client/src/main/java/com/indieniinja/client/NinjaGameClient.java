package com.indieniinja.client;

import com.badlogic.gdx.Game;
import com.indieniinja.client.ui.MainMenuScreen;

/**
 * Top-level libGDX Game for the Java client.
 *
 * Manages the screen stack:
 *   MainMenuScreen  →  (click CONNECT)  →  GameScreen
 *   GameScreen      →  (ESC)            →  PauseScreen overlay
 *   PauseScreen     →  (MAIN MENU btn)  →  MainMenuScreen
 *
 * All rendering logic lives in GameScreen; menus live in the ui/ package.
 */
public final class NinjaGameClient extends Game {

    private final String host;
    private final int    port;
    private final String replayPath;

    public NinjaGameClient(String host, int port) {
        this(host, port, null);
    }

    public NinjaGameClient(String host, int port, String replayPath) {
        this.host       = host;
        this.port       = port;
        this.replayPath = replayPath;
    }

    @Override
    public void create() {
        if (replayPath != null) {
            setScreen(new GameScreen(this, host, port, "solo", replayPath));
        } else {
            setScreen(new MainMenuScreen(this, host, port));
        }
    }

    // ── Accessors used by PauseScreen to navigate back to the menu ────────────

    public String getHost() { return host; }
    public int    getPort() { return port; }
}
