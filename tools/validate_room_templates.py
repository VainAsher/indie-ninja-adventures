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
import json
import xml.etree.ElementTree as ET
from pathlib import Path

REQUIRED_TEMPLATES = {"boss", "shop", "start", "exit"}
EXPECTED_WIDTH = 128
EXPECTED_HEIGHT = 128
VALID_GIDS = set(range(9))  # 0-8 match WorldGenerator byte constants

GID_NAMES = {
    0: "AIR",
    1: "SOLID",
    2: "PLATFORM",
    3: "ICE",
    4: "WATER",
    5: "LAVA",
    6: "DOOR_LOCKED",
    7: "GAS",
    8: "CLIMBABLE",
}

DEFAULT_GEOMETRY_RULES = {
    "roomWidthTiles": EXPECTED_WIDTH,
    "roomHeightTiles": EXPECTED_HEIGHT,
    "edgeWallThickness": 1,
    "floorThickness": 2,
    "doorHalfSpan": 5,
    "horizontalDoorDepth": 4,
    "verticalDoorDepth": 2,
}


def validate_template_catalog(catalog_path: Path, template_dir: Path) -> list[str]:
    """Validate weighted template catalog entries against a template directory."""
    if not catalog_path.exists():
        return [f"Catalog file not found: {catalog_path}"]
    try:
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Catalog parse error: {exc}"]

    errors: list[str] = []
    room_types = raw.get("roomTypes")
    if not isinstance(room_types, dict):
        return ["Catalog missing object field: roomTypes"]

    for room_id, entries in sorted(room_types.items()):
        if not isinstance(entries, list) or not entries:
            errors.append(f"Catalog entry {room_id} must be a non-empty list")
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                errors.append(f"Catalog entry {room_id} contains a non-object variant")
                continue
            file_name = entry.get("file")
            if not isinstance(file_name, str) or not file_name.strip():
                errors.append(f"Catalog entry {room_id} has missing file")
                continue
            weight = entry.get("weight", 1)
            if not isinstance(weight, int) or weight < 1:
                errors.append(f"Catalog entry {room_id} -> {file_name} has invalid weight {weight}")
            if Path(file_name).is_absolute() or ".." in Path(file_name).parts:
                errors.append(f"Catalog entry {room_id} -> {file_name} must stay inside template dir")
                continue
            if not (template_dir / file_name).exists():
                errors.append(f"Catalog entry {room_id} -> {file_name} does not exist")

    return errors


def load_geometry_rules(path: Path | None) -> dict[str, int]:
    rules = dict(DEFAULT_GEOMETRY_RULES)
    if path is None or not path.exists():
        return rules
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return rules
    for key, default in DEFAULT_GEOMETRY_RULES.items():
        value = raw.get(key, default)
        if isinstance(value, int):
            rules[key] = max(1, value)
    return rules


def is_horizontal_door_corridor(col: int, width: int, rules: dict[str, int]) -> bool:
    return abs(col - width // 2) <= rules["doorHalfSpan"]


def is_vertical_door_corridor(row: int, height: int, rules: dict[str, int]) -> bool:
    return abs(row - height // 2) <= rules["doorHalfSpan"]


def is_standable(tile: int) -> bool:
    return tile in {1, 2, 3, 5, 6, 8}


def validate_geometry(gids: list[int], width: int, height: int, rules: dict[str, int]) -> list[str]:
    errors: list[str] = []
    edge = min(rules["edgeWallThickness"], width, height)
    floor = min(rules["floorThickness"], height)

    def tile(row: int, col: int) -> int:
        return gids[row * width + col]

    for r in range(edge):
        for c in range(width):
            if is_horizontal_door_corridor(c, width, rules):
                continue
            if tile(r, c) != 1:
                errors.append(f"Top wall gap at row {r}, col {c}")
                break
        if errors and errors[-1].startswith("Top wall gap"):
            break

    for r in range(height - floor, height):
        for c in range(width):
            if is_horizontal_door_corridor(c, width, rules):
                continue
            if tile(r, c) != 1:
                errors.append(f"Floor gap at row {r}, col {c}")
                break
        if errors and errors[-1].startswith("Floor gap"):
            break

    for c in range(edge):
        for r in range(height):
            if is_vertical_door_corridor(r, height, rules):
                continue
            if tile(r, c) != 1:
                errors.append(f"Left wall gap at row {r}, col {c}")
                break
        if errors and errors[-1].startswith("Left wall gap"):
            break

    for c in range(width - edge, width):
        for r in range(height):
            if is_vertical_door_corridor(r, height, rules):
                continue
            if tile(r, c) != 1:
                errors.append(f"Right wall gap at row {r}, col {c}")
                break
        if errors and errors[-1].startswith("Right wall gap"):
            break

    standable_count = 0
    for r in range(1, height):
        for c in range(width):
            if is_standable(tile(r, c)) and tile(r - 1, c) == 0:
                standable_count += 1
    if standable_count == 0:
        errors.append("No standable tile found (solid/platform with AIR above)")

    return errors


def validate_tmx(
    path: Path,
    strict_geometry: bool = False,
    geometry_rules: dict[str, int] | None = None,
) -> list[str]:
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
        width = int(root.get("width", 0))
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
        errors.append(f"Tile count {len(tokens)} — expected {expected_tiles} ({width}×{height})")

    gids: list[int] = []
    non_air = 0
    for i, tok in enumerate(tokens):
        try:
            gid = int(tok)
        except ValueError:
            errors.append(f"Non-integer tile value at index {i}: '{tok}'")
            continue
        gids.append(gid)
        if gid not in VALID_GIDS:
            errors.append(f"Invalid GID {gid} at index {i} — valid range is 0-8")
        if gid != 0:
            non_air += 1

    if strict_geometry and not errors:
        errors.extend(validate_geometry(gids, width, height, geometry_rules or DEFAULT_GEOMETRY_RULES))

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
    parser.add_argument(
        "--strict-geometry",
        action="store_true",
        help="Also enforce wall/floor geometry rules with standard door-corridor exemptions",
    )
    parser.add_argument(
        "--rules",
        default="data/room_geometry_rules.json",
        help="JSON file containing geometry rule overrides (default: data/room_geometry_rules.json)",
    )
    parser.add_argument(
        "--catalog",
        default=None,
        help="Optional room template catalog JSON to validate against --dir",
    )
    args = parser.parse_args()
    geometry_rules = load_geometry_rules(Path(args.rules))

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
        errors = validate_tmx(path, args.strict_geometry, geometry_rules)
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

    if args.catalog:
        catalog_errors = validate_template_catalog(Path(args.catalog), template_dir)
        if catalog_errors:
            all_valid = False
            print(f"FAIL  {args.catalog}")
            for err in catalog_errors:
                print(f"      - {err}")
        else:
            print(f"OK    {args.catalog}")

    if all_valid:
        print(f"\nAll {len(tmx_files)} template(s) valid.")
    else:
        print(f"\nValidation failed.")
    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())
