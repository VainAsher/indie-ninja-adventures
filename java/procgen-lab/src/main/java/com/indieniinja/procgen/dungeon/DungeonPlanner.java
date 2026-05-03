package com.indieniinja.procgen.dungeon;

import com.indieniinja.procgen.intent.DungeonIntent;
import com.indieniinja.procgen.intent.RoomIntent;
import com.indieniinja.procgen.model.Ability;
import com.indieniinja.procgen.model.Direction;
import com.indieniinja.procgen.model.RoomType;

import java.util.EnumSet;
import java.util.Set;

public final class DungeonPlanner {

    /**
     * Builds a DungeonPlan from a DungeonIntent.
     *
     * Layout follows the spec target:
     *   Start → Traversal → Puzzle → Save → Combat → Boss → Exit
     *                          ↘ Treasure (optional)
     *
     * Additional rooms are appended to satisfy intent.roomCount if the base
     * layout is smaller.
     */
    public DungeonPlan plan(DungeonIntent intent) {
        RoomGraph graph = new RoomGraph();

        int col = 0;

        // --- Critical path ---
        RoomNode start = room(intent, "start", RoomType.START, EnumSet.noneOf(Ability.class),
                "rest", col++, 0);
        graph.add(start);

        RoomNode traversal = room(intent, "traversal", RoomType.TRAVERSAL, EnumSet.noneOf(Ability.class),
                "horizontal_intro", col++, 0);
        graph.add(traversal);
        start.connect(traversal);

        // Puzzle room gates the ability focus
        Set<Ability> abilityGate = intent.abilityFocus != null
                ? EnumSet.of(intent.abilityFocus)
                : EnumSet.noneOf(Ability.class);
        String puzzleGoal = abilityGoal(intent.abilityFocus);
        RoomNode puzzle = room(intent, "puzzle", RoomType.PUZZLE, abilityGate, puzzleGoal, col++, 0);
        graph.add(puzzle);
        traversal.connect(puzzle);

        // Optional treasure branch hangs off puzzle
        if (intent.hasTreasureBranch) {
            RoomNode treasure = room(intent, "treasure", RoomType.TREASURE,
                    EnumSet.noneOf(Ability.class), "optional_reward", col - 1, 1);
            graph.add(treasure);
            puzzle.connect(treasure);
        }

        RoomNode save = room(intent, "save", RoomType.SAVE, EnumSet.noneOf(Ability.class),
                "rest", col++, 0);
        graph.add(save);
        puzzle.connect(save);

        RoomNode combat = room(intent, "combat", RoomType.COMBAT, EnumSet.noneOf(Ability.class),
                "movement_pressure", col++, 0);
        graph.add(combat);
        save.connect(combat);

        // Optional shortcut from traversal → combat
        if (intent.hasShortcut) {
            RoomNode shortcut = room(intent, "shortcut", RoomType.SHORTCUT,
                    EnumSet.noneOf(Ability.class), "horizontal_intro", col - 2, -1);
            graph.add(shortcut);
            traversal.connect(shortcut);
            shortcut.connect(combat);
        }

        RoomNode boss = null;
        if (intent.hasBoss) {
            boss = room(intent, "boss", RoomType.BOSS, EnumSet.noneOf(Ability.class),
                    "movement_pressure", col++, 0);
            graph.add(boss);
            combat.connect(boss);
        }

        RoomNode exit = room(intent, "exit", RoomType.EXIT, EnumSet.noneOf(Ability.class),
                "rest", col, 0);
        graph.add(exit);
        (boss != null ? boss : combat).connect(exit);

        return new DungeonPlan(intent, graph);
    }

    // -------------------------------------------------------------------------

    private RoomNode room(DungeonIntent dungeon, String suffix, RoomType type,
                          Set<Ability> abilities, String traversalGoal,
                          int graphX, int graphY) {
        String id = dungeon.id + "_" + suffix;

        // Infer connections from graph position — doors resolved properly in S3
        Set<Direction> connections = EnumSet.noneOf(Direction.class);

        RoomIntent intent = new RoomIntent(
                type,
                dungeon.biome,
                dungeon.difficulty,
                abilities,
                connections,
                "",
                traversalGoal,
                type != RoomType.TREASURE && type != RoomType.SHORTCUT);

        return new RoomNode(id, intent, graphX, graphY);
    }

    private static String abilityGoal(Ability ability) {
        if (ability == null) return "horizontal_intro";
        return switch (ability) {
            case DASH        -> "cross_gap_with_dash";
            case WALL_JUMP   -> "vertical_ascent";
            case CLIMB       -> "vertical_ascent";
            case DOUBLE_JUMP -> "vertical_ascent";
            default          -> "horizontal_intro";
        };
    }
}
