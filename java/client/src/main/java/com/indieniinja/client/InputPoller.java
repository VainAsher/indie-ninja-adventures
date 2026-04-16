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

    private final KeyBindings keys;
    private long frameCounter = 0;

    public InputPoller(KeyBindings keys) {
        this.keys = keys != null ? keys : KeyBindings.defaults();
    }

    /** One-line controls signature for playtest evidence logging. */
    public String controlPresetSummary() {
        return keys.controlPresetSummary();
    }

    /**
     * Sample current keyboard state and return a packed InputCommand.
     * Called once per render frame.
     */
    public InputCommand poll() {
        InputCommand cmd = new InputCommand((int) (frameCounter++ & 0x7FFF_FFFFL));

        // Movement
        cmd.up = keys.isHeld("up");
        cmd.down = keys.isHeld("down");
        cmd.left = keys.isHeld("left");
        cmd.right = keys.isHeld("right");

        // Core movement profile
        cmd.jump = keys.isHeld("jump");
        cmd.dash = keys.isHeld("dash");
        cmd.crouch = keys.isHeld("crouch") || cmd.down;
        cmd.slowWalk = keys.isHeld("slow_walk");

        // Combat and arts
        cmd.attack = keys.isHeld("attack")
            || Gdx.input.isButtonPressed(Input.Buttons.LEFT);
        cmd.block = keys.isHeld("block");
        cmd.throwShuriken = keys.isHeld("throw");
        cmd.teleport = keys.isHeld("teleport");
        cmd.ninjutsu = keys.isHeld("ninjutsu");
        cmd.stanceSwitch = keys.isJustPressed("stance_switch");
        cmd.selectWeapon1 = keys.isJustPressed("select_weapon_1");
        cmd.selectWeapon2 = keys.isJustPressed("select_weapon_2");

        // Interaction/meta
        cmd.interact = keys.isJustPressed("interact");
        cmd.inventory = keys.isJustPressed("inventory");
        cmd.consumable = keys.isJustPressed("consumable");

        // Map and overlays
        cmd.minimap = keys.isJustPressed("minimap");
        cmd.fullmap = keys.isHeld("fullmap");
        cmd.controlsOverlay = keys.isJustPressed("controls_overlay");
        cmd.debugOverlay = keys.isJustPressed("debug_overlay");

        // Debug camera/dev toggles
        cmd.cycleCamera = keys.isJustPressed("cycle_camera");
        cmd.toggleProc = keys.isJustPressed("toggle_proc");

        // Menu
        cmd.menuConfirm = keys.isJustPressed("menu_confirm");
        cmd.menuBack = keys.isJustPressed("menu_back");

        return cmd;
    }
}
