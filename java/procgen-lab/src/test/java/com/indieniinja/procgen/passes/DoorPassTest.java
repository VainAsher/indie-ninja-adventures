package com.indieniinja.procgen.passes;

import com.indieniinja.procgen.model.Direction;
import com.indieniinja.procgen.model.GenConfig;
import com.indieniinja.procgen.model.ZoneBase;
import com.indieniinja.procgen.model.ZoneCell;
import org.junit.jupiter.api.Test;

import java.util.EnumSet;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

class DoorPassTest {

    @Test
    void leftConnectionPlacesLeftDoor() {
        ZoneCell[][] zones = solid();
        new DoorPass().apply(zones, EnumSet.of(Direction.LEFT));
        assertThat(zones[0][GenConfig.ZONE_H / 2].base).isEqualTo(ZoneBase.DOOR);
    }

    @Test
    void rightConnectionPlacesRightDoor() {
        ZoneCell[][] zones = solid();
        new DoorPass().apply(zones, EnumSet.of(Direction.RIGHT));
        assertThat(zones[GenConfig.ZONE_W - 1][GenConfig.ZONE_H / 2].base).isEqualTo(ZoneBase.DOOR);
    }

    @Test
    void upConnectionPlacesTopDoor() {
        ZoneCell[][] zones = solid();
        new DoorPass().apply(zones, EnumSet.of(Direction.UP));
        assertThat(zones[GenConfig.ZONE_W / 2][0].base).isEqualTo(ZoneBase.DOOR);
    }

    @Test
    void downConnectionPlacesBottomDoor() {
        ZoneCell[][] zones = solid();
        new DoorPass().apply(zones, EnumSet.of(Direction.DOWN));
        assertThat(zones[GenConfig.ZONE_W / 2][GenConfig.ZONE_H - 1].base).isEqualTo(ZoneBase.DOOR);
    }

    @Test
    void leftDoorHasAirClearanceInward() {
        ZoneCell[][] zones = solid();
        new DoorPass().apply(zones, EnumSet.of(Direction.LEFT));
        int midY = GenConfig.ZONE_H / 2;
        // Two zones inward from the door must be air
        assertThat(zones[1][midY].base).isEqualTo(ZoneBase.AIR);
        assertThat(zones[2][midY].base).isEqualTo(ZoneBase.AIR);
    }

    @Test
    void noDoorWhenNoConnections() {
        ZoneCell[][] zones = solid();
        new DoorPass().apply(zones, EnumSet.noneOf(Direction.class));
        for (int x = 0; x < GenConfig.ZONE_W; x++)
            for (int y = 0; y < GenConfig.ZONE_H; y++)
                assertThat(zones[x][y].base)
                        .as("zone [%d][%d]", x, y)
                        .isNotEqualTo(ZoneBase.DOOR);
    }

    @Test
    void allFourConnectionsAllPlaceDoors() {
        ZoneCell[][] zones = solid();
        new DoorPass().apply(zones, EnumSet.allOf(Direction.class));
        int midX = GenConfig.ZONE_W / 2;
        int midY = GenConfig.ZONE_H / 2;
        assertThat(zones[0][midY].base).isEqualTo(ZoneBase.DOOR);
        assertThat(zones[GenConfig.ZONE_W - 1][midY].base).isEqualTo(ZoneBase.DOOR);
        assertThat(zones[midX][0].base).isEqualTo(ZoneBase.DOOR);
        assertThat(zones[midX][GenConfig.ZONE_H - 1].base).isEqualTo(ZoneBase.DOOR);
    }

    // -------------------------------------------------------------------------

    private static ZoneCell[][] solid() {
        return new SolidFillPass().apply();
    }
}
