import json
import tempfile
import unittest
from pathlib import Path

import render_worldgen_snapshot as renderer


class WorldgenSnapshotRendererTest(unittest.TestCase):
    def test_render_bundle_writes_overlay_metrics_and_svg(self):
        snapshot = {
            "generatorSchemaVersion": 8,
            "worldSeed": 12345,
            "shape": "BLOB",
            "megamap": {
                "goldenSeedKey": "schema-8-seed-12345-shape-BLOB-rooms-3",
                "bounds": {"widthRooms": 3, "heightRooms": 2},
                "overlayRows": ["S#E", ".B."],
                "metrics": {
                    "roomCount": 4,
                    "seamCount": 3,
                    "stitchedTileCount": 98304,
                    "stampedTileCount": 65536,
                    "emptyTileCount": 32768,
                    "passableTileCount": 40000,
                    "solidTileCount": 20000,
                    "platformTileCount": 5000,
                    "hazardTileCount": 1,
                    "stitchedTileChecksum": "abc123",
                },
                "autotileSummary": {
                    "mode": "edge-mask-preview",
                    "solidLikeTileCount": 20000,
                    "solidEdgeMaskChecksum": "def456",
                },
            },
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "snapshot.json"
            out_dir = root / "bundle"
            source.write_text(json.dumps(snapshot), encoding="utf-8")

            written = renderer.render_bundle(source, out_dir)

            self.assertEqual(
                sorted(path.name for path in written),
                ["megamap.svg", "metrics.json", "overlay.txt"],
            )
            self.assertEqual((out_dir / "overlay.txt").read_text(encoding="utf-8"), "S#E\n.B.\n")
            metrics = json.loads((out_dir / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["goldenSeedKey"], "schema-8-seed-12345-shape-BLOB-rooms-3")
            self.assertIn("<svg", (out_dir / "megamap.svg").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
