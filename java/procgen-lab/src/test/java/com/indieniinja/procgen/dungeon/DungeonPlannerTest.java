package com.indieniinja.procgen.dungeon;

import com.indieniinja.procgen.intent.DungeonIntent;
import com.indieniinja.procgen.model.Ability;
import com.indieniinja.procgen.model.Biome;
import com.indieniinja.procgen.model.RoomType;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class DungeonPlannerTest {

    private DungeonPlan plan;

    @BeforeEach
    void setup() {
        DungeonIntent intent = new DungeonIntent(
                "court_of_proof",
                "Court of Proof",
                Biome.DUNGEON,
                "Prove your worth through dash mastery",
                Ability.DASH,
                8,
                2,
                true,  // hasBoss
                true,  // hasShortcut
                true); // hasTreasureBranch
        plan = new DungeonPlanner().plan(intent);
    }

    @Test
    void producesAtLeastEightRooms() {
        assertThat(plan.roomGraph.nodes()).hasSizeGreaterThanOrEqualTo(8);
    }

    @Test
    void hasStartRoom() {
        assertThat(plan.roomGraph.firstByType(RoomType.START)).isNotNull();
    }

    @Test
    void hasTreasureRoom() {
        assertThat(plan.roomGraph.firstByType(RoomType.TREASURE)).isNotNull();
    }

    @Test
    void hasBossRoom() {
        assertThat(plan.roomGraph.firstByType(RoomType.BOSS)).isNotNull();
    }

    @Test
    void hasExitRoom() {
        assertThat(plan.roomGraph.firstByType(RoomType.EXIT)).isNotNull();
    }

    @Test
    void hasPuzzleRoomWithDashAbility() {
        RoomNode puzzle = plan.roomGraph.firstByType(RoomType.PUZZLE);
        assertThat(puzzle).isNotNull();
        assertThat(puzzle.intent.requiredAbilities).contains(Ability.DASH);
    }

    @Test
    void graphIsConnected() {
        assertThat(plan.roomGraph.isConnected()).isTrue();
    }

    @Test
    void puzzleGoalIsDashRelated() {
        RoomNode puzzle = plan.roomGraph.firstByType(RoomType.PUZZLE);
        assertThat(puzzle.intent.traversalGoal).isEqualTo("cross_gap_with_dash");
    }

    @Test
    void shortcutRoomPresent() {
        assertThat(plan.roomGraph.firstByType(RoomType.SHORTCUT)).isNotNull();
    }

    @Test
    void deterministicAcrossRuns() {
        DungeonIntent intent = plan.intent;
        DungeonPlan a = new DungeonPlanner().plan(intent);
        DungeonPlan b = new DungeonPlanner().plan(intent);
        assertThat(a.roomGraph.nodes().size()).isEqualTo(b.roomGraph.nodes().size());
        for (int i = 0; i < a.roomGraph.nodes().size(); i++) {
            assertThat(a.roomGraph.nodes().get(i).id)
                    .isEqualTo(b.roomGraph.nodes().get(i).id);
        }
    }
}
