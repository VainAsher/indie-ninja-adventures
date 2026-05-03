package com.indieniinja.procgen.map;

import com.indieniinja.procgen.macro.RegionPlan;
import com.indieniinja.procgen.macro.WorldPlan;

import java.awt.*;
import java.awt.image.BufferedImage;

public final class WorldMapRenderer {

    private static final int CELL_PX = 52;
    private static final int MARGIN  = 24;

    public BufferedImage render(WorldPlan plan) {
        if (plan.regions.isEmpty()) return blankImage(200, 100);

        int maxX = 0, maxY = 0;
        for (RegionPlan r : plan.regions) {
            maxX = Math.max(maxX, r.node.mapX);
            maxY = Math.max(maxY, r.node.mapY);
        }

        int w = (maxX + 1) * CELL_PX + MARGIN * 2;
        int h = (maxY + 1) * CELL_PX + MARGIN * 2;
        BufferedImage img = new BufferedImage(Math.max(w, 200), Math.max(h, 100),
                BufferedImage.TYPE_INT_RGB);
        Graphics2D g = setup(img);

        for (RegionPlan r : plan.regions) {
            int cx = MARGIN + r.node.mapX * CELL_PX + CELL_PX / 2;
            int cy = MARGIN + r.node.mapY * CELL_PX + CELL_PX / 2;
            g.setColor(new Color(70, 120, 200));
            g.fillOval(cx - 15, cy - 15, 30, 30);
            g.setColor(Color.WHITE);
            g.setFont(new Font(Font.SANS_SERIF, Font.BOLD, 8));
            g.drawString(r.intent.id, cx - 12, cy + 4);
        }

        g.dispose();
        return img;
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
