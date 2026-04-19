package com.indieniinja.content;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.networknt.schema.JsonSchema;
import com.networknt.schema.JsonSchemaFactory;
import com.networknt.schema.SpecVersion;
import com.networknt.schema.ValidationMessage;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Set;
import java.util.stream.Stream;

public class ContentLoader {

    private static final Logger log = LoggerFactory.getLogger(ContentLoader.class);

    private final Path dataRoot;
    private final ObjectMapper mapper = new ObjectMapper();
    private final JsonSchemaFactory schemaFactory = JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V7);

    public ContentLoader(Path dataRoot) {
        this.dataRoot = dataRoot;
    }

    /**
     * Load all definitions from data/entities/.
     * Populates registry in-place; throws ContentLoadException if any file fails schema validation.
     */
    public ContentRegistry loadAll() throws ContentLoadException {
        ContentRegistry registry = new ContentRegistry();
        loadAll(registry);
        return registry;
    }

    public void loadAll(ContentRegistry registry) throws ContentLoadException {
        loadEnemies(registry);
        loadNpcs(registry);
        loadRoomTypes(registry);
        log.info("[Content] Loaded: {} enemies, {} npcs, {} roomTypes",
            registry.enemyCount(), registry.npcCount(), registry.roomTypeCount());
    }

    public void reloadEnemies(ContentRegistry registry) throws ContentLoadException {
        loadEnemies(registry);
    }

    public void reloadNpcs(ContentRegistry registry) throws ContentLoadException {
        loadNpcs(registry);
    }

    public void reloadRoomTypes(ContentRegistry registry) throws ContentLoadException {
        loadRoomTypes(registry);
    }

    // ── Loaders ───────────────────────────────────────────────────────────────

    private void loadEnemies(ContentRegistry registry) throws ContentLoadException {
        JsonSchema schema = loadSchema("schemas/enemy_def_schema.json");
        Path dir = dataRoot.resolve("entities/enemies");
        try (Stream<Path> files = Files.walk(dir, 1)) {
            for (Path file : (Iterable<Path>) files.filter(p -> p.toString().endsWith(".json"))::iterator) {
                JsonNode node = parseAndValidate(file, schema);
                registry.registerEnemy(EnemyDefinition.fromJson(node));
            }
        } catch (IOException e) {
            throw new ContentLoadException("Failed scanning " + dir, e);
        }
    }

    private void loadNpcs(ContentRegistry registry) throws ContentLoadException {
        JsonSchema schema = loadSchema("schemas/npc_def_schema.json");
        Path dir = dataRoot.resolve("entities/npcs");
        try (Stream<Path> files = Files.walk(dir, 1)) {
            for (Path file : (Iterable<Path>) files.filter(p -> p.toString().endsWith(".json"))::iterator) {
                JsonNode node = parseAndValidate(file, schema);
                registry.registerNpc(NpcDefinition.fromJson(node));
            }
        } catch (IOException e) {
            throw new ContentLoadException("Failed scanning " + dir, e);
        }
    }

    private void loadRoomTypes(ContentRegistry registry) throws ContentLoadException {
        JsonSchema schema = loadSchema("schemas/room_type_schema.json");
        Path dir = dataRoot.resolve("entities/rooms/types");
        try (Stream<Path> files = Files.walk(dir, 1)) {
            for (Path file : (Iterable<Path>) files.filter(p -> p.toString().endsWith(".json"))::iterator) {
                JsonNode node = parseAndValidate(file, schema);
                registry.registerRoomType(RoomTypeDefinition.fromJson(node));
            }
        } catch (IOException e) {
            throw new ContentLoadException("Failed scanning " + dir, e);
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private JsonNode parseAndValidate(Path file, JsonSchema schema) throws ContentLoadException {
        try {
            JsonNode node = mapper.readTree(file.toFile());
            Set<ValidationMessage> errors = schema.validate(node);
            if (!errors.isEmpty()) {
                StringBuilder sb = new StringBuilder("Schema validation failed for ")
                    .append(file).append(":\n");
                errors.forEach(e -> sb.append("  ").append(e.getMessage()).append("\n"));
                throw new ContentLoadException(sb.toString());
            }
            return node;
        } catch (IOException e) {
            throw new ContentLoadException("Failed reading " + file, e);
        }
    }

    private JsonSchema loadSchema(String relativePath) throws ContentLoadException {
        Path schemaPath = dataRoot.resolve(relativePath);
        try (InputStream is = Files.newInputStream(schemaPath)) {
            return schemaFactory.getSchema(is);
        } catch (IOException e) {
            throw new ContentLoadException("Failed loading schema " + schemaPath, e);
        }
    }
}
