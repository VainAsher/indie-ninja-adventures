package com.indieniinja.procgen.ui;

import com.indieniinja.procgen.dungeon.DungeonPlan;
import com.indieniinja.procgen.dungeon.DungeonPlanner;
import com.indieniinja.procgen.dungeon.RoomNode;
import com.indieniinja.procgen.intent.DungeonIntent;
import com.indieniinja.procgen.intent.RegionIntent;
import com.indieniinja.procgen.intent.WorldIntent;
import com.indieniinja.procgen.macro.WorldPlan;
import com.indieniinja.procgen.macro.WorldPlanner;
import com.indieniinja.procgen.model.Ability;
import com.indieniinja.procgen.model.Biome;
import com.indieniinja.procgen.quest.FeatureRequest;
import com.indieniinja.procgen.quest.QuestGenerator;
import com.indieniinja.procgen.room.GeneratedRoom;
import com.indieniinja.procgen.room.RoomGenerator;

import java.util.ArrayList;
import java.util.EnumSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class UiController {

    private long currentSeed;
    private WorldPlan worldPlan;
    private DungeonPlan dungeonPlan;
    private final Map<String, GeneratedRoom> roomCache = new LinkedHashMap<>();
    private RoomNode selectedNode;
    private GeneratedRoom currentRoom;
    private ViewMode viewMode = ViewMode.TILES;

    // hierarchyListeners fire on full regeneration only.
    // roomListeners fire on room selection, view mode change, and regeneration.
    private final List<Runnable> hierarchyListeners = new ArrayList<>();
    private final List<Runnable> roomListeners      = new ArrayList<>();

    public UiController(long initialSeed) {
        this.currentSeed = initialSeed;
    }

    /** Fires only when the world/dungeon hierarchy is rebuilt (full regeneration). */
    public void addHierarchyListener(Runnable r) { hierarchyListeners.add(r); }

    /** Fires whenever the displayed room or view mode changes. */
    public void addRoomListener(Runnable r) { roomListeners.add(r); }

    /** Fires on hierarchy change (regeneration) only — kept for ToolBarPanel seed sync. */
    public void addChangeListener(Runnable r) { hierarchyListeners.add(r); }

    // -------------------------------------------------------------------------

    public void regenerate(long seed) {
        this.currentSeed = seed;
        roomCache.clear();

        WorldIntent worldIntent = new WorldIntent(seed, "Shadow Ascent", List.of("act1"));
        List<RegionIntent> regionIntents = List.of(new RegionIntent(
                "act1", "Dungeon Trial", Biome.DUNGEON, "tense",
                EnumSet.noneOf(Ability.class), EnumSet.of(Ability.DASH),
                1, false, true, false));
        worldPlan = new WorldPlanner().plan(worldIntent, regionIntents);

        DungeonIntent dungeonIntent = new DungeonIntent(
                "d1", "Trial Dungeon", Biome.DUNGEON, "main",
                Ability.DASH, 8, 1, true, true, true);
        dungeonPlan = new DungeonPlanner().plan(dungeonIntent);
        dungeonPlan.questPlan = new QuestGenerator().generate(dungeonPlan);

        selectedNode = dungeonPlan.roomGraph.start();
        currentRoom = generateRoom(selectedNode, seed);

        for (Runnable r : hierarchyListeners) r.run();
        for (Runnable r : roomListeners) r.run();
    }

    public void selectRoom(RoomNode node) {
        selectedNode = node;
        currentRoom = generateRoom(node, currentSeed);
        for (Runnable r : roomListeners) r.run();
    }

    public void newSeed() {
        regenerate(System.currentTimeMillis());
    }

    public void setViewMode(ViewMode mode) {
        this.viewMode = mode;
        for (Runnable r : roomListeners) r.run();
    }

    // -------------------------------------------------------------------------

    public long getCurrentSeed()          { return currentSeed; }
    public GeneratedRoom getCurrentRoom() { return currentRoom; }
    public ViewMode getViewMode()         { return viewMode; }
    public WorldPlan getWorldPlan()       { return worldPlan; }
    public DungeonPlan getDungeonPlan()   { return dungeonPlan; }
    public RoomNode getSelectedNode()     { return selectedNode; }

    // -------------------------------------------------------------------------

    private GeneratedRoom generateRoom(RoomNode node, long baseSeed) {
        return roomCache.computeIfAbsent(node.id, id -> {
            long roomSeed = baseSeed ^ (long) id.hashCode();
            List<FeatureRequest> requests = dungeonPlan != null && dungeonPlan.questPlan != null
                    ? dungeonPlan.questPlan.forRoom(id)
                    : List.of();
            return new RoomGenerator().generate(node.intent, roomSeed, requests);
        });
    }
}
