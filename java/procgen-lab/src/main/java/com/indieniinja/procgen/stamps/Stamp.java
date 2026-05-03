package com.indieniinja.procgen.stamps;

import com.indieniinja.procgen.model.GenConfig;

/**
 * An 8×8 tile pattern used by TileStampPass to expand a zone into concrete tiles.
 * All implementations must return an array of exactly ZONE_SIZE × ZONE_SIZE.
 */
public interface Stamp {
    /** Returns an 8×8 tile array [x][y]. All tile IDs must be in range 0–12. */
    byte[][] tiles();

    default int size() { return GenConfig.ZONE_SIZE; }
}
