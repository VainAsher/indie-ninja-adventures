package com.indieniinja.procgen.validation;

import com.indieniinja.procgen.intent.RoomIntent;
import com.indieniinja.procgen.model.Ability;
import com.indieniinja.procgen.model.Direction;
import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.model.Tile;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.Set;

/**
 * Simplified tile-based traversal validator.
 *
 * Movement model (intentionally approximate — sufficient for S4 gate checks):
 *   - Walk: move left/right on a surface
 *   - Fall: drop straight down into air
 *   - Jump: rise up to MAX_JUMP_HEIGHT tiles above a surface
 *   - Dash: cross one solid-column horizontal gap (requires DASH ability)
 *
 * The validator does NOT model wall-jump, climb, or grapple at this stage.
 * Those are added when WALL_JUMP / CLIMB / GRAPPLE puzzle rooms are introduced.
 */
public final class TraversalValidator {

    // 16 tiles = 2 zones — enough to clear a full door zone opening (3 zones tall)
    // without requiring wall-jump or climb abilities.
    private static final int MAX_JUMP_HEIGHT = 16;
    // A dash crosses one zone = 8 tiles; allow up to 12 to give margin.
    private static final int DASH_MAX_GAP   = 12;

    /**
     * Validates whether the room is completable with the given ability set.
     *
     * @param tiles    128×128 tilemap [x][y]
     * @param intent   room intent describing connections and required abilities
     * @param abilities the ability set available to the player during this check
     */
    public ValidationResult validate(byte[][] tiles, RoomIntent intent, Set<Ability> abilities) {
        ValidationResult result = new ValidationResult();

        int[] start = findStart(tiles, intent);
        if (start == null) {
            result.error("No valid player start position found (no air tile above a solid floor).");
            return result;
        }

        boolean[][] reachable = flood(tiles, start[0], start[1], abilities);
        result.reachable = reachable;

        // Check each required exit door is reachable
        for (Direction dir : intent.connections) {
            int[] doorTile = doorSampleTile(dir);
            if (!reachable[doorTile[0]][doorTile[1]]) {
                result.error(String.format(
                        "Exit door %s at tile (%d,%d) is not reachable with abilities %s.",
                        dir, doorTile[0], doorTile[1], abilities));
            }
        }

        // Warn if no tiles at all were reached (degenerate room)
        long reachableCount = countReachable(reachable);
        if (reachableCount < 4) {
            result.warn("Fewer than 4 tiles reachable — room may be degenerate.");
        }

        return result;
    }

    // -------------------------------------------------------------------------
    // Flood fill

    private boolean[][] flood(byte[][] tiles, int startX, int startY, Set<Ability> abilities) {
        boolean[][] visited = new boolean[GenConfig.ROOM_W][GenConfig.ROOM_H];
        Deque<int[]> queue  = new ArrayDeque<>();

        visit(visited, queue, startX, startY);

        while (!queue.isEmpty()) {
            int[] pos = queue.poll();
            int x = pos[0], y = pos[1];

            // Walk left / right
            tryVisit(tiles, visited, queue, x - 1, y);
            tryVisit(tiles, visited, queue, x + 1, y);

            // Fall straight down
            tryVisit(tiles, visited, queue, x, y + 1);

            // Jump upward (up to MAX_JUMP_HEIGHT above a surface)
            if (isOnSurface(tiles, x, y)) {
                for (int h = 1; h <= MAX_JUMP_HEIGHT; h++) {
                    if (!isAir(tiles, x, y - h)) break;
                    tryVisit(tiles, visited, queue, x, y - h);
                }
            }

            // Dash: cross one solid column gap horizontally
            if (abilities.contains(Ability.DASH)) {
                tryDash(tiles, visited, queue, x, y, -1); // dash left
                tryDash(tiles, visited, queue, x, y,  1); // dash right
            }
        }

        return visited;
    }

    /**
     * Attempt to dash over a solid gap of 1..DASH_MAX_GAP tiles in direction dx.
     * All intermediate tiles must be solid; the landing tile must be air.
     */
    private void tryDash(byte[][] tiles, boolean[][] visited, Deque<int[]> queue,
                         int x, int y, int dx) {
        for (int gap = 1; gap <= DASH_MAX_GAP; gap++) {
            int checkX = x + dx * gap;
            if (!inBounds(checkX, y)) break;
            if (isAir(tiles, checkX, y)) {
                // Found air after 'gap' solid tiles — this is the landing
                tryVisit(tiles, visited, queue, checkX, y);
                break;
            }
            // checkX is solid — keep extending the gap
        }
    }

    // -------------------------------------------------------------------------
    // Helpers

    /** Find the first air tile with a solid floor directly below, near the left entrance. */
    private static int[] findStart(byte[][] tiles, RoomIntent intent) {
        int startX = GenConfig.ROOM_W / 4;
        int startY = GenConfig.ROOM_H / 2;

        // Scan down from the mid-left area for a standing position
        for (int y = startY - 10; y < GenConfig.ROOM_H - 1; y++) {
            if (y < 0) continue;
            if (isAir(tiles, startX, y) && !isAir(tiles, startX, y + 1)) {
                return new int[]{startX, y};
            }
        }
        // Fallback: scan entire room for any standing tile
        for (int x = 1; x < GenConfig.ROOM_W - 1; x++) {
            for (int y = 1; y < GenConfig.ROOM_H - 1; y++) {
                if (isAir(tiles, x, y) && !isAir(tiles, x, y + 1)) {
                    return new int[]{x, y};
                }
            }
        }
        return null;
    }

    /** Representative tile for a door opening in a given direction. */
    private static int[] doorSampleTile(Direction dir) {
        int midX = GenConfig.ROOM_W / 2;
        int midY = GenConfig.ROOM_H / 2;
        return switch (dir) {
            case LEFT  -> new int[]{2,       midY};
            case RIGHT -> new int[]{GenConfig.ROOM_W - 3, midY};
            case UP    -> new int[]{midX, 2};
            case DOWN  -> new int[]{midX, GenConfig.ROOM_H - 3};
        };
    }

    private static void tryVisit(byte[][] tiles, boolean[][] visited,
                                  Deque<int[]> queue, int x, int y) {
        if (!inBounds(x, y)) return;
        if (visited[x][y]) return;
        if (!isAir(tiles, x, y)) return;
        visit(visited, queue, x, y);
    }

    private static void visit(boolean[][] visited, Deque<int[]> queue, int x, int y) {
        visited[x][y] = true;
        queue.add(new int[]{x, y});
    }

    private static boolean isAir(byte[][] tiles, int x, int y) {
        if (!inBounds(x, y)) return false;
        byte t = tiles[x][y];
        return t == Tile.AIR || t == Tile.DOOR || t == Tile.PLATFORM
                || t == Tile.PICKUP || t == Tile.SAVE_POINT || t == Tile.ENEMY_SPAWN
                || t == Tile.BOSS_SPAWN || t == Tile.CLIMBABLE;
    }

    private static boolean isOnSurface(byte[][] tiles, int x, int y) {
        if (!inBounds(x, y + 1)) return true; // bottom edge counts as surface
        return !isAir(tiles, x, y + 1);
    }

    private static boolean inBounds(int x, int y) {
        return x >= 0 && x < GenConfig.ROOM_W && y >= 0 && y < GenConfig.ROOM_H;
    }

    private static long countReachable(boolean[][] visited) {
        long n = 0;
        for (boolean[] col : visited)
            for (boolean v : col)
                if (v) n++;
        return n;
    }
}
