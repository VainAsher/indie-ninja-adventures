package com.indieniinja.network;

import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class NPCStateTest {

    @Test
    void toMapFromMapRoundTripKeepsDimensions() {
        NPCState src = new NPCState();
        src.npcId = "hub_npc_1";
        src.npcType = "siren";
        src.x = 128f;
        src.y = 320f;
        src.width = 48;
        src.height = 72;
        src.facing = -1;
        src.animState = "walk";
        src.isInteractable = true;

        NPCState decoded = NPCState.fromMap(src.toMap());

        assertThat(decoded.npcId).isEqualTo(src.npcId);
        assertThat(decoded.npcType).isEqualTo(src.npcType);
        assertThat(decoded.x).isEqualTo(src.x);
        assertThat(decoded.y).isEqualTo(src.y);
        assertThat(decoded.width).isEqualTo(48);
        assertThat(decoded.height).isEqualTo(72);
        assertThat(decoded.facing).isEqualTo(src.facing);
        assertThat(decoded.animState).isEqualTo(src.animState);
        assertThat(decoded.isInteractable).isEqualTo(src.isInteractable);
    }

    @Test
    void fromMapFallsBackToNewNpcDimensionDefaultsWhenMissing() {
        NPCState decoded = NPCState.fromMap(Map.of(
            "npc_id", "legacy_npc",
            "npc_type", "lore",
            "x", 0f,
            "y", 0f
        ));

        assertThat(decoded.width).isEqualTo(48);
        assertThat(decoded.height).isEqualTo(72);
    }
}
