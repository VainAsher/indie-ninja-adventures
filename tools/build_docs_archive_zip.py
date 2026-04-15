#!/usr/bin/env python3
"""Build docs archive ZIP snapshots under docs/archive/zips."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_version(root: Path) -> str:
    payload = json.loads((root / "version.json").read_text(encoding="utf-8"))
    version = str(payload.get("version", "")).strip()
    if not version:
        raise RuntimeError("version.json missing version")
    return version


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_zip(root: Path, version: str, date_str: str) -> Path:
    src = root / "docs" / "archive" / "retired"
    out_dir = root / "docs" / "archive" / "zips"
    out_dir.mkdir(parents=True, exist_ok=True)

    out_name = f"docs-archive-{date_str}-v{version}.zip"
    out_path = out_dir / out_name

    with ZipFile(out_path, "w", compression=ZIP_DEFLATED) as zf:
        if src.exists():
            for p in sorted(src.rglob("*")):
                if p.is_file():
                    zf.write(p, p.relative_to(root))

    return out_path


def prune_zips(root: Path, keep: int) -> None:
    out_dir = root / "docs" / "archive" / "zips"
    files = sorted(out_dir.glob("docs-archive-*-v*.zip"), key=lambda p: p.name)
    if len(files) <= keep:
        return
    for p in files[: len(files) - keep]:
        p.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build docs archive ZIP snapshot.")
    parser.add_argument("--version", default=None, help="Version override (x.y.z)")
    parser.add_argument("--date", default=None, help="Date override (YYYY-MM-DD)")
    parser.add_argument("--keep", type=int, default=6, help="How many ZIP snapshots to keep in repo")
    args = parser.parse_args()

    root = repo_root()
    version = (args.version or load_version(root)).lstrip("v")
    date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    out = build_zip(root, version, date_str)
    checksum = sha256(out)
    prune_zips(root, max(args.keep, 1))

    print(f"archive_zip={out.as_posix()}")
    print(f"archive_sha256={checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
