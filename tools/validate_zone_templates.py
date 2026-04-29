#!/usr/bin/env python3
"""Validate Shadow Ascent 8x8 Tiled zone patch templates."""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

VALID_GIDS = set(range(0, 9))


def validate_catalog(catalog_path: Path, template_dir: Path) -> list[str]:
    errors: list[str] = []
    if not catalog_path.exists():
        return [f"Catalog not found: {catalog_path}"]

    try:
        root = json.loads(catalog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"Catalog JSON parse error: {exc}"]

    roles = root.get("roles")
    if not isinstance(roles, dict):
        return ["Catalog must contain an object field named 'roles'"]

    resolved_root = template_dir.resolve()
    for role, role_data in roles.items():
        if not isinstance(role_data, dict):
            errors.append(f"Role {role!r} must be an object")
            continue

        fallback_weight = role_data.get("fallbackWeight", 0)
        if not isinstance(fallback_weight, int) or fallback_weight < 0:
            errors.append(
                f"Role {role!r} fallbackWeight must be a non-negative integer"
            )

        templates = role_data.get("templates", [])
        if not isinstance(templates, list):
            errors.append(f"Role {role!r} templates must be a list")
            continue

        for index, entry in enumerate(templates):
            if not isinstance(entry, dict):
                errors.append(f"Role {role!r} template #{index} must be an object")
                continue

            file_name = entry.get("file")
            if not isinstance(file_name, str) or not file_name.strip():
                errors.append(f"Role {role!r} template #{index} needs a non-empty file")
                continue

            weight = entry.get("weight", 1)
            if not isinstance(weight, int) or weight < 1:
                errors.append(f"Role {role!r} template {file_name} weight must be >= 1")

            candidate = (template_dir / file_name).resolve()
            if not candidate.is_relative_to(resolved_root):
                errors.append(
                    f"Role {role!r} template {file_name} must stay inside template dir"
                )
            elif not candidate.exists():
                errors.append(f"Role {role!r} template missing: {file_name}")

            biome_indexes = entry.get("biomeIndexes", [])
            if not isinstance(biome_indexes, list) or not all(
                isinstance(value, int) for value in biome_indexes
            ):
                errors.append(
                    f"Role {role!r} template {file_name} biomeIndexes must be integers"
                )

    return errors


def validate_tmx(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return [f"{path}: XML parse error: {exc}"]

    width = _int_attr(root, "width")
    height = _int_attr(root, "height")
    if width != 8 or height != 8:
        errors.append(f"{path}: map must be 8x8 tiles, got {width}x{height}")

    layers = root.findall("layer")
    terrain = next(
        (layer for layer in layers if layer.get("name", "").lower() == "terrain"), None
    )
    if terrain is None and layers:
        terrain = layers[0]
    if terrain is None:
        return errors + [f"{path}: no tile layer found"]

    data = terrain.find("data")
    if data is None:
        return errors + [f"{path}: terrain layer has no data element"]
    if data.get("encoding", "") not in ("", "csv"):
        errors.append(f"{path}: only CSV encoded terrain data is supported")

    tokens = [
        token.strip() for token in (data.text or "").replace("\r", "\n").split(",")
    ]
    gids: list[int] = []
    for token in tokens:
        if not token:
            continue
        for line_part in token.splitlines():
            line_part = line_part.strip()
            if not line_part:
                continue
            try:
                gid = int(line_part)
            except ValueError:
                errors.append(f"{path}: non-integer gid {line_part!r}")
                continue
            gids.append(gid)
            if gid not in VALID_GIDS:
                errors.append(f"{path}: unsupported gid {gid}; valid gids are 0-8")

    if len(gids) != 64:
        errors.append(f"{path}: expected 64 tile gids, found {len(gids)}")

    return errors


def _int_attr(element: ET.Element, name: str) -> int | None:
    try:
        return int(element.get(name, ""))
    except ValueError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Shadow Ascent zone patch templates."
    )
    parser.add_argument(
        "--dir",
        default="java/assets/rooms/zone_templates",
        help="Directory containing 8x8 .tmx zone patch templates.",
    )
    parser.add_argument(
        "--catalog",
        default="data/zone_template_catalog.json",
        help="Zone patch catalog JSON to validate against --dir.",
    )
    args = parser.parse_args()

    template_dir = Path(args.dir)
    if not template_dir.is_dir():
        print(f"ERROR: template directory not found: {template_dir}")
        return 1

    errors = validate_catalog(Path(args.catalog), template_dir)
    tmx_files = sorted(template_dir.rglob("*.tmx"))
    if not tmx_files:
        errors.append(f"No .tmx files found in {template_dir}")
    for tmx in tmx_files:
        errors.extend(validate_tmx(tmx))

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"All {len(tmx_files)} zone template(s) valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
