package com.indieniinja.world;

/**
 * Computes the autotile role (neighbor bitmask) for a solid tile in a byte grid.
 *
 * Compatible with the mk_16_16 nature tileset blob-set encoding used by
 * BlobTileSet. Both SOLID and PLATFORM neighbours count as solid for role
 * purposes so that terrain edges look correct when adjacent to platforms.
 *
 * Bit encoding (matches mk_nature_blob_sets.json role values 0–255):
 *
 *   bit 7 (128) = W  — west  (left)
 *   bit 6 ( 64) = NW — north-west corner  (only set when N and W both solid)
 *   bit 5 ( 32) = N  — north (up)
 *   bit 4 ( 16) = NE — north-east corner  (only set when N and E both solid)
 *   bit 3 (  8) = E  — east  (right)
 *   bit 2 (  4) = SE — south-east corner  (only set when S and E both solid)
 *   bit 1 (  2) = S  — south (down)
 *   bit 0 (  1) = SW — south-west corner  (only set when S and W both solid)
 *
 * The 47 valid role values (subset of 0–255) are those produced by the corner-
 * correction rule: diagonal bits are only set when both adjacent cardinal bits
 * are set.  Any out-of-bounds neighbour is treated as solid (seals world edges).
 */
public final class AutotileResolver {

    private AutotileResolver() {}

    /**
     * Compute the blob-autotile role for the cell at grid[r][c].
     *
     * @param grid byte[rows][cols] from {@link WorldGenerator}
     * @param r    row of the cell
     * @param c    column of the cell
     * @param rows grid height
     * @param cols grid width
     * @return role value in 0..255 that can be looked up in a blob-set
     */
    public static int computeRole(byte[][] grid, int r, int c, int rows, int cols) {
        boolean N  = isSolid(grid, r - 1, c,     rows, cols);
        boolean S  = isSolid(grid, r + 1, c,     rows, cols);
        boolean E  = isSolid(grid, r,     c + 1, rows, cols);
        boolean W  = isSolid(grid, r,     c - 1, rows, cols);
        boolean NE = isSolid(grid, r - 1, c + 1, rows, cols);
        boolean NW = isSolid(grid, r - 1, c - 1, rows, cols);
        boolean SE = isSolid(grid, r + 1, c + 1, rows, cols);
        boolean SW = isSolid(grid, r + 1, c - 1, rows, cols);

        int role = 0;
        if (N)           role |= 32;   // bit5
        if (S)           role |= 2;    // bit1
        if (E)           role |= 8;    // bit3
        if (W)           role |= 128;  // bit7
        if (N && E && NE) role |= 16;  // bit4 — NE corner
        if (N && W && NW) role |= 64;  // bit6 — NW corner
        if (S && E && SE) role |= 4;   // bit2 — SE corner
        if (S && W && SW) role |= 1;   // bit0 — SW corner
        return role;
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    /**
     * Returns true when the given cell is solid (or out of bounds — treated as
     * solid so world edges are tiled correctly).
     * Both SOLID and PLATFORM tile types are treated as solid for autotiling.
     */
    private static boolean isSolid(byte[][] grid, int r, int c, int rows, int cols) {
        if (r < 0 || r >= rows || c < 0 || c >= cols) return true;
        return grid[r][c] != WorldGenerator.AIR;
    }
}
