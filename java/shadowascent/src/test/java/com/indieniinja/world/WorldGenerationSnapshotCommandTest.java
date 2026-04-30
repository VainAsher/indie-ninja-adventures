package com.indieniinja.world;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;

class WorldGenerationSnapshotCommandTest {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    @TempDir
    Path tempDir;

    @Test
    void snapshotExportIsByteIdenticalForSameInputs() throws Exception {
        Path first = tempDir.resolve("first.json");
        Path second = tempDir.resolve("second.json");

        WorldGenerationSnapshotCommand.writeSnapshot(12345L, 12, WorldGraph.WorldShape.BLOB, first);
        WorldGenerationSnapshotCommand.writeSnapshot(12345L, 12, WorldGraph.WorldShape.BLOB, second);

        assertThat(Files.readString(first)).isEqualTo(Files.readString(second));
    }

    @Test
    void snapshotIncludesSchemaSeedStreamsAndRoomChecksums() throws Exception {
        Path out = tempDir.resolve("snapshot.json");

        WorldGenerationSnapshotCommand.writeSnapshot(777L, 10, WorldGraph.WorldShape.BRANCHY, out);

        JsonNode root = MAPPER.readTree(out.toFile());
        assertThat(root.get("generatorSchemaVersion").asInt()).isEqualTo(GeneratorSchemaVersion.CURRENT);
        assertThat(root.get("worldSeed").asLong()).isEqualTo(777L);
        assertThat(root.get("shape").asText()).isEqualTo("BRANCHY");
        assertThat(root.get("seedStreams").get(0).asText()).isEqualTo("world_graph");
        assertThat(root.get("rooms")).hasSize(root.get("roomCountActual").asInt());
        assertThat(root.get("rooms").get(0).hasNonNull("tileChecksum")).isTrue();
        assertThat(root.get("progressionGraph").get("centralHubId").asText()).isEqualTo("central_hub");
        assertThat(root.get("progressionGraph").get("criticalPath")).isNotEmpty();
        assertThat(root.get("sectionTemplates").get("templateCount").asInt()).isGreaterThanOrEqualTo(1);
        assertThat(root.get("sectionTemplates").get("templates").get(0).hasNonNull("id")).isTrue();
        assertThat(root.get("hybridLayout").get("assignments")).isNotEmpty();
        assertThat(root.get("hybridLayout").get("connections")).isNotEmpty();
    }
}
