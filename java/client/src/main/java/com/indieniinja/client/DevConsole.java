package com.indieniinja.client;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.Input;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.g2d.BitmapFont;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.indieniinja.content.ContentLoadException;
import com.indieniinja.content.ContentLoader;
import com.indieniinja.content.ContentRegistry;
import com.indieniinja.client.rendering.AnimationRegistry;
import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.SimPlayer;

import java.nio.file.Paths;
import java.util.*;
import java.util.function.Consumer;

/**
 * In-game developer console toggled by backtick (`).
 *
 * Disabled entirely when the system property "indie.release" is true.
 * No-op in multiplayer mode (when isMultiplayer is set).
 *
 * To disable in release builds, launch with: -Dindierelease=true
 * The Gradle shadowJar task can inject this via the manifest when -Prelease is passed.
 *
 * Commands are registered via {@link #register(String, String, CommandHandler)}.
 * Built-in commands: help, reload_content, reload_anims, spawn, teleport,
 *                    god, noclip, hud, fps, give_xp, set_health, clear, quit
 */
public final class DevConsole {

    /** False in release builds — disables all console functionality. */
    public static final boolean ENABLED = !Boolean.getBoolean("indie.release");

    private static final int   MAX_LOG_LINES  = 20;
    private static final int   CONSOLE_HEIGHT = 200;
    private static final float FONT_SCALE     = 1.0f;
    private static final Color BG_COLOR       = new Color(0f, 0f, 0f, 0.80f);
    private static final Color TEXT_COLOR     = new Color(0.9f, 0.9f, 0.9f, 1f);
    private static final Color INPUT_COLOR    = new Color(0.4f, 1f, 0.4f, 1f);
    private static final Color ERROR_COLOR    = new Color(1f, 0.4f, 0.4f, 1f);
    private static final Color INFO_COLOR     = new Color(0.6f, 0.8f, 1f, 1f);

    @FunctionalInterface
    public interface CommandHandler {
        void execute(String[] args, Consumer<String> log);
    }

    private final Map<String, CommandHandler> handlers     = new LinkedHashMap<>();
    private final Map<String, String>         descriptions = new LinkedHashMap<>();
    private final Deque<String>               logLines     = new ArrayDeque<>();

    private boolean visible      = false;
    private boolean isMultiplayer = false;
    private StringBuilder inputBuffer = new StringBuilder();

    // External refs injected by GameScreen
    private GameSimulator     sim;
    private AnimationRegistry anims;
    private ContentRegistry   contentRegistry;

    // Rendering
    private ShapeRenderer shapeRenderer;
    private BitmapFont    font;

    // Stateful toggle flags
    private boolean godMode   = false;
    private boolean noclip    = false;
    private boolean showFps   = false;
    private boolean showHud   = true;

    public DevConsole() {
        if (!ENABLED) return;
        registerBuiltins();
        // Guard: Gdx.app is null in headless unit tests — skip renderer construction.
        if (Gdx.app != null) {
            shapeRenderer = new ShapeRenderer();
            font = new BitmapFont();
            font.getData().setScale(FONT_SCALE);
        }
    }

    // ── Dependency injection ──────────────────────────────────────────────────

    public void setSimulator(GameSimulator sim)            { this.sim            = sim; }
    public void setAnimationRegistry(AnimationRegistry ar) { this.anims           = ar; }
    public void setContentRegistry(ContentRegistry cr)     { this.contentRegistry = cr; }
    public void setMultiplayer(boolean mp)                 { this.isMultiplayer   = mp; }

    // ── Accessors for GameScreen ──────────────────────────────────────────────
    public boolean isGodMode()   { return godMode; }
    public boolean isNoclip()    { return noclip; }
    public boolean isShowHud()   { return showHud; }
    public boolean isShowFps()   { return showFps; }

    // ── Visibility ────────────────────────────────────────────────────────────

    public boolean isVisible() { return ENABLED && visible && !isMultiplayer; }

    /**
     * Process keyboard input. Call every frame before render.
     * Returns true if the console consumed the input event (key toggle or text entry).
     */
    public boolean processInput() {
        if (!ENABLED || isMultiplayer) return false;

        // Backtick toggles visibility
        if (Gdx.input.isKeyJustPressed(Input.Keys.GRAVE)) {
            visible = !visible;
            if (!visible) inputBuffer.setLength(0);
            return true;
        }
        if (!visible) return false;

        // Enter → execute command
        if (Gdx.input.isKeyJustPressed(Input.Keys.ENTER)) {
            String cmd = inputBuffer.toString().trim();
            inputBuffer.setLength(0);
            if (!cmd.isEmpty()) execute(cmd);
            return true;
        }

        // Backspace
        if (Gdx.input.isKeyJustPressed(Input.Keys.BACKSPACE)) {
            if (inputBuffer.length() > 0)
                inputBuffer.deleteCharAt(inputBuffer.length() - 1);
            return true;
        }

        // Escape closes console
        if (Gdx.input.isKeyJustPressed(Input.Keys.ESCAPE)) {
            visible = false;
            inputBuffer.setLength(0);
            return true;
        }

        return false;
    }

