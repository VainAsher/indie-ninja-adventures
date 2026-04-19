#!/usr/bin/env python3
"""
validate_room_templates.py — Shadow Ascent room template validator.

Checks that all .tmx files in assets/rooms/templates/ are well-formed and
compatible with TmxRoomLoader:
  - Valid XML
  - Correct map dimensions (128×128)
  - CSV encoding
  - Tile values in range [0, 8] (engine tile type codes)
  - At least one non-AIR tile (non-trivial content)

Usage:
    python tools/validate_room_templates.py [--dir assets/rooms/templates]

Exit codes:
    0 — all templates valid
    1 — one or more templates failed validation
"""

import sys
import os
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

REQUIRED_TEMPLATES = {"boss", "shop", "start", "exit"}
EXPECTED_WIDTH  = 128
EXPECTED_HEIGHT = 128
VALID_GIDS      = set(range(9))   # 0-8 match WorldGenerator byte constants

GID_NAMES = {
    0: "AIR", 1: "SOLID", 2: "PLATFORM", 3: "ICE",
    4: "WATER", 5: "LAVA", 6: "DOOR_LOCKED", 7: "GAS", 8: "CLIMBABLE",
}


def validate_tmx(path: Path) -> list[str]:
    """Return a list of error strings; empty list means the file is valid."""
    errors: list[str] = []

    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        return [f"XML parse error: {e}"]

    root = tree.getroot()
    if root.tag != "map":
        errors.append(f"Root element is <{root.tag}>, expected <map>")
        return errors

    try:
        width  = int(root.get("width",  0))
        height = int(root.get("height", 0))
    except ValueError:
        errors.append("Map width/height attributes are not integers")
        return errors

    if width != EXPECTED_WIDTH or height != EXPECTED_HEIGHT:
        errors.append(
            f"Map dimensions {width}×{height} — expected {EXPECTED_WIDTH}×{EXPECTED_HEIGHT}"
        )

    # Find terrain layer
    layers = root.findall("layer")
    terrain = next(
        (l for l in layers if l.get("name", "").lower() == "terrain"),
        layers[0] if layers else None,
    )
    if terrain is None:
        errors.append("No <layer> element found")
        return errors

    data_el = terrain.find("data")
    if data_el is None:
        errors.append("Layer has no <data> element")
        return errors

    encoding = data_el.get("encoding", "")
    if encoding not in ("", "csv"):
        errors.append(f"Unsupported encoding '{encoding}' — TmxRoomLoader requires CSV")
        return errors

    raw = (data_el.text or "").strip()
    tokens = [t.strip() for t in raw.replace("\n", ",").split(",") if t.strip()]
    expected_tiles = width * height

    if len(tokens) != expected_tiles:
        errors.append(
            f"Tile count {len(tokens)} — expected {expected_tiles} ({width}×{height})"
        )

    non_air = 0
    for i, tok in enumerate(tokens):
        try:
            gid = int(tok)
        except ValueError:
            errors.append(f"Non-integer tile value at index {i}: '{tok}'")
            continue
        if gid not in VALID_GIDS:
            errors.append(f"Invalid GID {gid} at index {i} — valid range is 0-8")
        if gid != 0:
            non_air += 1

    if non_air == 0:
        errors.append("Template is entirely AIR — no geometry authored")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Shadow Ascent room templates.")
    parser.add_argument(
        "--dir",
        default="assets/rooms/templates",
        help="Directory containing .tmx template files (default: assets/rooms/templates)",
    )
    args = parser.parse_args()

    template_dir = Path(args.dir)
    if not template_dir.is_dir():
        print(f"ERROR: template directory not found: {template_dir}")
        return 1

    tmx_files = sorted(template_dir.glob("*.tmx"))
    if not tmx_files:
        print(f"WARNING: no .tmx files found in {template_dir}")
        return 0

    all_valid = True
    found_ids: set[str] = set()

    for path in tmx_files:
        room_id = path.stem
        found_ids.add(room_id)
        errors = validate_tmx(path)
        if errors:
            all_valid = False
            print(f"FAIL  {path.name}")
            for err in errors:
                print(f"      - {err}")
        else:
            print(f"OK    {path.name}")

    missing = REQUIRED_TEMPLATES - found_ids
    if missing:
        for m in sorted(missing):
            print(f"MISSING  {m}.tmx — required template not found")
        all_valid = False

    if all_valid:
        print(f"\nAll {len(tmx_files)} template(s) valid.")
    else:
        print(f"\nValidation failed.")
    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())
