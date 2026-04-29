import json
import tempfile
import unittest
from pathlib import Path

import validate_room_templates as validator


class TemplateCatalogValidationTest(unittest.TestCase):
    def test_catalog_reports_missing_template_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "templates"
            root.mkdir()
            catalog = Path(tmp) / "room_template_catalog.json"
            catalog.write_text(
                json.dumps({"roomTypes": {"start": [{"file": "missing.tmx", "weight": 1}]}}),
                encoding="utf-8",
            )

            errors = validator.validate_template_catalog(catalog, root)

            self.assertEqual(errors, ["Catalog entry start -> missing.tmx does not exist"])

    def test_catalog_reports_non_positive_weight(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "templates"
            root.mkdir()
            (root / "start.tmx").write_text("<map />", encoding="utf-8")
            catalog = Path(tmp) / "room_template_catalog.json"
            catalog.write_text(
                json.dumps({"roomTypes": {"start": [{"file": "start.tmx", "weight": 0}]}}),
                encoding="utf-8",
            )

            errors = validator.validate_template_catalog(catalog, root)

            self.assertEqual(errors, ["Catalog entry start -> start.tmx has invalid weight 0"])

    def test_catalog_accepts_existing_weighted_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "templates"
            root.mkdir()
            (root / "start.tmx").write_text("<map />", encoding="utf-8")
            catalog = Path(tmp) / "room_template_catalog.json"
            catalog.write_text(
                json.dumps({"roomTypes": {"start": [{"file": "start.tmx", "weight": 2}]}}),
                encoding="utf-8",
            )

            errors = validator.validate_template_catalog(catalog, root)

            self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
