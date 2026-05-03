package com.indieniinja.procgen.ui;

import com.indieniinja.procgen.dungeon.RoomNode;
import com.indieniinja.procgen.macro.RegionPlan;

import javax.swing.*;
import javax.swing.tree.*;
import java.awt.*;

public final class HierarchyPanel extends JPanel {

    private final JTree        tree;
    private final UiController controller;
    private boolean            rebuilding = false;

    public HierarchyPanel(UiController controller) {
        this.controller = controller;
        setLayout(new BorderLayout());
        setPreferredSize(new Dimension(185, 0));

        add(new JLabel("Hierarchy", SwingConstants.CENTER), BorderLayout.NORTH);
        tree = new JTree(new DefaultMutableTreeNode("(none)"));
        tree.setRootVisible(true);
        add(new JScrollPane(tree), BorderLayout.CENTER);

        tree.addTreeSelectionListener(e -> {
            if (rebuilding) return;
            DefaultMutableTreeNode node =
                    (DefaultMutableTreeNode) tree.getLastSelectedPathComponent();
            if (node == null) return;
            if (node.getUserObject() instanceof RoomNode rn) {
                controller.selectRoom(rn);
            }
        });

        controller.addHierarchyListener(this::rebuildTree);
    }

    private void rebuildTree() {
        if (controller.getWorldPlan() == null) return;
        rebuilding = true;
        try {
            DefaultMutableTreeNode root =
                    new DefaultMutableTreeNode(controller.getWorldPlan().campaignName);

            for (RegionPlan region : controller.getWorldPlan().regions) {
                DefaultMutableTreeNode regionNode =
                        new DefaultMutableTreeNode(region.intent.displayName);
                root.add(regionNode);

                if (controller.getDungeonPlan() != null) {
                    DefaultMutableTreeNode dungeonNode =
                            new DefaultMutableTreeNode(controller.getDungeonPlan().intent.displayName);
                    regionNode.add(dungeonNode);

                    for (RoomNode rn : controller.getDungeonPlan().roomGraph.nodes()) {
                        dungeonNode.add(new DefaultMutableTreeNode(rn));
                    }
                }
            }

            DefaultTreeModel model = new DefaultTreeModel(root);
            tree.setModel(model);
            for (int i = 0; i < tree.getRowCount(); i++) tree.expandRow(i);

            // Restore selection to the currently active room node
            selectCurrentNode(root);
        } finally {
            rebuilding = false;
        }
    }

    private void selectCurrentNode(DefaultMutableTreeNode root) {
        RoomNode current = controller.getSelectedNode();
        if (current == null) return;
        javax.swing.tree.TreeNode[] path = findPath(root, current);
        if (path != null) tree.setSelectionPath(new TreePath(path));
    }

    private static javax.swing.tree.TreeNode[] findPath(DefaultMutableTreeNode root, RoomNode target) {
        java.util.Enumeration<?> e = root.depthFirstEnumeration();
        while (e.hasMoreElements()) {
            DefaultMutableTreeNode node = (DefaultMutableTreeNode) e.nextElement();
            if (node.getUserObject() == target) {
                return node.getPath();
            }
        }
        return null;
    }
}
