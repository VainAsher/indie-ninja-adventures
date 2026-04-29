package com.indieniinja.world;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Random;

import static org.assertj.core.api.Assertions.assertThat;

class ZonePatchTemplateLibraryTest {

    @TempDir
    Path tempDir;

    @Test
    void loadsEightByEightTmxPatchFromCatalog() throws Exception {
        Path root = tempDir.resolve("zone_templates");
        Files.createDirectories(root.resolve("fill"));
        writeTmx(root.resolve("fill/solid.tmx"), 1);
        Path catalogPath = tempDir.resolve("zone_template_catalog.json");
        Files.writeString(catalogPath, """
            {
              "roles": {
                "fill": {
                  "fallbackWeight": 0,
                  "templates": [
                    { "file": "fill/solid.tmx", "weight": 1 }
                  ]
                }
              }
            }
            """);

        ZonePatchTemplateLibrary catalog = ZonePatchTemplateLibrary.load(catalogPath, root);

        byte[][] patch = catalog.pick(ZonePlanner.FILL, 0, new Random(7L)).orElseThrow();
        assertThat(patch).hasDimensions(8, 8);
        assertThat(patch[0][0]).isEqualTo(WorldGenerator.SOLID);
        assertThat(patch[7][7]).isEqualTo(WorldGenerator.SOLID);
    }

    @Test
    void fallbackWeightCanReturnEmptySoLegacyPoolStillMixesIn() throws Exception {
        Path root = tempDir.resolve("zone_templates");
        Files.createDirectories(root.resolve("plat"));
        writeTmx(root.resolve("plat/bar.tmx"), 2);
        Path catalogPath = tempDir.resolve("zone_template_catalog.json");
        Files.writeString(catalogPath, """
            {
              "roles": {
                "plat": {
                  "fallbackWeight": 100,
                  "templates": [
                    { "file": "plat/bar.tmx", "weight": 1 }
                  ]
                }
              }
            }
            """);

        ZonePatchTemplateLibrary catalog = ZonePatchTemplateLibrary.load(catalogPath, root);

        assertThat(catalog.pick(ZonePlanner.PLAT, 0, new Random(0L))).isEmpty();
    }

    @Test
    void zoneTemplateLibraryUsesAuthoredPatchBeforeLegacyFallback() throws Exception {
        Path root = tempDir.resolve("zone_templates");
        Files.createDirectories(root.resolve("plat"));
        writeTmx(root.resolve("plat/full.tmx"), 2);
        Path catalogPath = tempDir.resolve("zone_template_catalog.json");
        Files.writeString(catalogPath, """
            {
              "roles": {
                "plat": {
                  "fallbackWeight": 0,
                  "templates": [
                    { "file": "plat/full.tmx", "weight": 1 }
                  ]
                }
              }
            }
            """);

        ZonePatchTemplateLibrary authored = ZonePatchTemplateLibrary.load(catalogPath, root);

        byte[][] patch = ZoneTemplateLibrary.pick(ZonePlanner.PLAT, 0, new Random(99L), authored);

        for (byte[] row : patch) {
            assertThat(row).containsOnly(WorldGenerator.PLATFORM);
        }
    }

    private static void writeTmx(Path path, int gid) throws Exception {
        StringBuilder csv = new StringBuilder();
        for (int i = 0; i < 64; i++) {
            if (i > 0) {
                csv.append(',');
            }
            csv.append(gid);
        }
        Files.writeString(path, """
            <?xml version="1.0" encoding="UTF-8"?>
            <map version="1.10" tiledversion="1.10.2" orientation="orthogonal" renderorder="right-down" width="8" height="8" tilewidth="16" tileheight="16" infinite="0">
             <layer id="1" name="terrain" width="8" height="8">
              <data encoding="csv">
            %s
              </data>
             </layer>
            </map>
            """.formatted(csv));
    }
}
