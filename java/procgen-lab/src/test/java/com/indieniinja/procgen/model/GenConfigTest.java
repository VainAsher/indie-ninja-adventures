package com.indieniinja.procgen.model;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class GenConfigTest {

    @Test
    void roomDimensionsAre128x128() {
        assertThat(GenConfig.ROOM_W).isEqualTo(128);
        assertThat(GenConfig.ROOM_H).isEqualTo(128);
    }

    @Test
    void zoneGridIsConsistentWithStampSize() {
        assertThat(GenConfig.ZONE_W * GenConfig.ZONE_SIZE).isEqualTo(GenConfig.ROOM_W);
        assertThat(GenConfig.ZONE_H * GenConfig.ZONE_SIZE).isEqualTo(GenConfig.ROOM_H);
    }

    @Test
    void stampSizeIs8() {
        assertThat(GenConfig.ZONE_SIZE).isEqualTo(8);
    }

    @Test
    void zoneGridIs16x16() {
        assertThat(GenConfig.ZONE_W).isEqualTo(16);
        assertThat(GenConfig.ZONE_H).isEqualTo(16);
    }
}
