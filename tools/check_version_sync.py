#!/usr/bin/env python3
"""
Validate release version metadata parity.

Authoritative source: version.json["version"].

Checks:
- Optional git tag (if provided) matches version.json.
- java/build.gradle.kts subproject version matches version.json.
- README.md primary version banner matches version.json.
- docs/ROADMAP.md metadata line version matches version.json.
- docs/CHANGELOG.md latest version heading matches version.json.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise RuntimeError(f"Required file not found: {path}")


def _match_or_error(text: str, pattern: str, label: str) -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        raise RuntimeError(f"Could not parse {label}.")
    return match.group(1)


def _load_authoritative_version(root: Path) -> str:
    version_path = root / "version.json"
    try:
        payload = json.loads(_read_text(version_path))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {version_path}: {exc}") from exc

    version = str(payload.get("version", "")).strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise RuntimeError(
            f"version.json has invalid semantic version '{version}'. Expected N.N.N."
        )
    return version


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate version metadata synchronization.")
    parser.add_argument(
        "--tag",
        default=None,
        help="Optional git tag to validate, e.g. v0.11.34",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    errors: list[str] = []

    try:
        version = _load_authoritative_version(root)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1

    expected_tag = f"v{version}"

    if args.tag:
        tag = args.tag.strip()
        if not re.fullmatch(r"v0\.\d+\.\d+", tag):
            errors.append(
                (f"Invalid release tag '{tag}'. " "Only v0.<minor>.<patch> is allowed pre-alpha.")
            )
        if tag != expected_tag:
            errors.append(f"Tag mismatch: tag={tag} version.json={expected_tag}")

    gradle_text = _read_text(root / "java" / "build.gradle.kts")
    readme_text = _read_text(root / "README.md")
    roadmap_text = _read_text(root / "docs" / "ROADMAP.md")
    changelog_text = _read_text(root / "docs" / "CHANGELOG.md")

    gradle_version = _match_or_error(
        gradle_text,
        r'^\s*version\s*=\s*"([^"]+)"',
        "java/build.gradle.kts version",
    )
    if gradle_version != version:
        errors.append(
            (
                "Gradle version mismatch: "
                f"java/build.gradle.kts={gradle_version} version.json={version}"
            )
        )

    readme_version = _match_or_error(
        readme_text,
        r"Version:\s*\*\*v(\d+\.\d+\.\d+)\*\*",
        "README version banner",
    )
    if readme_version != version:
        errors.append(
            "README version mismatch: " f"README=v{readme_version} version.json={expected_tag}"
        )

    roadmap_version = _match_or_error(
        roadmap_text,
        r"^Last Updated:\s*[^|]+\|\s*Version:\s*v(\d+\.\d+\.\d+)\s*\|",
        "docs/ROADMAP.md metadata version",
    )
    if roadmap_version != version:
        errors.append(
            (
                "ROADMAP version mismatch: "
                f"docs/ROADMAP.md=v{roadmap_version} version.json={expected_tag}"
            )
        )

    changelog_latest = _match_or_error(
        changelog_text,
        r"^## \[(\d+\.\d+\.\d+)\]",
        "docs/CHANGELOG.md latest heading",
    )
    if changelog_latest != version:
        errors.append(
            (
                "CHANGELOG latest version mismatch: "
                f"docs/CHANGELOG.md={changelog_latest} version.json={version}"
            )
        )

    if errors:
        print("Version synchronization check failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    print(f"Version synchronization OK: v{version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
