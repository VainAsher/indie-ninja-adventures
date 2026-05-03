package com.indieniinja.procgen.passes;

import com.indieniinja.procgen.intent.RoomIntent;
import com.indieniinja.procgen.model.FillVariant;
import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.model.ZoneBase;
import com.indieniinja.procgen.model.ZoneCell;
import com.indieniinja.procgen.rules.CrackedWallRule;
import com.indieniinja.procgen.rules.FillVariantRule;
import com.indieniinja.procgen.rules.HollowBoxRule;
import com.indieniinja.procgen.rules.PillarRule;
import com.indieniinja.procgen.rules.SolidRule;
import com.indieniinja.procgen.rules.StalactiteRule;
import com.indieniinja.procgen.rules.StalagmiteRule;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * Pass 5 — Replaces SOLID_FILL zones with legal structural variants.
 * Runs after SurfaceClassificationPass. The SolidRule is always the fallback.
 */
public final class FillVariantPass {

    private static final List<FillVariantRule> RULES = List.of(
            new StalactiteRule(),
            new StalagmiteRule(),
            new PillarRule(),
            new CrackedWallRule(),
            new HollowBoxRule(),
            new SolidRule()   // fallback — must be last
    );

    public void apply(ZoneCell[][] zones, RoomIntent intent, Random rng) {
        for (int x = 0; x < GenConfig.ZONE_W; x++) {
            for (int y = 0; y < GenConfig.ZONE_H; y++) {
                if (zones[x][y].base != ZoneBase.SOLID_FILL) continue;
                zones[x][y].variant = selectVariant(zones, x, y, intent, rng);
            }
        }
    }

    private static FillVariant selectVariant(ZoneCell[][] zones, int x, int y,
                                              RoomIntent intent, Random rng) {
        List<FillVariantRule> valid = new ArrayList<>();
        int totalWeight = 0;
        for (FillVariantRule rule : RULES) {
            if (rule.valid(zones, x, y, intent)) {
                valid.add(rule);
                totalWeight += rule.weight(intent);
            }
        }
        if (valid.isEmpty()) return FillVariant.SOLID_8X8;

        int roll = rng.nextInt(totalWeight);
        int cursor = 0;
        for (FillVariantRule rule : valid) {
            cursor += rule.weight(intent);
            if (roll < cursor) return rule.variant();
        }
        return FillVariant.SOLID_8X8;
    }
}
