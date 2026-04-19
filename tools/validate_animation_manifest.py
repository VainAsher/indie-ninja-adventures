#!/usr/bin/env python3
"""
validate_animation_manifest.py — Validate assets/animations/manifest.json.

Checks:
  - JSON is well-formed
  - Top-level fields present: spriteWidth, spriteHeight, sets
  - Every set has: id, baseDir
  - Regular sets: entries array, each entry has key (str), file (str), frames (int >= 1)
  - Subset entries: totalFrames >= frames, offset >= 0, offset + frames <= totalFrames
  - enemy_sheet_batch sets: types array, each type has srcType, regType, frameCounts (list of ints)
  - No duplicate animation keys across all sets
  - spriteWidth and spriteHeight are positive integers

Exit codes:
  0 — manifest valid
  1 — one or more errors found
"""

import sys
import json
import argparse
from pathlib import Path

MANIFEST_DEFAULT = "assets/animations/manifest.json"


def validate(manifest_path: Path) -> list[str]:
    errors: list[str] = []

    if not manifest_path.exists():
        return [f"Manifest not found: {manifest_path}"]

    try:
        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"JSON parse error: {e}"]

    # Top-level fields
    for field in ("spriteWidth", "spriteHeight", "sets"):
        if field not in data:
            errors.append(f"Missing top-level field: '{field}'")

    w = data.get("spriteWidth")
    h = data.get("spriteHeight")
    if not isinstance(w, int) or w <= 0:
        errors.append(f"spriteWidth must be a positive integer, got: {w!r}")
    if not isinstance(h, int) or h <= 0:
        errors.append(f"spriteHeight must be a positive integer, got: {h!r}")

    sets = data.get("sets")
    if not isinstance(sets, list):
        errors.append("'sets' must be a list")
        return errors

    seen_keys: set[str] = set()

    for si, s in enumerate(sets):
        prefix = f"sets[{si}] (id={s.get('id', '?')!r})"

        if "id" not in s:
            errors.append(f"{prefix}: missing 'id'")
        if "baseDir" not in s:
            errors.append(f"{prefix}: missing 'baseDir'")

        set_type = s.get("type", "entries")

        if set_type == "enemy_sheet_batch":
            types = s.get("types")
            if not isinstance(types, list):
                errors.append(f"{prefix}: enemy_sheet_batch missing 'types' list")
                continue
            for ti, t in enumerate(types):
                tprefix = f"{prefix}.types[{ti}]"
                for field in ("srcType", "regType", "frameCounts"):
                    if field not in t:
                        errors.append(f"{tprefix}: missing '{field}'")
                fc = t.get("frameCounts")
                if not isinstance(fc, list) or not all(isinstance(x, int) and x >= 0 for x in fc):
                    errors.append(
                        f"{tprefix}: frameCounts must be list of non-negative ints, got {fc!r}"
                    )

        else:
            entries = s.get("entries")
            if not isinstance(entries, list):
                errors.append(f"{prefix}: missing 'entries' list")
                continue

            for ei, e in enumerate(entries):
                eprefix = f"{prefix}.entries[{ei}]"

                key = e.get("key")
                if not isinstance(key, str) or not key:
                    errors.append(f"{eprefix}: 'key' must be a non-empty string, got {key!r}")
                elif key in seen_keys:
                    errors.append(f"{eprefix}: duplicate animation key {key!r}")
                else:
                    seen_keys.add(key)

                if not isinstance(e.get("file"), str) or not e["file"]:
                    errors.append(f"{eprefix}: 'file' must be a non-empty string")

                frames = e.get("frames")
                if not isinstance(frames, int) or frames < 1:
                    errors.append(f"{eprefix}: 'frames' must be int >= 1, got {frames!r}")

                # Subset slice validation
                total = e.get("totalFrames")
                offset = e.get("offset")
                if total is not None or offset is not None:
                    if not isinstance(total, int) or total < 1:
                        errors.append(f"{eprefix}: 'totalFrames' must be int >= 1 when present")
                    if not isinstance(offset, int) or offset < 0:
                        errors.append(f"{eprefix}: 'offset' must be int >= 0 when present")
                    if (
                        isinstance(frames, int)
                        and isinstance(total, int)
                        and isinstance(offset, int)
                    ):
                        if offset + frames > total:
                            errors.append(
                                f"{eprefix}: offset({offset}) + frames({frames}) > totalFrames({total})"
                            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate animation manifest JSON.")
    parser.add_argument(
        "--manifest",
        default=MANIFEST_DEFAULT,
        help=f"Path to manifest (default: {MANIFEST_DEFAULT})",
    )
    args = parser.parse_args()

    errors = validate(Path(args.manifest))
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        print(f"\n{len(errors)} error(s) found — manifest invalid.", file=sys.stderr)
        return 1

    manifest_path = Path(args.manifest)
    with open(manifest_path, encoding="utf-8") as f:
        data = json.load(f)
    total_keys = sum(
        (
            len(s.get("entries", []))
            if s.get("type", "entries") != "enemy_sheet_batch"
            else len(s.get("types", []))
        )
        for s in data.get("sets", [])
    )
    print(f"Manifest valid: {len(data.get('sets', []))} sets, {total_keys} entries — zero errors.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
