package com.indieniinja.procgen.ui;

import javax.swing.*;
import java.awt.*;

public final class ToolBarPanel extends JPanel {

    private final JTextField  seedField;
    private final UiController controller;

    public ToolBarPanel(UiController controller) {
        this.controller = controller;
        setLayout(new FlowLayout(FlowLayout.LEFT, 8, 4));

        add(new JLabel("Seed:"));
        seedField = new JTextField(String.valueOf(controller.getCurrentSeed()), 18);
        add(seedField);

        JButton regenerate = new JButton("Regenerate");
        regenerate.addActionListener(e -> {
            try {
                controller.regenerate(Long.parseLong(seedField.getText().trim()));
            } catch (NumberFormatException ex) {
                JOptionPane.showMessageDialog(this, "Invalid seed — enter a long integer.");
            }
        });
        add(regenerate);

        JButton newSeed = new JButton("New Seed");
        newSeed.addActionListener(e -> {
            controller.newSeed();
            seedField.setText(String.valueOf(controller.getCurrentSeed()));
        });
        add(newSeed);

        add(new JLabel("View:"));
        JComboBox<ViewMode> viewCombo = new JComboBox<>(ViewMode.values());
        viewCombo.setSelectedItem(ViewMode.TILES);
        viewCombo.addActionListener(e -> controller.setViewMode((ViewMode) viewCombo.getSelectedItem()));
        add(viewCombo);

        controller.addChangeListener(() ->
                seedField.setText(String.valueOf(controller.getCurrentSeed())));
    }
}
