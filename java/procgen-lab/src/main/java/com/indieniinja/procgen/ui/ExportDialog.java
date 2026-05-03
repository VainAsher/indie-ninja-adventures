package com.indieniinja.procgen.ui;

import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.room.GeneratedRoom;

import javax.swing.*;
import java.awt.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;

/**
 * Modal dialog offering one-click export of the current room to Tiled JSON or LDtk format.
 * Produces minimal but spec-valid output; intended for dev tooling, not production pipeline.
 */
public final class ExportDialog extends JDialog {

    private final GeneratedRoom room;

    public ExportDialog(Frame owner, GeneratedRoom room) {
        super(owner, "Export Room", true);
        this.room = room;

        setLayout(new BorderLayout(8, 8));
        getRootPane().setBorder(BorderFactory.createEmptyBorder(12, 12, 12, 12));

        JLabel info = new JLabel(String.format(
                "Room: %s / %s   Seed: %d",
                room.intent.type, room.intent.biome, room.report.seed));
        add(info, BorderLayout.NORTH);

        JPanel buttons = new JPanel(new FlowLayout(FlowLayout.CENTER, 10, 0));

        JButton tiledBtn = new JButton("Export Tiled JSON…");
        tiledBtn.addActionListener(e -> exportAs("tiled_room.json", this::buildTiledJson));
        buttons.add(tiledBtn);

        JButton ldtkBtn = new JButton("Export LDtk JSON…");
        ldtkBtn.addActionListener(e -> exportAs("ldtk_room.json", this::buildLdtkJson));
        buttons.add(ldtkBtn);

        JButton closeBtn = new JButton("Close");
        closeBtn.addActionListener(e -> dispose());
        buttons.add(closeBtn);

        add(buttons, BorderLayout.CENTER);
        pack();
        setLocationRelativeTo(owner);
    }

    private void exportAs(String defaultName, java.util.function.Supplier<String> builder) {
        JFileChooser chooser = new JFileChooser();
        chooser.setSelectedFile(new File(defaultName));
        if (chooser.showSaveDialog(this) != JFileChooser.APPROVE_OPTION) return;
        File file = chooser.getSelectedFile();
        try {
            Files.writeString(file.toPath(), builder.get(), StandardCharsets.UTF_8);
            JOptionPane.showMessageDialog(this, "Saved: " + file.getName());
        } catch (IOException ex) {
            JOptionPane.showMessageDialog(this, "Error: " + ex.getMessage(),
                    "Export Failed", JOptionPane.ERROR_MESSAGE);
        }
    }

    // -------------------------------------------------------------------------
    // Tiled JSON (spec: https://doc.mapeditor.org/en/stable/reference/json-map-format/)

    private String buildTiledJson() {
        int[] data = buildRowMajorData();
        StringBuilder sb = new StringBuilder();
        sb.append("{\n");
        sb.append("  \"version\": \"1.10\",\n");
        sb.append("  \"tiledversion\": \"1.10.0\",\n");
        sb.append(String.format("  \"width\": %d,\n", GenConfig.ROOM_W));
        sb.append(String.format("  \"height\": %d,\n", GenConfig.ROOM_H));
        sb.append(String.format("  \"tilewidth\": %d,\n", GenConfig.ZONE_SIZE));
        sb.append(String.format("  \"tileheight\": %d,\n", GenConfig.ZONE_SIZE));
        sb.append("  \"infinite\": false,\n");
        sb.append("  \"orientation\": \"orthogonal\",\n");
        sb.append("  \"renderorder\": \"right-down\",\n");
        sb.append("  \"nextlayerid\": 2,\n");
        sb.append("  \"nextobjectid\": 1,\n");
        sb.append("  \"tilesets\": [{\n");
        sb.append("    \"firstgid\": 1,\n");
        sb.append("    \"name\": \"shadow-ascent\",\n");
        sb.append(String.format("    \"tilewidth\": %d,\n", GenConfig.ZONE_SIZE));
        sb.append(String.format("    \"tileheight\": %d,\n", GenConfig.ZONE_SIZE));
        sb.append("    \"tilecount\": 13,\n");
        sb.append("    \"columns\": 13,\n");
        sb.append("    \"image\": \"shadow-ascent.png\",\n");
        sb.append("    \"imagewidth\": 104,\n");
        sb.append("    \"imageheight\": 8\n");
        sb.append("  }],\n");
        sb.append("  \"layers\": [{\n");
        sb.append("    \"type\": \"tilelayer\",\n");
        sb.append("    \"id\": 1,\n");
        sb.append("    \"name\": \"tiles\",\n");
        sb.append("    \"visible\": true,\n");
        sb.append("    \"opacity\": 1,\n");
        sb.append("    \"x\": 0, \"y\": 0,\n");
        sb.append(String.format("    \"width\": %d,\n", GenConfig.ROOM_W));
        sb.append(String.format("    \"height\": %d,\n", GenConfig.ROOM_H));
        sb.append("    \"data\": ").append(intArrayJson(data)).append("\n");
        sb.append("  }]\n");
        sb.append("}\n");
        return sb.toString();
    }

