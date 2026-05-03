package com.indieniinja.procgen.ui;

import com.indieniinja.procgen.map.DungeonMapRenderer;
import com.indieniinja.procgen.map.RoomMinimapRenderer;
import com.indieniinja.procgen.model.GenConfig;

import javax.swing.*;
import java.awt.*;
import java.awt.image.BufferedImage;

public final class ProcgenLabFrame extends JFrame {

    public ProcgenLabFrame(long initialSeed) {
        super("Procedural Generation Lab — Shadow Ascent");

        UiController   controller = new UiController(initialSeed);
        SelectionModel selection  = new SelectionModel();
        RenderPanel    render     = new RenderPanel(selection);
        LogPanel       log        = new LogPanel();
        ToolBarPanel   toolbar    = new ToolBarPanel(controller);
        HierarchyPanel hierarchy  = new HierarchyPanel(controller);
        InspectorPanel inspector  = new InspectorPanel(controller, selection);

        // Dungeon map panel (live thumbnail under hierarchy)
        JLabel dungeonMapLabel = new JLabel();
        dungeonMapLabel.setHorizontalAlignment(SwingConstants.CENTER);
        dungeonMapLabel.setBorder(BorderFactory.createTitledBorder("Dungeon"));

        // Minimap panel (live thumbnail in inspector)
        JLabel minimapLabel = new JLabel();
        minimapLabel.setHorizontalAlignment(SwingConstants.CENTER);
        minimapLabel.setBorder(BorderFactory.createTitledBorder("Minimap"));

        controller.addRoomListener(() -> {
            render.setRoom(controller.getCurrentRoom());
            render.setViewMode(controller.getViewMode());
            log.setRoom(controller.getCurrentRoom());

            if (controller.getDungeonPlan() != null) {
                BufferedImage dmap = new DungeonMapRenderer()
                        .render(controller.getDungeonPlan(), controller.getSelectedNode());
                dungeonMapLabel.setIcon(new ImageIcon(dmap));
            }
            if (controller.getCurrentRoom() != null) {
                BufferedImage minimap = new RoomMinimapRenderer()
                        .render(controller.getCurrentRoom());
                minimapLabel.setIcon(new ImageIcon(minimap));
            }
        });

        // Left panel: hierarchy tree + dungeon map thumbnail
        JPanel leftPanel = new JPanel(new BorderLayout());
        leftPanel.add(hierarchy, BorderLayout.CENTER);
        leftPanel.add(dungeonMapLabel, BorderLayout.SOUTH);
        leftPanel.setPreferredSize(new Dimension(185, 0));

        // Right panel: inspector + minimap thumbnail
        JPanel rightPanel = new JPanel(new BorderLayout());
        rightPanel.add(inspector, BorderLayout.CENTER);
        rightPanel.add(minimapLabel, BorderLayout.SOUTH);
        rightPanel.setPreferredSize(new Dimension(215, 0));

        // Export button added to toolbar
        JButton exportBtn = new JButton("Export…");
        exportBtn.addActionListener(e -> {
            if (controller.getCurrentRoom() != null) {
                new ExportDialog(this, controller.getCurrentRoom()).setVisible(true);
            }
        });
        toolbar.add(exportBtn);

        // Center: render panel (scrollable) + right panel
        JSplitPane centerSplit = new JSplitPane(
                JSplitPane.HORIZONTAL_SPLIT,
                new JScrollPane(render),
                rightPanel);
        centerSplit.setResizeWeight(1.0);
        centerSplit.setDividerLocation(GenConfig.ROOM_W * 4 + 22);

        // Outer: left panel + center
        JSplitPane mainSplit = new JSplitPane(
                JSplitPane.HORIZONTAL_SPLIT,
                leftPanel,
                centerSplit);
        mainSplit.setDividerLocation(185);
        mainSplit.setResizeWeight(0.0);

        setLayout(new BorderLayout());
        add(toolbar, BorderLayout.NORTH);
        add(mainSplit, BorderLayout.CENTER);
        add(log, BorderLayout.SOUTH);

        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        pack();
        setLocationRelativeTo(null);
        setVisible(true);

        controller.regenerate(initialSeed);
    }
}
