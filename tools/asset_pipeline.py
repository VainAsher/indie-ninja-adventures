#!/usr/bin/env python3
"""
asset_pipeline.py — Shadow Ascent asset pipeline orchestrator.

Scans assets/ to build/update assets/asset_manifest.json, which catalogues
every asset file with its relative path, file size, and SHA-256 hash.

The manifest is consumed by:
  - The client's shadowJar task to ensure assets are up-to-date.
  - CI artifact uploads for change tracking.
  - Hot-reload tooling (DevConsole reload_anims compares against this).

Usage:
    python tools/asset_pipeline.py [--root assets] [--out assets/asset_manifest.json]
    python tools/asset_pipeline.py --check   # validate existing manifest (exit 1 if stale)

Exit codes:
    0 — manifest written or already up-to-date
    1 — manifest is stale (--check mode) or write error
"""

import sys
import os
import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime, timezone

IGNORE_PATTERNS = {".DS_Store", "Thumbs.db", "desktop.ini", "__pycache__"}
IGNORE_EXTS     = {".pyc", ".class"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_assets(root: Path) -> list[dict]:
    entries = []
    for abs_path in sorted(root.rglob("*")):
        if not abs_path.is_file():
            continue
        if abs_path.name in IGNORE_PATTERNS:
            continue
        if abs_path.suffix in IGNORE_EXTS:
            continue
        rel = abs_path.relative_to(root).as_posix()
        entries.append({
            "path":   rel,
            "size":   abs_path.stat().st_size,
            "sha256": sha256(abs_path),
        })
    return entries


def build_manifest(root: Path) -> dict:
    entries = scan_assets(root)
    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "root":      root.as_posix(),
        "count":     len(entries),
        "files":     entries,
    }


def check_manifest(manifest_path: Path, root: Path) -> bool:
    """Return True if manifest is up-to-date with current asset state."""
    if not manifest_path.exists():
        print("Manifest not found — stale.", file=sys.stderr)
        return False
    try:
        with open(manifest_path, encoding="utf-8") as f:
            existing = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Cannot read manifest: {e}", file=sys.stderr)
        return False

    current_files  = {e["path"]: e for e in scan_assets(root)}
    manifest_files = {e["path"]: e for e in existing.get("files", [])}

    added   = set(current_files) - set(manifest_files)
    removed = set(manifest_files) - set(current_files)
    changed = {
        p for p in current_files
        if p in manifest_files and current_files[p]["sha256"] != manifest_files[p]["sha256"]
    }

    if added or removed or changed:
        print(f"Manifest stale: +{len(added)} added, -{len(removed)} removed, ~{len(changed)} changed.")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Shadow Ascent asset pipeline.")
    parser.add_argument("--root",  default="assets",                  help="Asset root directory")
    parser.add_argument("--out",   default="assets/asset_manifest.json", help="Output manifest path")
    parser.add_argument("--check", action="store_true",
                        help="Check manifest currency without updating (exit 1 if stale)")
    args = parser.parse_args()

    root         = Path(args.root)
    manifest_path = Path(args.out)

    if not root.is_dir():
        print(f"ERROR: asset root not found: {root}", file=sys.stderr)
        return 1

    if args.check:
        ok = check_manifest(manifest_path, root)
        if ok:
            print("Manifest is up-to-date.")
        return 0 if ok else 1

    manifest = build_manifest(root)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    print(f"Asset manifest written: {manifest_path}  ({manifest['count']} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
