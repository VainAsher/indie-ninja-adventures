package com.indieniinja.client.ui;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.Input;
import com.badlogic.gdx.graphics.Color;
import com.badlogic.gdx.graphics.g2d.BitmapFont;
import com.badlogic.gdx.graphics.g2d.GlyphLayout;
import com.badlogic.gdx.graphics.g2d.SpriteBatch;
import com.badlogic.gdx.graphics.glutils.ShapeRenderer;
import com.indieniinja.client.game.DialogueChoice;
import com.indieniinja.client.game.DialogueManager;
import com.indieniinja.client.game.DialogueNode;

import java.util.List;

/**
 * Renders the active dialogue as a text box at the bottom of the screen.
 *
 * Java equivalent of Python rendering/hud_renderer.py dialogue panel sections
 * and game/dialogue_system.py rendering integration in demo_game.py.
 *
 * Layout (Y-UP libGDX screen space):
 *   ┌────────────────────────────────────┐  ← BOX_Y + BOX_H
 *   │ SPEAKER NAME                       │
 *   │ Dialogue text wrapping at max      │
 *   │ width of the box...                │
 *   ├────────────────────────────────────┤
 *   │ [1] Choice one                     │
 *   │ [2] Choice two                     │
 *   │ [SPACE/E] Continue / close         │
 *   └────────────────────────────────────┘  ← BOX_Y
 *
 * All drawing is in screen coordinates (SpriteBatch projection matrix must be
 * set to an identity / screen-size projection before calling render()).
 */
public final class DialogueOverlay {

    private static final float PAD        = 12f;
    private static final float BOX_H      = 160f;
    private static final float BOX_MARGIN = 24f;   // from screen edges

    private final DialogueManager dialogueManager;
    private final BitmapFont       font;
    private final ShapeRenderer    shapes;
    private final GlyphLayout      layout = new GlyphLayout();

    // Selected choice index (keyboard navigation)
    private int selectedChoice = 0;

    public DialogueOverlay(DialogueManager dialogueManager) {
        this.dialogueManager = dialogueManager;
        this.font   = new BitmapFont();    // libGDX built-in Arial 15px
        this.shapes = new ShapeRenderer();
    }

    /**
     * Handle dialogue input.  Call each frame BEFORE rendering.
     * Returns true if the event was consumed by dialogue (caller should not process it).
     */
    public boolean handleInput() {
        if (!dialogueManager.isActive()) return false;

        DialogueNode node = dialogueManager.currentNode();
        if (node == null) return false;

        List<DialogueChoice> choices = dialogueManager.availableChoices();

        if (choices.isEmpty()) {
            // Auto-advance node: SPACE / E / ENTER
            if (Gdx.input.isKeyJustPressed(Input.Keys.SPACE)
                    || Gdx.input.isKeyJustPressed(Input.Keys.E)
                    || Gdx.input.isKeyJustPressed(Input.Keys.ENTER)) {
                dialogueManager.advance();
                selectedChoice = 0;
                return true;
            }
        } else {
            // Navigate choices
            if (Gdx.input.isKeyJustPressed(Input.Keys.UP)) {
                selectedChoice = Math.max(0, selectedChoice - 1);
                return true;
            }
            if (Gdx.input.isKeyJustPressed(Input.Keys.DOWN)) {
                selectedChoice = Math.min(choices.size() - 1, selectedChoice + 1);
                return true;
            }
            // Confirm selection
            if (Gdx.input.isKeyJustPressed(Input.Keys.ENTER)
                    || Gdx.input.isKeyJustPressed(Input.Keys.E)) {
                dialogueManager.selectChoice(selectedChoice);
                selectedChoice = 0;
                return true;
            }
            // Number keys 1-9 for quick selection
            for (int i = 0; i < Math.min(choices.size(), 9); i++) {
                if (Gdx.input.isKeyJustPressed(Input.Keys.NUM_1 + i)) {
                    dialogueManager.selectChoice(i);
                    selectedChoice = 0;
                    return true;
                }
            }
        }

        // ESC / Q always closes dialogue
        if (Gdx.input.isKeyJustPressed(Input.Keys.ESCAPE)
                || Gdx.input.isKeyJustPressed(Input.Keys.Q)) {
            dialogueManager.endDialogue();
            selectedChoice = 0;
            return true;
        }

        return true;  // consume all input while dialogue is open
    }

    /**
     * Render the dialogue box over the game.
     *
     * @param batch SpriteBatch configured with screen-space projection (NOT camera projection).
     *              Caller must begin/end the batch around this call.
     */
    public void render(SpriteBatch batch) {
        if (!dialogueManager.isActive()) return;

        DialogueNode node = dialogueManager.currentNode();
        if (node == null) return;

        float sw = Gdx.graphics.getWidth();

        float boxX = BOX_MARGIN;
        float boxY = BOX_MARGIN;
        float boxW = sw - BOX_MARGIN * 2f;

        List<DialogueChoice> choices = dialogueManager.availableChoices();
        float extraH = choices.isEmpty() ? 20f : (choices.size() * 18f + 20f);
        float totalH = BOX_H + extraH;

        // ── Background ────────────────────────────────────────────────────────
        batch.end();
        shapes.setProjectionMatrix(batch.getProjectionMatrix());
        shapes.begin(ShapeRenderer.ShapeType.Filled);
        shapes.setColor(0.05f, 0.05f, 0.15f, 0.88f);
        shapes.rect(boxX, boxY, boxW, totalH);
        shapes.end();
        shapes.begin(ShapeRenderer.ShapeType.Line);
        shapes.setColor(0.4f, 0.6f, 1f, 1f);
        shapes.rect(boxX, boxY, boxW, totalH);
        shapes.end();
        batch.begin();

        float textX = boxX + PAD;
        float textY = boxY + totalH - PAD;

        // ── Speaker name ──────────────────────────────────────────────────────
        if (node.speaker != null && !node.speaker.isBlank()) {
            font.setColor(0.6f, 0.85f, 1f, 1f);
            font.draw(batch, node.speaker, textX, textY);
            textY -= 18f;
        }

        // ── Dialogue text (word-wrapped) ──────────────────────────────────────
        font.setColor(Color.WHITE);
        layout.setText(font, node.text, Color.WHITE, boxW - PAD * 2f,
                        com.badlogic.gdx.utils.Align.left, true);
        font.draw(batch, layout, textX, textY);
        textY -= layout.height + 10f;

        // ── Separator line ────────────────────────────────────────────────────
        batch.end();
        shapes.begin(ShapeRenderer.ShapeType.Line);
        shapes.setColor(0.3f, 0.4f, 0.8f, 0.6f);
        shapes.line(boxX + PAD, textY + 4f, boxX + boxW - PAD, textY + 4f);
        shapes.end();
        batch.begin();
        textY -= 8f;

        // ── Choices ───────────────────────────────────────────────────────────
        if (!choices.isEmpty()) {
            for (int i = 0; i < choices.size(); i++) {
                boolean selected = (i == selectedChoice);
                font.setColor(selected ? Color.YELLOW : new Color(0.8f, 0.8f, 0.8f, 1f));
                String label = "[" + (i + 1) + "] " + choices.get(i).choiceText;
                font.draw(batch, label, textX + (selected ? 6f : 0f), textY);
                textY -= 18f;
            }
        } else {
            font.setColor(0.5f, 0.5f, 0.5f, 1f);
            font.draw(batch, "[E / SPACE] Continue", textX, textY);
        }

        font.setColor(Color.WHITE);
    }

    public void dispose() {
        font.dispose();
        shapes.dispose();
    }
}
