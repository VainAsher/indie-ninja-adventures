package com.indieniinja.procgen.ui;

import com.indieniinja.procgen.room.GeneratedRoom;
import com.indieniinja.procgen.room.RoomGenerationReport;

import javax.swing.*;
import java.awt.*;

public final class LogPanel extends JPanel {

    private final JTextArea textArea;

    public LogPanel() {
        setLayout(new BorderLayout());
        setPreferredSize(new Dimension(0, 140));
        textArea = new JTextArea();
        textArea.setEditable(false);
        textArea.setFont(new Font(Font.MONOSPACED, Font.PLAIN, 11));
        textArea.setBackground(new Color(18, 18, 26));
        textArea.setForeground(new Color(170, 195, 170));
        add(new JScrollPane(textArea), BorderLayout.CENTER);
    }

    public void setRoom(GeneratedRoom room) {
        if (room == null) { textArea.setText(""); return; }
        RoomGenerationReport report = room.report;
        StringBuilder sb = new StringBuilder();
        sb.append(String.format("Seed: %d  |  %s / %s  |  Valid: %b%n",
                report.seed, room.intent.type, room.intent.biome,
                room.isValid()));
        for (String line : report.passLog) {
            sb.append("  ").append(line).append('\n');
        }
        if (!report.errors.isEmpty()) {
            sb.append("ERRORS:\n");
            for (String e : report.errors) sb.append("  ! ").append(e).append('\n');
        }
        textArea.setText(sb.toString());
        textArea.setCaretPosition(0);
    }
}
