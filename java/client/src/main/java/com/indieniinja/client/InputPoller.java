package com.indieniinja.client;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.Input;
import com.indieniinja.network.InputCommand;

/**
 * Polls libGDX's input state each frame and builds an InputCommand.
 *
 * Key bindings match the Python client defaults from demo_game.py.
 * Must be called from the libGDX render thread (main thread).
 */
public final class InputPoller {

    private long frameCounter = 0;

    /**
     * Sample current keyboard/gamepad state and return a packed InputCommand.
     * Called once per render frame — the result is forwarded to the server.
     */
    public InputCommand poll() {
        InputCommand cmd = new InputCommand((int) (frameCounter++ & 0x7FFF_FFFFL));

        // Movement
        cmd.up     = Gdx.input.isKeyPressed(Input.Keys.W) || Gdx.input.isKeyPressed(Input.Keys.UP);
        cmd.down   = Gdx.input.isKeyPressed(Input.Keys.S) || Gdx.input.isKeyPressed(Input.Keys.DOWN);
        cmd.left   = Gdx.input.isKeyPressed(Input.Keys.A) || Gdx.input.isKeyPressed(Input.Keys.LEFT);
        cmd.right  = Gdx.input.isKeyPressed(Input.Keys.D) || Gdx.input.isKeyPressed(Input.Keys.RIGHT);

        // Jump / action
        cmd.jump   = Gdx.input.isKeyPressed(Input.Keys.SPACE);
        cmd.dash   = Gdx.input.isKeyPressed(Input.Keys.SHIFT_LEFT) || Gdx.input.isKeyPressed(Input.Keys.SHIFT_RIGHT);
        cmd.crouch = Gdx.input.isKeyPressed(Input.Keys.CONTROL_LEFT) || Gdx.input.isKeyPressed(Input.Keys.CONTROL_RIGHT);

        // Combat (edge-triggered to match Python's isKeyJustPressed behaviour)
        cmd.attack        = Gdx.input.isKeyJustPressed(Input.Keys.J) || Gdx.input.isButtonJustPressed(Input.Buttons.LEFT);
        cmd.throwShuriken = Gdx.input.isKeyJustPressed(Input.Keys.K);
        cmd.ninjutsu      = Gdx.input.isKeyJustPressed(Input.Keys.L);
        cmd.teleport      = Gdx.input.isKeyJustPressed(Input.Keys.T);

        // Interaction
        cmd.interact   = Gdx.input.isKeyJustPressed(Input.Keys.E) || Gdx.input.isKeyJustPressed(Input.Keys.F);
        cmd.inventory  = Gdx.input.isKeyJustPressed(Input.Keys.I) || Gdx.input.isKeyJustPressed(Input.Keys.TAB);
        cmd.consumable = Gdx.input.isKeyJustPressed(Input.Keys.Q);
        cmd.slowWalk   = Gdx.input.isKeyPressed(Input.Keys.ALT_LEFT);

        // Map / overlays
        cmd.minimap         = Gdx.input.isKeyJustPressed(Input.Keys.M);
        cmd.fullmap         = Gdx.input.isKeyJustPressed(Input.Keys.N);
        cmd.controlsOverlay = Gdx.input.isKeyJustPressed(Input.Keys.F1);
        cmd.debugOverlay    = Gdx.input.isKeyJustPressed(Input.Keys.F3);

        // Camera
        cmd.cycleCamera = Gdx.input.isKeyJustPressed(Input.Keys.C);
        cmd.toggleProc  = Gdx.input.isKeyJustPressed(Input.Keys.P);

        // Menu
        cmd.menuConfirm = Gdx.input.isKeyJustPressed(Input.Keys.ENTER)    || Gdx.input.isKeyJustPressed(Input.Keys.Z);
        cmd.menuBack    = Gdx.input.isKeyJustPressed(Input.Keys.ESCAPE)    || Gdx.input.isKeyJustPressed(Input.Keys.X);

        return cmd;
    }
}
