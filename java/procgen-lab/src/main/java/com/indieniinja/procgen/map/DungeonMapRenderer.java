package com.indieniinja.procgen.map;

import com.indieniinja.procgen.dungeon.DungeonPlan;
import com.indieniinja.procgen.dungeon.RoomNode;
import com.indieniinja.procgen.model.RoomType;

import java.awt.*;
import java.awt.image.BufferedImage;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public final class DungeonMapRenderer {

    private static final int CELL_PX = 56;
    private static final int MARGIN  = 24;
    private static final int NODE_W  = 38;
    private static final int NODE_H  = 22;

    public BufferedImage render(DungeonPlan plan, RoomNode selected) {
        List<RoomNode> nodes = plan.roomGraph.nodes();
        if (nodes.isEmpty()) return blankImage(320, 120);

        int minX = nodes.stream().mapToInt(n -> n.graphX).min().orElse(0);
        int minY = nodes.stream().mapToInt(n -> n.graphY).min().orElse(0);
        int maxX = nodes.stream().mapToInt(n -> n.graphX).max().orElse(0);
        int maxY = nodes.stream().mapToInt(n -> n.graphY).max().orElse(0);

        int w = (maxX - minX + 1) * CELL_PX + MARGIN * 2;
        int h = (maxY - minY + 1) * CELL_PX + MARGIN * 2;
        BufferedImage img = new BufferedImage(Math.max(w, 320), Math.max(h, 120),
                BufferedImage.TYPE_INT_RGB);
        Graphics2D g = setup(img);

        // Edges (deduplicated)
        Set<String> drawn = new HashSet<>();
        g.setColor(new Color(100, 105, 140));
        g.setStroke(new BasicStroke(1.5f));
        for (RoomNode n : nodes) {
            for (RoomNode nb : n.neighbors) {
                String key = n.id.compareTo(nb.id) < 0
                        ? n.id + ":" + nb.id : nb.id + ":" + n.id;
                if (!drawn.add(key)) continue;
                g.drawLine(cx(n, minX), cy(n, minY), cx(nb, minX), cy(nb, minY));
            }
        }

        // Nodes
        g.setFont(new Font(Font.MONOSPACED, Font.PLAIN, 8));
        for (RoomNode n : nodes) {
            int x = cx(n, minX) - NODE_W / 2;
            int y = cy(n, minY) - NODE_H / 2;
            boolean isSel = n == selected;
            g.setColor(isSel ? new Color(255, 220, 50) : roomColor(n.intent.type));
            g.fillRoundRect(x, y, NODE_W, NODE_H, 6, 6);
            g.setColor(isSel ? Color.BLACK : Color.WHITE);
            String label = n.intent.type.name();
            label = label.substring(0, Math.min(5, label.length()));
            g.drawString(label, x + 2, y + NODE_H - 5);
        }

        g.dispose();
        return img;
    }

    private static int cx(RoomNode n, int minX) { return MARGIN + (n.graphX - minX) * CELL_PX + CELL_PX / 2; }
    private static int cy(RoomNode n, int minY) { return MARGIN + (n.graphY - minY) * CELL_PX + CELL_PX / 2; }

    private static Color roomColor(RoomType t) {
        return switch (t) {
            case START     -> new Color( 55, 180,  55);
            case TRAVERSAL -> new Color( 75, 110, 195);
            case PUZZLE    -> new Color(180, 120,  55);
            case COMBAT    -> new Color(200,  75,  75);
            case SAVE      -> new Color( 55, 195, 195);
            case SHORTCUT  -> new Color(155, 155,  55);
            case TREASURE  -> new Color(200, 175,  40);
            case BOSS      -> new Color(195,  40, 195);
            case EXIT      -> new Color( 90, 195,  90);
            default        -> new Color(110, 110, 140);
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
