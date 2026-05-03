package com.indieniinja.procgen.passes;

import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.model.ZoneBase;
import com.indieniinja.procgen.model.ZoneCell;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class SolidFillPassTest {

    @Test
    void producesCorrectGridDimensions() {
        ZoneCell[][] zones = new SolidFillPass().apply();
        assertThat(zones.length).isEqualTo(GenConfig.ZONE_W);
        assertThat(zones[0].length).isEqualTo(GenConfig.ZONE_H);
    }

    @Test
    void noNullCells() {
        ZoneCell[][] zones = new SolidFillPass().apply();
        for (int x = 0; x < GenConfig.ZONE_W; x++)
            for (int y = 0; y < GenConfig.ZONE_H; y++)
                assertThat(zones[x][y]).isNotNull();
    }

    @Test
    void allCellsAreSolidFill() {
        ZoneCell[][] zones = new SolidFillPass().apply();
        for (int x = 0; x < GenConfig.ZONE_W; x++)
            for (int y = 0; y < GenConfig.ZONE_H; y++)
                assertThat(zones[x][y].base)
                        .as("zone [%d][%d]", x, y)
                        .isEqualTo(ZoneBase.SOLID_FILL);
    }
}
