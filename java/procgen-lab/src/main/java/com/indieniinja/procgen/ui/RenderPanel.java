package com.indieniinja.procgen.ui;

import com.indieniinja.procgen.model.FillVariant;
import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.model.Tile;
import com.indieniinja.procgen.model.ZoneBase;
import com.indieniinja.procgen.model.ZoneCell;
import com.indieniinja.procgen.model.ZoneSurface;
import com.indieniinja.procgen.room.GeneratedRoom;
import com.indieniinja.procgen.validation.ValidationResult;

import javax.swing.*;
import java.awt.*;
import java.awt.event.*;

public final class RenderPanel extends JPanel {

    private static final int TILE_PX = 4;
    private static final int ZONE_PX = GenConfig.ZONE_SIZE * TILE_PX; // 32px per zone

    private static final Color[] TILE_PALETTE    = buildTilePalette();
    private static final Color[] ZONE_PALETTE    = buildZonePalette();
    private static final Color[] SURFACE_PALETTE = buildSurfacePalette();
    private static final Color[] VARIANT_PALETTE = buildVariantPalette();

    private final SelectionModel selection;
    private GeneratedRoom room;
    private ViewMode viewMode = ViewMode.TILES;

    public RenderPanel(SelectionModel selection) {
        this.selection = selection;
        setPreferredSize(new Dimension(GenConfig.ROOM_W * TILE_PX, GenConfig.ROOM_H * TILE_PX));
        setBackground(Color.BLACK);
        addMouseListener(new MouseAdapter() {
            @Override
            public void mouseClicked(MouseEvent e) {
                int zx = e.getX() / ZONE_PX;
                int zy = e.getY() / ZONE_PX;
                if (zx >= 0 && zx < GenConfig.ZONE_W && zy >= 0 && zy < GenConfig.ZONE_H) {
                    selection.select(zx, zy);
                    repaint();
                }
            }
        });
        selection.addChangeListener(this::repaint);
    }

    public void setRoom(GeneratedRoom room) {
        this.room = room;
        repaint();
    }

    public void setViewMode(ViewMode mode) {
        this.viewMode = mode;
        repaint();
    }

    @Override
    protected void paintComponent(Graphics rawG) {
        super.paintComponent(rawG);
        Graphics2D g = (Graphics2D) rawG;
        if (room == null) {
            g.setColor(new Color(30, 30, 38));
            g.fillRect(0, 0, getWidth(), getHeight());
            return;
        }
        switch (viewMode) {
            case TILES      -> paintTiles(g);
            case ZONES      -> paintZones(g);
            case SURFACE    -> paintSurface(g);
            case VARIANT    -> paintVariant(g);
            case VALIDATION -> paintValidation(g);
        }
        paintSelectionOverlay(g);
    }

    // -------------------------------------------------------------------------
    // View mode renderers

    private void paintTiles(Graphics2D g) {
        byte[][] tiles = room.tiles;
        for (int x = 0; x < GenConfig.ROOM_W; x++) {
            for (int y = 0; y < GenConfig.ROOM_H; y++) {
                int id = tiles[x][y] & 0xFF;
                g.setColor(id < TILE_PALETTE.length ? TILE_PALETTE[id] : Color.MAGENTA);
                g.fillRect(x * TILE_PX, y * TILE_PX, TILE_PX, TILE_PX);
            }
        }
    }

    private void paintZones(Graphics2D g) {
        ZoneCell[][] zones = room.zones;
        for (int zx = 0; zx < GenConfig.ZONE_W; zx++) {
            for (int zy = 0; zy < GenConfig.ZONE_H; zy++) {
                int idx = zones[zx][zy].base.ordinal();
                g.setColor(idx < ZONE_PALETTE.length ? ZONE_PALETTE[idx] : Color.MAGENTA);
                g.fillRect(zx * ZONE_PX, zy * ZONE_PX, ZONE_PX, ZONE_PX);
                if (zones[zx][zy].criticalPath) {
                    g.setColor(new Color(255, 255, 0, 80));
                    g.fillRect(zx * ZONE_PX, zy * ZONE_PX, ZONE_PX, ZONE_PX);
                }
            }
        }
        paintZoneGrid(g);
    }

    private void paintSurface(Graphics2D g) {
        ZoneCell[][] zones = room.zones;
        for (int zx = 0; zx < GenConfig.ZONE_W; zx++) {
            for (int zy = 0; zy < GenConfig.ZONE_H; zy++) {
                int idx = zones[zx][zy].surface.ordinal();
                g.setColor(idx < SURFACE_PALETTE.length ? SURFACE_PALETTE[idx] : Color.MAGENTA);
                g.fillRect(zx * ZONE_PX, zy * ZONE_PX, ZONE_PX, ZONE_PX);
            }
        }
        paintZoneGrid(g);
    }

    private void paintVariant(Graphics2D g) {
        ZoneCell[][] zones = room.zones;
        for (int zx = 0; zx < GenConfig.ZONE_W; zx++) {
            for (int zy = 0; zy < GenConfig.ZONE_H; zy++) {
                int idx = zones[zx][zy].variant.ordinal();
                g.setColor(idx < VARIANT_PALETTE.length ? VARIANT_PALETTE[idx] : Color.MAGENTA);
                g.fillRect(zx * ZONE_PX, zy * ZONE_PX, ZONE_PX, ZONE_PX);
            }
        }
        paintZoneGrid(g);
    }

