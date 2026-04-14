package com.indieniinja.client;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.Input;
import com.indieniinja.network.InputCommand;

/**
 * Polls libGDX input each frame and builds an InputCommand.
 *
 * Key bindings follow GDD 10.3.13 (Precision Keyboard Preset).
 */
public final class InputPoller {

    private long frameCounter = 0;

    /**
     * Sample current keyboard state and return a packed InputCommand.
     * Called once per render frame.
     */
    public InputCommand poll() {
        InputCommand cmd = new InputCommand((int) (frameCounter++ & 0x7FFF_FFFFL));

        // Movement (GDD: Arrow keys)
        cmd.up = Gdx.input.isKeyPressed(Input.Keys.UP);
        cmd.down = Gdx.input.isKeyPressed(Input.Keys.DOWN);
        cmd.left = Gdx.input.isKeyPressed(Input.Keys.LEFT);
        cmd.right = Gdx.input.isKeyPressed(Input.Keys.RIGHT);

        // Core movement profile (GDD: Z jump, C dash, Shift run modifier)
        cmd.jump = Gdx.input.isKeyPressed(Input.Keys.Z);
        cmd.dash = Gdx.input.isKeyPressed(Input.Keys.C);
        cmd.crouch = cmd.down;
        cmd.slowWalk = Gdx.input.isKeyPressed(Input.Keys.SHIFT_LEFT)
            || Gdx.input.isKeyPressed(Input.Keys.SHIFT_RIGHT);

        // Combat and arts (GDD: X/A/S/D/F/R)
        cmd.attack = Gdx.input.isKeyPressed(Input.Keys.X);
        cmd.throwShuriken = Gdx.input.isKeyPressed(Input.Keys.F);
        cmd.teleport = Gdx.input.isKeyPressed(Input.Keys.D);  // Traversal Art
        cmd.ninjutsu = Gdx.input.isKeyPressed(Input.Keys.R);  // Echo Art
        cmd.stanceSwitch = Gdx.input.isKeyJustPressed(Input.Keys.A);
        // NOTE: Guard/Parry (S) is reserved in GDD, but there is no dedicated
        // player guard input field in the current network command schema yet.

        // Interaction/meta
        cmd.interact = Gdx.input.isKeyJustPressed(Input.Keys.E);
        cmd.inventory = Gdx.input.isKeyJustPressed(Input.Keys.I);
        cmd.consumable = Gdx.input.isKeyJustPressed(Input.Keys.Q);

        // Map and overlays
        cmd.minimap = Gdx.input.isKeyJustPressed(Input.Keys.TAB);
        cmd.fullmap = Gdx.input.isKeyPressed(Input.Keys.TAB);
        cmd.controlsOverlay = Gdx.input.isKeyJustPressed(Input.Keys.F1);
        cmd.debugOverlay = Gdx.input.isKeyJustPressed(Input.Keys.F3);

        // Debug camera/dev toggles
        cmd.cycleCamera = Gdx.input.isKeyJustPressed(Input.Keys.V);
        cmd.toggleProc = Gdx.input.isKeyJustPressed(Input.Keys.P);

        // Menu
        cmd.menuConfirm = Gdx.input.isKeyJustPressed(Input.Keys.ENTER);
        cmd.menuBack = Gdx.input.isKeyJustPressed(Input.Keys.ESCAPE);

        return cmd;
    }
}
