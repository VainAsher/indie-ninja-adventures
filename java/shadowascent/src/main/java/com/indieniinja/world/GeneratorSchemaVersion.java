package com.indieniinja.world;

/**
 * Version identity for deterministic world-generation exports.
 *
 * Increment this when snapshot shape, generator layer ordering, or seed-stream
 * semantics change in a way that affects regression baselines.
 */
public final class GeneratorSchemaVersion {
    public static final int CURRENT = 2;

    private GeneratorSchemaVersion() {}
}
