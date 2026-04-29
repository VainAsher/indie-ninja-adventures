package com.indieniinja.world;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

class RoomTemplateCatalogTest {

    @TempDir
    Path tempDir;

    @Test
    void weightedCatalogSelectsDeterministicExistingVariant() throws Exception {
        Path root = tempDir.resolve("templates");
        Files.createDirectories(root);
        Files.writeString(root.resolve("start.tmx"), "base");
        Files.writeString(root.resolve("start_alt.tmx"), "alt");
        Path catalogPath = tempDir.resolve("room_template_catalog.json");
        Files.writeString(catalogPath, """
            {
              "roomTypes": {
                "start": [
                  { "file": "start.tmx", "weight": 1 },
                  { "file": "start_alt.tmx", "weight": 2 }
                ]
              }
            }
            """);

        RoomTemplateCatalog catalog = RoomTemplateCatalog.load(catalogPath);

        assertThat(catalog.selectTemplate("start", 0L, root)).contains(root.resolve("start.tmx"));
        assertThat(catalog.selectTemplate("start", 1L, root)).contains(root.resolve("start_alt.tmx"));
        assertThat(catalog.selectTemplate("start", 2L, root)).contains(root.resolve("start_alt.tmx"));
    }

    @Test
    void missingCatalogFallsBackToExactTemplateAndSortedConventionVariants() throws Exception {
        Path root = tempDir.resolve("templates");
        Files.createDirectories(root);
        Files.writeString(root.resolve("shop.tmx"), "base");
        Files.writeString(root.resolve("shop_b.tmx"), "b");
        Files.writeString(root.resolve("shop_a.tmx"), "a");

        RoomTemplateCatalog catalog = RoomTemplateCatalog.load(tempDir.resolve("missing.json"));

        assertThat(catalog.selectTemplate("shop", 0L, root)).contains(root.resolve("shop.tmx"));
        assertThat(catalog.selectTemplate("shop", 1L, root)).contains(root.resolve("shop_a.tmx"));
        assertThat(catalog.selectTemplate("shop", 2L, root)).contains(root.resolve("shop_b.tmx"));
    }

    @Test
    void missingTemplateReturnsEmpty() throws Exception {
        Path root = tempDir.resolve("templates");
        Files.createDirectories(root);

        RoomTemplateCatalog catalog = RoomTemplateCatalog.load(tempDir.resolve("missing.json"));

        Optional<Path> selected = catalog.selectTemplate("boss", 10L, root);

        assertThat(selected).isEmpty();
    }
}
