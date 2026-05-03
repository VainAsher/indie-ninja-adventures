package com.indieniinja.procgen.validation;

import com.indieniinja.procgen.intent.RoomIntent;
import com.indieniinja.procgen.model.Ability;
import com.indieniinja.procgen.model.Biome;
import com.indieniinja.procgen.model.Direction;
import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.model.RoomType;
import com.indieniinja.procgen.model.Tile;
import com.indieniinja.procgen.model.ZoneCell;
import com.indieniinja.procgen.passes.CarvePass;
import com.indieniinja.procgen.passes.DoorPass;
import com.indieniinja.procgen.passes.FillVariantPass;
import com.indieniinja.procgen.passes.SolidFillPass;
import com.indieniinja.procgen.passes.SurfaceClassificationPass;
import com.indieniinja.procgen.passes.TileStampPass;
import com.indieniinja.procgen.passes.TraversalGoal;
import org.junit.jupiter.api.Test;

import java.util.EnumSet;
import java.util.Random;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

class TraversalValidatorTest {

    // ---- Positive: basic room reachable with just JUMP ----------------------

    @Test
    void basicRoomValidatesWithJumpOnly() {
        byte[][] tiles = buildTiles(TraversalGoal.HORIZONTAL_INTRO,
                EnumSet.noneOf(Direction.class), EnumSet.noneOf(Ability.class));
        ValidationResult result = new TraversalValidator()
                .validate(tiles, intent(TraversalGoal.HORIZONTAL_INTRO,
                        EnumSet.noneOf(Direction.class),
                        EnumSet.noneOf(Ability.class)),
                        EnumSet.of(Ability.JUMP));
        assertThat(result.valid).isTrue();
        assertThat(result.errors).isEmpty();
    }

    // ---- Positive: dash room validates WITH Dash ----------------------------

    @Test
    void dashRoomValidatesWithDash() {
        RoomIntent intent = dashPuzzleIntent();
        byte[][] tiles = buildTilesFromIntent(intent);
        ValidationResult result = new TraversalValidator()
                .validate(tiles, intent, EnumSet.of(Ability.DASH));
        assertThat(result.valid)
                .as("Dash room should be valid with DASH: errors=%s", result.errors)
                .isTrue();
    }

    // ---- Negative: dash room fails WITHOUT Dash ------------------------------

    @Test
    void dashRoomFailsWithoutDash() {
        // Build an explicit tilemap with a gap that requires dash:
        // left platform, solid gap column, right platform, left/right doors.
        byte[][] tiles = buildDashGapTilemap();
        RoomIntent intent = dashPuzzleIntent();
        ValidationResult result = new TraversalValidator()
                .validate(tiles, intent, EnumSet.noneOf(Ability.class));
        assertThat(result.valid)
                .as("Dash room should be invalid without DASH")
                .isFalse();
        assertThat(result.errors).isNotEmpty();
        assertThat(result.errors.get(0)).containsIgnoringCase("not reachable");
    }

    // ---- Error messages are useful -------------------------------------------

    @Test
    void errorMessageContainsDoorDirection() {
        byte[][] tiles = buildDashGapTilemap();
        RoomIntent intent = dashPuzzleIntent();
        ValidationResult result = new TraversalValidator()
                .validate(tiles, intent, EnumSet.noneOf(Ability.class));
        assertThat(result.errors.get(0)).containsIgnoringCase("RIGHT");
    }

    // ---- Warnings only for degenerate room -----------------------------------

    @Test
    void allSolidRoomProducesWarning() {
        byte[][] tiles = new byte[GenConfig.ROOM_W][GenConfig.ROOM_H];
        for (int x = 0; x < GenConfig.ROOM_W; x++)
            for (int y = 0; y < GenConfig.ROOM_H; y++)
                tiles[x][y] = Tile.SOLID;
        RoomIntent intent = intent(TraversalGoal.REST, EnumSet.noneOf(Direction.class),
                EnumSet.noneOf(Ability.class));
        ValidationResult result = new TraversalValidator()
                .validate(tiles, intent, EnumSet.noneOf(Ability.class));
        // Either an error (no start pos) or a warning (< 4 reachable tiles)
        assertThat(result.valid).isFalse();
    }

    // =========================================================================
    // Helpers

    /**
     * Builds a tilemap with a genuine horizontal dash gap:
     *   - Left half: open corridor floor
     *   - Centre column: solid (the gap)
     *   - Right half: open corridor floor
     *   - Left + Right doors at mid height
     */
    private static byte[][] buildDashGapTilemap() {
        byte[][] tiles = new byte[GenConfig.ROOM_W][GenConfig.ROOM_H];
        int midY  = GenConfig.ROOM_H / 2;
        int gapX  = GenConfig.ROOM_W / 2;

        // Fill everything solid
        for (int x = 0; x < GenConfig.ROOM_W; x++)
            for (int y = 0; y < GenConfig.ROOM_H; y++)
                tiles[x][y] = Tile.SOLID;

        // Carve left corridor (cols 0 to gapX-1, rows midY-4 to midY)
        for (int x = 0; x < gapX; x++)
            for (int y = midY - 4; y <= midY; y++)
                tiles[x][y] = Tile.AIR;

        // Carve right corridor (cols gapX+1 to ROOM_W-1, rows midY-4 to midY)
        for (int x = gapX + 1; x < GenConfig.ROOM_W; x++)
            for (int y = midY - 4; y <= midY; y++)
                tiles[x][y] = Tile.AIR;

        // gapX column stays SOLID — this is the gap the dash must cross

        // Left door
        for (int y = midY - 2; y <= midY; y++) tiles[0][y] = Tile.DOOR;
        // Right door
        for (int y = midY - 2; y <= midY; y++) tiles[GenConfig.ROOM_W - 1][y] = Tile.DOOR;

        return tiles;
    }

    private static RoomIntent dashPuzzleIntent() {
        return intent(TraversalGoal.CROSS_GAP_WITH_DASH,
                EnumSet.of(Direction.LEFT, Direction.RIGHT),
                EnumSet.of(Ability.DASH));
    }

    private static RoomIntent intent(String goal, Set<Direction> connections,
                                     Set<Ability> abilities) {
        return new RoomIntent(RoomType.PUZZLE, Biome.DUNGEON, 1,
                abilities, connections, "", goal, true);
    }

    private static byte[][] buildTiles(String goal, Set<Direction> connections,
                                       Set<Ability> abilities) {
        return buildTilesFromIntent(intent(goal, connections, abilities));
    }

    private static byte[][] buildTilesFromIntent(RoomIntent intent) {
        ZoneCell[][] zones = new SolidFillPass().apply();
        Random rng = new Random(42L);
        new CarvePass().apply(zones, intent, rng);
        new DoorPass().apply(zones, intent.connections);
        new SurfaceClassificationPass().apply(zones);
        new FillVariantPass().apply(zones, intent, new Random(42L));
        return new TileStampPass().apply(zones);
    }
}