    /** Append typed characters to the input buffer (call from keyTyped or equivalent). */
    public void typeChar(char c) {
        if (!ENABLED || !visible || isMultiplayer) return;
        if (c >= 32 && c != 127) inputBuffer.append(c);  // printable ASCII
    }

    // ── Rendering ─────────────────────────────────────────────────────────────

    /**
     * Render the console overlay. SpriteBatch must NOT be active when called.
     * Call at the very end of the render pass (after game world is drawn).
     */
    public void render(SpriteBatch batch, int screenWidth, int screenHeight) {
        if (!isVisible() || shapeRenderer == null) return;

        // Draw background panel
        shapeRenderer.setProjectionMatrix(batch.getProjectionMatrix());
        Gdx.gl.glEnable(com.badlogic.gdx.graphics.GL20.GL_BLEND);
        shapeRenderer.begin(ShapeRenderer.ShapeType.Filled);
        shapeRenderer.setColor(BG_COLOR);
        shapeRenderer.rect(0, screenHeight - CONSOLE_HEIGHT, screenWidth, CONSOLE_HEIGHT);
        shapeRenderer.end();

        batch.begin();
        int lineH   = 16;
        int startY  = screenHeight - 8;
        int x       = 8;

        // Input line
        font.setColor(INPUT_COLOR);
        font.draw(batch, "> " + inputBuffer + "_", x, startY);
        startY -= lineH;

        // Log lines (most recent first)
        List<String> lines = new ArrayList<>(logLines);
        Collections.reverse(lines);
        for (int i = 0; i < lines.size() && startY > screenHeight - CONSOLE_HEIGHT; i++) {
            String line = lines.get(i);
            if (line.startsWith("[ERR]"))       font.setColor(ERROR_COLOR);
            else if (line.startsWith("[INFO]"))  font.setColor(INFO_COLOR);
            else                                 font.setColor(TEXT_COLOR);
            font.draw(batch, line, x, startY);
            startY -= lineH;
        }
        batch.end();
    }

    /** Render FPS overlay (independent of console visibility). */
    public void renderFpsOverlay(SpriteBatch batch, int screenWidth, int screenHeight) {
        if (!ENABLED || !showFps || font == null) return;
        batch.begin();
        font.setColor(INFO_COLOR);
        font.draw(batch, "FPS: " + Gdx.graphics.getFramesPerSecond(), 8, screenHeight - 8);
        batch.end();
    }

    public void dispose() {
        if (!ENABLED) return;
        if (shapeRenderer != null) shapeRenderer.dispose();
        if (font != null) font.dispose();
    }

    // ── Command execution ─────────────────────────────────────────────────────

    /** Register an external command. */
    public void register(String name, String description, CommandHandler handler) {
        if (!ENABLED) return;
        handlers.put(name.toLowerCase(), handler);
        descriptions.put(name.toLowerCase(), description);
    }

    private void execute(String raw) {
        log("[CMD] " + raw);
        String[] parts = raw.trim().split("\\s+");
        String   name  = parts[0].toLowerCase();
        String[] args  = Arrays.copyOfRange(parts, 1, parts.length);
        CommandHandler h = handlers.get(name);
        if (h == null) {
            logError("Unknown command: " + name + " (type 'help' for list)");
            return;
        }
        try {
            h.execute(args, this::log);
        } catch (Exception e) {
            logError("Command error: " + e.getMessage());
        }
    }

    private void log(String msg)      { addLine(msg); }
    private void logError(String msg) { addLine("[ERR] " + msg); }
    private void logInfo(String msg)  { addLine("[INFO] " + msg); }

    private void addLine(String line) {
        logLines.addLast(line);
        while (logLines.size() > MAX_LOG_LINES) logLines.pollFirst();
    }

    // ── Built-in commands ─────────────────────────────────────────────────────

