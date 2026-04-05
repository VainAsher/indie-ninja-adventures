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

    public NinjaGameClient(String host, int port) {
        this.host = host;
        this.port = port;
    }

    @Override
    public void create() {
        setScreen(new MainMenuScreen(this, host, port));
    }

    // ── Accessors used by PauseScreen to navigate back to the menu ────────────

    public String getHost() { return host; }
    public int    getPort() { return port; }
}
