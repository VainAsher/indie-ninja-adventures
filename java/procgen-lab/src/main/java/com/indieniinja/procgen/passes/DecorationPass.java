package com.indieniinja.procgen.passes;

import com.indieniinja.procgen.intent.RoomIntent;

import java.util.Random;

/**
 * Pass 9 — Non-critical visual decoration.
 *
 * Decoration must never affect required traversal.  At this stage the pass
 * is intentionally minimal: it records that the decoration pass ran without
 * modifying tiles, preserving the contract that it can be disabled without
 * breaking any room.  Visual scatter will be added in a later authoring pass.
 */
public final class DecorationPass {

    public void apply(byte[][] tiles, RoomIntent intent, Random rng) {
        // No-op: decoration is biome-authored content, not procedural at this stage.
        // The pass exists to complete the 10-pass pipeline contract.
    }
}