    // -------------------------------------------------------------------------
    // LDtk JSON (spec: https://ldtk.io/files/JSON_SCHEMA.json)

    private String buildLdtkJson() {
        int[] data = buildRowMajorData();
        int pxW = GenConfig.ROOM_W * GenConfig.ZONE_SIZE;
        int pxH = GenConfig.ROOM_H * GenConfig.ZONE_SIZE;
        StringBuilder sb = new StringBuilder();
        sb.append("{\n");
        sb.append("  \"jsonVersion\": \"1.5.3\",\n");
        sb.append("  \"worlds\": [{\n");
        sb.append("    \"identifier\": \"World\",\n");
        sb.append(String.format("    \"defaultLevelWidth\": %d,\n", pxW));
        sb.append(String.format("    \"defaultLevelHeight\": %d,\n", pxH));
        sb.append("    \"levels\": [{\n");
        sb.append("      \"identifier\": \"Room\",\n");
        sb.append("      \"uid\": 1,\n");
        sb.append("      \"worldX\": 0, \"worldY\": 0,\n");
        sb.append(String.format("      \"pxWid\": %d,\n", pxW));
        sb.append(String.format("      \"pxHei\": %d,\n", pxH));
        sb.append("      \"layerInstances\": [{\n");
        sb.append("        \"__type\": \"IntGrid\",\n");
        sb.append("        \"__identifier\": \"Tiles\",\n");
        sb.append(String.format("        \"__cWid\": %d,\n", GenConfig.ROOM_W));
        sb.append(String.format("        \"__cHei\": %d,\n", GenConfig.ROOM_H));
        sb.append(String.format("        \"gridSize\": %d,\n", GenConfig.ZONE_SIZE));
        sb.append("        \"intGridCsv\": ").append(intArrayJson(data)).append("\n");
        sb.append("      }]\n");
        sb.append("    }]\n");
        sb.append("  }]\n");
        sb.append("}\n");
        return sb.toString();
    }

    // -------------------------------------------------------------------------
    // Shared helpers

    /** Row-major flat tile array (y outer, x inner). AIR=0 maps to 0 (empty in both formats). */
    private int[] buildRowMajorData() {
        byte[][] tiles = room.tiles;
        int[] data = new int[GenConfig.ROOM_W * GenConfig.ROOM_H];
        for (int y = 0; y < GenConfig.ROOM_H; y++) {
            for (int x = 0; x < GenConfig.ROOM_W; x++) {
                data[y * GenConfig.ROOM_W + x] = tiles[x][y] & 0xFF;
            }
        }
        return data;
    }

    private static String intArrayJson(int[] data) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < data.length; i++) {
            if (i > 0) sb.append(',');
            sb.append(data[i]);
        }
        sb.append(']');
        return sb.toString();
    }
}
