package com.indieniinja.procgen.ui;

import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.model.ZoneCell;

import javax.swing.*;
import java.awt.*;

public final class InspectorPanel extends JPanel {

    private final JTextArea    textArea;
    private final UiController controller;
    private final SelectionModel selection;

    public InspectorPanel(UiController controller, SelectionModel selection) {
        this.controller = controller;
        this.selection  = selection;
        setLayout(new BorderLayout());
        setPreferredSize(new Dimension(205, 0));

        add(new JLabel("Inspector", SwingConstants.CENTER), BorderLayout.NORTH);
        textArea = new JTextArea("Click a zone to inspect.");
        textArea.setEditable(false);
        textArea.setFont(new Font(Font.MONOSPACED, Font.PLAIN, 11));
        textArea.setBackground(new Color(18, 18, 26));
        textArea.setForeground(new Color(180, 200, 180));
        add(new JScrollPane(textArea), BorderLayout.CENTER);

        controller.addRoomListener(this::refresh);
        selection.addChangeListener(this::refresh);
    }

    private void refresh() {
        if (!selection.hasSelection() || controller.getCurrentRoom() == null) {
            textArea.setText("Click a zone to inspect.");
            return;
        }
        int zx = selection.getZoneX();
        int zy = selection.getZoneY();
        if (zx < 0 || zx >= GenConfig.ZONE_W || zy < 0 || zy >= GenConfig.ZONE_H) {
            textArea.setText("Out of bounds.");
            return;
        }
        ZoneCell cell = controller.getCurrentRoom().zones[zx][zy];
        StringBuilder sb = new StringBuilder();
        sb.append(String.format("Zone  (%d, %d)%n", zx, zy));
        sb.append(String.format("Tile  (%d, %d)%n", zx * GenConfig.ZONE_SIZE, zy * GenConfig.ZONE_SIZE));
        sb.append('\n');
        sb.append(String.format("Base:     %s%n", cell.base));
        sb.append(String.format("Surface:  %s%n", cell.surface));
        sb.append(String.format("Variant:  %s%n", cell.variant));
        sb.append(String.format("Critical: %s%n", cell.criticalPath ? "yes" : "no"));
        textArea.setText(sb.toString());
        textArea.setCaretPosition(0);
    }
}
