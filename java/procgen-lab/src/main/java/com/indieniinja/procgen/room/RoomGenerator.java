package com.indieniinja.procgen.room;

import com.indieniinja.procgen.intent.RoomIntent;
import com.indieniinja.procgen.model.ZoneCell;
import com.indieniinja.procgen.passes.CarvePass;
import com.indieniinja.procgen.quest.FeatureRequest;
import com.indieniinja.procgen.passes.DecorationPass;
import com.indieniinja.procgen.passes.DoorPass;
import com.indieniinja.procgen.passes.FillVariantPass;
import com.indieniinja.procgen.passes.GameplayFeaturePass;
import com.indieniinja.procgen.passes.SolidFillPass;
import com.indieniinja.procgen.passes.SurfaceClassificationPass;
import com.indieniinja.procgen.passes.TileStampPass;
import com.indieniinja.procgen.passes.TraversalFeaturePass;
import com.indieniinja.procgen.validation.TraversalValidator;
import com.indieniinja.procgen.validation.ValidationResult;

import java.util.List;
import java.util.Random;

/**
 * Orchestrates all 10 room generation passes and the validation/retry loop.
 */
public final class RoomGenerator {

    private static final int MAX_ATTEMPTS = 20;

    public GeneratedRoom generate(RoomIntent intent, long seed) {
        return generate(intent, seed, List.of());
    }

    public GeneratedRoom generate(RoomIntent intent, long seed,
                                   List<FeatureRequest> featureRequests) {
        for (int attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
            GeneratedRoom room = attempt(intent, seed + attempt, featureRequests);
            if (room.isValid()) return room;
        }
        return attempt(intent, seed + MAX_ATTEMPTS, featureRequests);
    }

    // -------------------------------------------------------------------------

    private GeneratedRoom attempt(RoomIntent intent, long seed,
                                   List<FeatureRequest> featureRequests) {
        Random rng    = new Random(seed);
        RoomGenerationReport report = new RoomGenerationReport(seed, intent);

        // Pass 1: Solid Fill
        ZoneCell[][] zones = new SolidFillPass().apply();
        report.logPass("SolidFillPass", true);

        // Pass 2: Carve
        new CarvePass().apply(zones, intent, rng);
        report.logPass("CarvePass", true);

        // Pass 3: Doors
        new DoorPass().apply(zones, intent.connections);
        report.logPass("DoorPass", true);

        // Pass 4: Surface Classification
        new SurfaceClassificationPass().apply(zones);
        report.logPass("SurfaceClassificationPass", true);

        // Pass 5: Fill Variants
        new FillVariantPass().apply(zones, intent, rng);
        report.logPass("FillVariantPass", true);

        // Pass 6: Tile Stamps
        byte[][] tiles = new TileStampPass().apply(zones);
        report.logPass("TileStampPass", true);

        // Pass 7: Traversal Features
        new TraversalFeaturePass().apply(tiles, zones, intent, rng);
        report.logPass("TraversalFeaturePass", true);

        // Pass 8: Gameplay Features
        new GameplayFeaturePass().apply(tiles, intent, rng, featureRequests);
        report.logPass("GameplayFeaturePass", true);

        // Pass 9: Decoration
        new DecorationPass().apply(tiles, intent, rng);
        report.logPass("DecorationPass", true);

        // Pass 10: Validation
        ValidationResult validation = new TraversalValidator()
                .validate(tiles, intent, intent.requiredAbilities);
        report.validation = validation;
        report.logPass("ValidationPass", validation.valid);
        if (!validation.valid) {
            report.errors.addAll(validation.errors);
        }

        return new GeneratedRoom(intent, zones, tiles, report);
    }
}
