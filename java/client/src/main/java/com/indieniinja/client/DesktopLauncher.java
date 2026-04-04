package com.indieniinja.client;

import com.badlogic.gdx.backends.lwjgl3.Lwjgl3Application;
import com.badlogic.gdx.backends.lwjgl3.Lwjgl3ApplicationConfiguration;

/**
 * LWJGL3 desktop entry point for the Java libGDX client.
 *
 * Usage:
 *   java -jar ninja-client.jar [host] [port]
 *   java -jar ninja-client.jar 127.0.0.1 7777
 *
 * Defaults: host=127.0.0.1, port=7777
 */
public final class DesktopLauncher {

    public static void main(String[] args) {
        String host = args.length > 0 ? args[0] : "127.0.0.1";
        int    port = args.length > 1 ? Integer.parseInt(args[1]) : 7777;

        Lwjgl3ApplicationConfiguration cfg = new Lwjgl3ApplicationConfiguration();
        cfg.setTitle("Indie Ninja Adventures");
        cfg.setWindowedMode(1280, 720);
        cfg.setForegroundFPS(0);   // uncapped — NinjaGameClient drives its own fixed timestep
        cfg.useVsync(true);
        cfg.setResizable(true);
        cfg.setWindowIcon("icon.png");  // loaded from assets/ if present

        new Lwjgl3Application(new NinjaGameClient(host, port), cfg);
    }
}
