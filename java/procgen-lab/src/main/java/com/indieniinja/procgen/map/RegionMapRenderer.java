package com.indieniinja.procgen.map;

import com.indieniinja.procgen.macro.RegionPlan;
import com.indieniinja.procgen.model.MapNode;
import com.indieniinja.procgen.model.MapNodeType;

import java.awt.*;
import java.awt.image.BufferedImage;
import java.util.LinkedHashMap;
import java.util.Map;

public final class RegionMapRenderer {

    private static final int CELL_PX = 60;
    private static final int MARGIN  = 28;

    public BufferedImage render(RegionPlan plan) {
        if (plan.locations.isEmpty()) return blankImage(280, 120);

        int minX = Integer.MAX_VALUE, minY = Integer.MAX_VALUE;
        int maxX = Integer.MIN_VALUE, maxY = Integer.MIN_VALUE;
        for (MapNode n : plan.locations) {
            minX = Math.min(minX, n.mapX); minY = Math.min(minY, n.mapY);
            maxX = Math.max(maxX, n.mapX); maxY = Math.max(maxY, n.mapY);
        }

        int w = (maxX - minX + 1) * CELL_PX + MARGIN * 2;
        int h = (maxY - minY + 2) * CELL_PX + MARGIN * 2;
        BufferedImage img = new BufferedImage(Math.max(w, 280), Math.max(h, 120),
                BufferedImage.TYPE_INT_RGB);
        Graphics2D g = setup(img);

        Map<String, MapNode> byId = new LinkedHashMap<>();
        for (MapNode n : plan.locations) byId.put(n.id, n);

        final int fMinX = minX, fMinY = minY;

        // Edges
        g.setColor(new Color(100, 100, 140));
        g.setStroke(new BasicStroke(1.5f));
        for (String[] edge : plan.edges) {
            MapNode from = byId.get(edge[0]);
            MapNode to   = byId.get(edge[1]);
            if (from == null || to == null) continue;
            g.drawLine(
                    cx(from, fMinX), cy(from, fMinY),
                    cx(to,   fMinX), cy(to,   fMinY));
        }

        // Nodes
        g.setFont(new Font(Font.SANS_SERIF, Font.PLAIN, 8));
        for (MapNode n : plan.locations) {
            int x = cx(n, fMinX);
            int y = cy(n, fMinY);
            g.setColor(nodeColor(n.type));
            g.fillOval(x - 13, y - 13, 26, 26);
            if (n.locked) {
                g.setColor(new Color(220, 50, 50));
                g.setStroke(new BasicStroke(2f));
                g.drawOval(x - 13, y - 13, 26, 26);
                g.setStroke(new BasicStroke(1.5f));
            }
            g.setColor(Color.WHITE);
            g.drawString(n.type.name().substring(0, Math.min(4, n.type.name().length())), x - 11, y + 4);
        }

        g.dispose();
        return img;
    }

    private static int cx(MapNode n, int minX) { return MARGIN + (n.mapX - minX) * CELL_PX + CELL_PX / 2; }
    private static int cy(MapNode n, int minY) { return MARGIN + (n.mapY - minY) * CELL_PX + CELL_PX / 2; }

    private static Color nodeColor(MapNodeType t) {
        return switch (t) {
            case VILLAGE -> new Color( 80, 155,  80);
            case DUNGEON -> new Color( 80, 100, 185);
            case CAVE    -> new Color(120,  90,  55);
            case GATE    -> new Color(180, 160,  55);
            case BOSS    -> new Color(200,  55,  55);
            case EXIT    -> new Color( 90, 200,  90);
            default      -> new Color(110, 110, 140);
        };
    }

    private static Graphics2D setup(BufferedImage img) {
        Graphics2D g = img.createGraphics();
        g.setColor(new Color(18, 18, 28));
        g.fillRect(0, 0, img.getWidth(), img.getHeight());
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        return g;
    }

    private static BufferedImage blankImage(int w, int h) {
        BufferedImage img = new BufferedImage(w, h, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = setup(img);
        g.dispose();
        return img;
    }
}