    private void paintValidation(Graphics2D g) {
        paintTiles(g);
        ValidationResult vr = room.report.validation;
        if (vr == null || vr.reachable == null) return;
        g.setColor(new Color(200, 0, 0, 130));
        byte[][] tiles = room.tiles;
        for (int x = 0; x < GenConfig.ROOM_W; x++) {
            for (int y = 0; y < GenConfig.ROOM_H; y++) {
                if (!vr.reachable[x][y] && isTraversable(tiles[x][y])) {
                    g.fillRect(x * TILE_PX, y * TILE_PX, TILE_PX, TILE_PX);
                }
            }
        }
    }

    private void paintZoneGrid(Graphics2D g) {
        g.setColor(new Color(10, 10, 10, 90));
        for (int zx = 0; zx <= GenConfig.ZONE_W; zx++)
            g.drawLine(zx * ZONE_PX, 0, zx * ZONE_PX, GenConfig.ROOM_H * TILE_PX);
        for (int zy = 0; zy <= GenConfig.ZONE_H; zy++)
            g.drawLine(0, zy * ZONE_PX, GenConfig.ROOM_W * TILE_PX, zy * ZONE_PX);
    }

    private void paintSelectionOverlay(Graphics2D g) {
        if (!selection.hasSelection()) return;
        int zx = selection.getZoneX();
        int zy = selection.getZoneY();
        g.setColor(new Color(255, 255, 100, 90));
        g.fillRect(zx * ZONE_PX, zy * ZONE_PX, ZONE_PX, ZONE_PX);
        g.setColor(new Color(255, 255, 0));
        g.drawRect(zx * ZONE_PX, zy * ZONE_PX, ZONE_PX - 1, ZONE_PX - 1);
    }

    // -------------------------------------------------------------------------
    // Helpers

    private static boolean isTraversable(byte t) {
        return t == Tile.AIR      || t == Tile.DOOR      || t == Tile.PLATFORM
            || t == Tile.PICKUP   || t == Tile.SAVE_POINT || t == Tile.ENEMY_SPAWN
            || t == Tile.BOSS_SPAWN || t == Tile.CLIMBABLE;
    }

    // -------------------------------------------------------------------------
    // Palettes

    private static Color[] buildTilePalette() {
        Color[] c = new Color[13];
        c[Tile.AIR]         = new Color( 20,  22,  32);
        c[Tile.SOLID]       = new Color( 90,  95, 110);
        c[Tile.PLATFORM]    = new Color(130,  85,  40);
        c[Tile.WATER]       = new Color( 30, 100, 200);
        c[Tile.LAVA]        = new Color(220,  80,  20);
        c[Tile.SPIKES]      = new Color(210, 195,  50);
        c[Tile.DOOR]        = new Color( 60, 200,  90);
        c[Tile.LOCKED_DOOR] = new Color(200,  50,  50);
        c[Tile.CLIMBABLE]   = new Color( 50, 175, 175);
        c[Tile.PICKUP]      = new Color(255, 215,   0);
        c[Tile.ENEMY_SPAWN] = new Color(255, 120,   0);
        c[Tile.SAVE_POINT]  = new Color(  0, 210, 210);
        c[Tile.BOSS_SPAWN]  = new Color(210,  50, 210);
        return c;
    }

    private static Color[] buildZonePalette() {
        Color[] c = new Color[ZoneBase.values().length];
        c[ZoneBase.SOLID_FILL.ordinal()] = new Color( 80,  82, 100);
        c[ZoneBase.AIR.ordinal()]        = new Color( 20,  22,  40);
        c[ZoneBase.PLATFORM.ordinal()]   = new Color(130,  85,  40);
        c[ZoneBase.LIQUID.ordinal()]     = new Color( 30, 100, 200);
        c[ZoneBase.HAZARD.ordinal()]     = new Color(210, 195,  50);
        c[ZoneBase.DOOR.ordinal()]       = new Color( 60, 200,  90);
        c[ZoneBase.FEATURE.ordinal()]    = new Color(210,  50, 210);
        return c;
    }

    private static Color[] buildSurfacePalette() {
        Color[] c = new Color[ZoneSurface.values().length];
        c[ZoneSurface.NONE.ordinal()]       = new Color( 40,  40,  55);
        c[ZoneSurface.FLOOR.ordinal()]      = new Color( 60, 160,  80);
        c[ZoneSurface.CEILING.ordinal()]    = new Color( 80, 100, 200);
        c[ZoneSurface.LEFT_WALL.ordinal()]  = new Color(200, 130,  50);
        c[ZoneSurface.RIGHT_WALL.ordinal()] = new Color(230, 160,  60);
        c[ZoneSurface.CORNER.ordinal()]     = new Color(180,  60, 180);
        c[ZoneSurface.ENCLOSED.ordinal()]   = new Color( 55,  55,  65);
        c[ZoneSurface.LEDGE.ordinal()]      = new Color(230, 210,  80);
        return c;
    }

    private static Color[] buildVariantPalette() {
        FillVariant[] vals = FillVariant.values();
        Color[] c = new Color[vals.length];
        for (int i = 0; i < vals.length; i++) {
            c[i] = Color.getHSBColor((float) i / vals.length, 0.65f, 0.72f);
        }
        return c;
    }
}