    private void registerBuiltins() {
        register("help", "List commands or describe one: help [cmd]", (args, log) -> {
            if (args.length > 0) {
                String desc = descriptions.get(args[0].toLowerCase());
                log(desc != null ? args[0] + " — " + desc : "Unknown command: " + args[0]);
            } else {
                log("Commands: " + String.join(", ", handlers.keySet()));
            }
        });

        register("clear", "Clear console log", (args, log) -> logLines.clear());

        register("reload_content", "Reload all content JSON from data/", (args, log) -> {
            try {
                ContentRegistry fresh = new ContentLoader(Paths.get("data")).loadAll();
                if (sim != null) sim.setContentRegistry(fresh);
                contentRegistry = fresh;
                log("[INFO] Content reloaded — " + fresh.enemyCount() + " enemies, "
                    + fresh.npcCount() + " npcs, " + fresh.roomTypeCount() + " room types");
            } catch (ContentLoadException e) {
                logError("Content reload failed: " + e.getMessage());
            }
        });

        register("reload_anims", "Reload animation manifest from assets/", (args, log) -> {
            if (anims == null) { logError("AnimationRegistry not set"); return; }
            com.badlogic.gdx.files.FileHandle manifest =
                Gdx.files.internal("assets/animations/manifest.json");
            com.badlogic.gdx.files.FileHandle assetRoot =
                Gdx.files.internal("assets");
            anims.loadFromManifest(manifest, assetRoot);
            log("[INFO] Animation manifest reloaded");
        });

        register("spawn", "Spawn enemy at player position: spawn <type>", (args, log) -> {
            if (args.length < 1) { logError("Usage: spawn <enemyType>"); return; }
            if (sim == null)     { logError("Simulator not set"); return; }
            SimPlayer p = sim.getPlayer(0);
            if (p == null) { logError("No local player found"); return; }
            sim.devSpawnEnemy(args[0], p.physics.x + 64f, p.physics.y);
            log("[INFO] Spawned " + args[0] + " near player");
        });

        register("teleport", "Teleport player: teleport <x> <y>", (args, log) -> {
            if (args.length < 2) { logError("Usage: teleport <x> <y>"); return; }
            if (sim == null)     { logError("Simulator not set"); return; }
            SimPlayer p = sim.getPlayer(0);
            if (p == null) { logError("No local player found"); return; }
            try {
                float x = Float.parseFloat(args[0]);
                float y = Float.parseFloat(args[1]);
                p.physics.x = x;
                p.physics.y = y;
                log("[INFO] Teleported to (" + x + ", " + y + ")");
            } catch (NumberFormatException e) {
                logError("Invalid coordinates: " + args[0] + ", " + args[1]);
            }
        });

        register("god", "Toggle god mode (invincibility)", (args, log) -> {
            godMode = !godMode;
            log("[INFO] God mode " + (godMode ? "ON" : "OFF"));
        });

        register("noclip", "Toggle noclip (no collision)", (args, log) -> {
            noclip = !noclip;
            log("[INFO] Noclip " + (noclip ? "ON" : "OFF"));
        });

        register("hud", "Toggle HUD visibility", (args, log) -> {
            showHud = !showHud;
            log("[INFO] HUD " + (showHud ? "visible" : "hidden"));
        });

        register("fps", "Toggle FPS overlay", (args, log) -> {
            showFps = !showFps;
            log("[INFO] FPS overlay " + (showFps ? "ON" : "OFF"));
        });

        register("give_xp", "Give XP to local player: give_xp <amount>", (args, log) -> {
            if (args.length < 1) { logError("Usage: give_xp <amount>"); return; }
            if (sim == null)     { logError("Simulator not set"); return; }
            SimPlayer p = sim.getPlayer(0);
            if (p == null) { logError("No local player found"); return; }
            try {
                int xp = Integer.parseInt(args[0]);
                int leveled = p.addXp(xp);
                log("[INFO] Gave " + xp + " XP (leveled up " + leveled + " time(s))");
            } catch (NumberFormatException e) {
                logError("Invalid amount: " + args[0]);
            }
        });

        register("set_health", "Set local player health: set_health <hp>", (args, log) -> {
            if (args.length < 1) { logError("Usage: set_health <hp>"); return; }
            if (sim == null)     { logError("Simulator not set"); return; }
            SimPlayer p = sim.getPlayer(0);
            if (p == null) { logError("No local player found"); return; }
            try {
                int hp = Integer.parseInt(args[0]);
                p.health  = Math.max(1, Math.min(hp, p.maxHealth));
                p.isDead  = false;
                log("[INFO] Player health set to " + p.health);
            } catch (NumberFormatException e) {
                logError("Invalid health: " + args[0]);
            }
        });

        register("quit", "Exit the game", (args, log) -> Gdx.app.exit());
    }
}
