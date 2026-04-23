#!/usr/bin/env python3
"""
Run P0 critical regression commands and write a markdown report artifact.

Outputs:
- docs/reports/P0_REGRESSION_REPORT.md

Exit code:
- 0 when all checks pass
- 1 when any check fails
"""

from __future__ import annotations

import datetime as dt
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CheckResult:
    name: str
    command: list[str]
    cwd: Path
    elapsed_seconds: float
    return_code: int
    output_tail: str
    skipped: bool = False

    @property
    def status(self) -> str:
        if self.skipped:
            return "SKIP"
        return "PASS" if self.return_code == 0 else "FAIL"


def _gradle_command(root: Path) -> list[str]:
    if os.name == "nt":
        return [str(root / "java" / "gradlew.bat")]
    return [str(root / "java" / "gradlew")]


def _run_check(
    name: str,
    command: list[str],
    cwd: Path,
    env_overrides: dict[str, str] | None = None,
) -> CheckResult:
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)

    started = time.perf_counter()
    proc = subprocess.run(  # noqa: S603
        command,
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    elapsed = time.perf_counter() - started

    combined = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    tail_lines = [line for line in combined.splitlines() if line.strip()][-20:]
    output_tail = "\n".join(tail_lines) if tail_lines else "(no output)"

    return CheckResult(
        name=name,
        command=command,
        cwd=cwd,
        elapsed_seconds=elapsed,
        return_code=proc.returncode,
        output_tail=output_tail,
    )


def _render_report(results: list[CheckResult], generated_at: str) -> str:
    overall = "PASS" if all(r.return_code == 0 for r in results) else "FAIL"
    lines: list[str] = [
        "# P0 Regression Report",
        "",
        f"Generated: `{generated_at}`",
        f"Overall: **{overall}**",
        "",
        "## Summary",
        "",
        "| Check | Status | Duration (s) |",
        "|-------|--------|--------------|",
    ]

    for result in results:
        lines.append(f"| `{result.name}` | `{result.status}` | `{result.elapsed_seconds:.2f}` |")

    lines.extend(["", "## Details", ""])
    for result in results:
        cmd = " ".join(result.command)
        lines.extend(
            [
                f"### {result.name}",
                "",
                f"- Command: `{cmd}`",
                f"- Working directory: `{result.cwd}`",
                f"- Status: `{result.status}`",
                f"- Duration: `{result.elapsed_seconds:.2f}s`",
                "",
                "```text",
                result.output_tail,
                "```",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    generated_at = dt.datetime.now(dt.timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %z")

    gradle_user_home = str(root / ".gradle-local")
    checks: list[tuple[str, list[str], Path, dict[str, str] | None, Path | None]] = [
        (
            "Version Sync",
            [sys.executable, "tools/check_version_sync.py"],
            root,
            None,
            root / "tools" / "check_version_sync.py",
        ),
        (
            "Data Integrity",
            [sys.executable, "tests/test_data_integrity.py"],
            root,
            None,
            root / "tests" / "test_data_integrity.py",
        ),
        (
            "Java Server/Client Tests",
            _gradle_command(root)
            + [":server:test", ":client:test", "--console=plain", "--no-daemon"],
            root / "java",
            {"GRADLE_USER_HOME": gradle_user_home},
            root / "java" / "gradlew.bat" if os.name == "nt" else root / "java" / "gradlew",
        ),
    ]

    results: list[CheckResult] = []
    for name, command, cwd, env_overrides, required_path in checks:
        if required_path is not None and not required_path.exists():
            results.append(
                CheckResult(
                    name=name,
                    command=command,
                    cwd=cwd,
                    elapsed_seconds=0.0,
                    return_code=0,
                    output_tail=f"Skipped: required path not found: {required_path}",
                    skipped=True,
                )
            )
            print(f"[P0] skipping {name} (missing: {required_path})")
            continue
        print(f"[P0] running {name}...")
        results.append(_run_check(name, command, cwd, env_overrides))

    report_path = root / "docs" / "reports" / "P0_REGRESSION_REPORT.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render_report(results, generated_at), encoding="utf-8")
    print(f"[P0] wrote report: {report_path}")

    failures = [r for r in results if not r.skipped and r.return_code != 0]
    if failures:
        print("[P0] regression suite FAILED")
        for failure in failures:
            print(f"  - {failure.name} (exit {failure.return_code})")
        return 1

    print("[P0] regression suite PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
