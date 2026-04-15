#!/usr/bin/env python3
"""Docs freshness checker.

Usage:
  python tools/check_docs_freshness.py [--strict] [--emit-report] [--version <x.y.z>]
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

REQUIRED_FIELDS = [
    "doc_type",
    "status",
    "owner",
    "last_updated",
    "version_anchor",
]

PLAN_STATUSES = {"developing", "implementing", "completed", "archived"}
GENERAL_STATUSES = PLAN_STATUSES | {"living", "historical"}


@dataclass
class Finding:
    level: str
    code: str
    message: str
    path: Path | None = None


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_version(root: Path) -> str:
    payload = json.loads((root / "version.json").read_text(encoding="utf-8"))
    version = str(payload.get("version", "")).strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise RuntimeError(f"Invalid version in version.json: {version!r}")
    return version


def parse_frontmatter(text: str) -> dict[str, str]:
    normalized = text.lstrip("\ufeff")
    if not normalized.startswith("---\n"):
        return {}
    end = normalized.find("\n---\n", 4)
    if end == -1:
        return {}
    block = normalized[4:end]
    result: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()
    return result


def living_docs(root: Path) -> list[Path]:
    docs = root / "docs"
    paths: list[Path] = []

    top_level = [
        "INDEX.md",
        "CURRENT_STATE.md",
        "CHANGELOG.md",
        "ROADMAP.md",
        "GDD.md",
        "PLAYER_EXPECTATIONS.md",
        "RELEASE_VERSION_SYNC_CHECKLIST.md",
        "DEVLOG.md",
        "HANDOVER.md",
    ]
    for rel in top_level:
        p = docs / rel
        if p.exists():
            paths.append(p)

    for pattern in (
        "plans/developing/*.md",
        "plans/implementing/*.md",
        "plans/completed/*.md",
        "devlog/*.md",
    ):
        paths.extend(sorted(docs.glob(pattern)))

    for rel in (
        "workflow/ITERATION_RELEASE_PROTOCOL.md",
        "workflow/RELEASE_CHECKLIST.md",
        "workflow/SPRINT_WORKFLOW.md",
        "operations/CI_CD_PLAN.md",
    ):
        p = docs / rel
        if p.exists():
            paths.append(p)

    return sorted({p.resolve() for p in paths})


def parse_last_updated(value: str) -> datetime | None:
    v = value.strip()
    if not v:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S %z"):
        try:
            dt = datetime.strptime(v, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(v)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def check_metadata(root: Path, docs: Iterable[Path], expected_version: str) -> list[Finding]:
    findings: list[Finding] = []
    now = datetime.now(timezone.utc)

    for path in docs:
        rel = path.relative_to(root)
        text = path.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(text)

        if not fm:
            findings.append(Finding("warn", "missing_frontmatter", "Missing metadata frontmatter", rel))
            continue

        missing = [f for f in REQUIRED_FIELDS if not fm.get(f)]
        if missing:
            findings.append(
                Finding(
                    "warn",
                    "missing_required_metadata",
                    f"Missing metadata fields: {', '.join(missing)}",
                    rel,
                )
            )

        status = fm.get("status", "")
        if status and status not in GENERAL_STATUSES:
            findings.append(Finding("warn", "invalid_status", f"Unknown status '{status}'", rel))

        if "/docs/plans/" in str(path).replace("\\", "/"):
            if status not in PLAN_STATUSES:
                findings.append(
                    Finding("warn", "plan_status_invalid", f"Plan status must be one of {sorted(PLAN_STATUSES)}", rel)
                )

            normalized = str(rel).replace("\\", "/")
            if "/developing/" in normalized and status != "developing":
                findings.append(Finding("warn", "plan_folder_status_mismatch", "Plan in developing folder must have status=developing", rel))
            if "/implementing/" in normalized and status != "implementing":
                findings.append(Finding("warn", "plan_folder_status_mismatch", "Plan in implementing folder must have status=implementing", rel))
            if "/completed/" in normalized and status != "completed":
                findings.append(Finding("warn", "plan_folder_status_mismatch", "Plan in completed folder must have status=completed", rel))

        dt = parse_last_updated(fm.get("last_updated", ""))
        if dt is None:
            findings.append(Finding("warn", "invalid_last_updated", "Unable to parse last_updated", rel))
        else:
            age_days = (now - dt.astimezone(timezone.utc)).days
            if age_days > 45:
                findings.append(Finding("warn", "stale_doc", f"Document appears stale ({age_days} days old)", rel))

    canonical = {
        root / "README.md",
        root / "docs" / "ROADMAP.md",
        root / "docs" / "CHANGELOG.md",
        root / "docs" / "CURRENT_STATE.md",
    }

    for path in canonical:
        if not path.exists():
            findings.append(Finding("warn", "missing_canonical_doc", "Canonical file missing", path.relative_to(root)))
            continue

        if path.name == "README.md":
            text = path.read_text(encoding="utf-8", errors="replace")
            match = re.search(r"Version:\s*\*\*v(\d+\.\d+\.\d+)\*\*", text)
            if not match:
                findings.append(Finding("warn", "readme_version_missing", "README version banner missing", path.relative_to(root)))
            elif match.group(1) != expected_version:
                findings.append(
                    Finding(
                        "warn",
                        "version_anchor_mismatch",
                        f"README banner v{match.group(1)} != v{expected_version}",
                        path.relative_to(root),
                    )
                )
            continue

        text = path.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(text)
        anchor = fm.get("version_anchor", "")
        if anchor != f"v{expected_version}":
            findings.append(
                Finding(
                    "warn",
                    "version_anchor_mismatch",
                    f"version_anchor '{anchor}' != 'v{expected_version}'",
                    path.relative_to(root),
                )
            )

    return findings


def check_index_links(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    index_path = root / "docs" / "INDEX.md"
    if not index_path.exists():
        return [Finding("warn", "missing_index", "docs/INDEX.md is missing", Path("docs/INDEX.md"))]

    text = index_path.read_text(encoding="utf-8", errors="replace")
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    for raw in links:
        link = raw.strip()
        if not link or link.startswith("http") or link.startswith("mailto:"):
            continue
        if link.startswith("#"):
            continue

        target = link.split("#", 1)[0]
        resolved = (index_path.parent / target).resolve()
        if not resolved.exists():
            findings.append(
                Finding(
                    "warn",
                    "broken_index_link",
                    f"Broken link target: {link}",
                    index_path.relative_to(root),
                )
            )

    return findings


def check_root_plan_files(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    docs_root = root / "docs"
    legacy_patterns = ["PLAN_*.md", "*_plan.md"]
    for pattern in legacy_patterns:
        for path in docs_root.glob(pattern):
            findings.append(
                Finding(
                    "warn",
                    "plan_not_categorized",
                    "Plan file should be under docs/plans/{developing,implementing,completed}",
                    path.relative_to(root),
                )
            )
    return findings


def format_report(expected_version: str, findings: list[Finding], checked: list[Path], generated_at: datetime) -> str:
    warnings = [f for f in findings if f.level == "warn"]
    status = "PASS" if not warnings else "WARN"

    lines = [
        "# Docs Freshness Report",
        "",
        f"- Generated: {generated_at.isoformat()}",
        f"- Version anchor target: v{expected_version}",
        f"- Documents checked: {len(checked)}",
        f"- Status: {status}",
        "",
    ]

    if not warnings:
        lines.append("No warnings found.")
        return "\n".join(lines) + "\n"

    lines.append("## Warnings")
    lines.append("")
    for f in warnings:
        location = f" ({f.path.as_posix()})" if f.path else ""
        lines.append(f"- [{f.code}] {f.message}{location}")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check docs freshness and metadata.")
    parser.add_argument("--strict", action="store_true", help="Return non-zero when warnings exist")
    parser.add_argument("--emit-report", action="store_true", help="Write docs/reports/docs_freshness_report.md")
    parser.add_argument("--version", default=None, help="Expected version, e.g. 0.11.45")
    args = parser.parse_args()

    root = repo_root()
    expected = args.version or load_version(root)
    if expected.startswith("v"):
        expected = expected[1:]

    docs = living_docs(root)
    findings: list[Finding] = []
    findings.extend(check_metadata(root, docs, expected))
    findings.extend(check_index_links(root))
    findings.extend(check_root_plan_files(root))

    report = format_report(expected, findings, docs, datetime.now(timezone.utc))
    if args.emit_report:
        report_path = root / "docs" / "reports" / "docs_freshness_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")

    print(report)

    has_warn = any(f.level == "warn" for f in findings)
    if args.strict and has_warn:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
