import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_worldgen_lab(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "tools/worldgen_lab.py", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )


def test_render_writes_html_svg_metrics_and_overlay(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(
        json.dumps(
            {
                "worldSeed": 123,
                "megamap": {"overlayRows": ["S.", ".E"], "rooms": [], "metrics": {"roomCount": 2}},
                "labReport": {
                    "overallStatus": "pass",
                    "qualityScore": 100,
                    "warningCounts": {},
                    "rooms": [],
                },
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out"

    result = run_worldgen_lab("render", str(snapshot), "--out", str(out))

    assert result.returncode == 0, result.stderr
    assert (out / "index.html").exists()
    assert (out / "megamap.svg").exists()
    assert (out / "metrics.json").exists()
    assert (out / "overlay.txt").exists()


def write_snapshot(path: Path, seed: int, quality_score: int, status: str = "pass") -> None:
    path.write_text(
        json.dumps(
            {
                "worldSeed": seed,
                "shape": "BLOB",
                "megamap": {"overlayRows": ["S.", ".E"], "rooms": [], "metrics": {"roomCount": 2}},
                "labReport": {
                    "overallStatus": status,
                    "qualityScore": quality_score,
                    "warningCounts": {},
                    "rooms": [],
                },
            }
        ),
        encoding="utf-8",
    )


def test_batch_sorts_summary_and_renders_lowest_quality_failures(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    write_snapshot(fixtures / "good.json", 100, 98)
    write_snapshot(fixtures / "bad.json", 200, 12, "fail")
    write_snapshot(fixtures / "middle.json", 300, 50)
    out = tmp_path / "batch"

    result = run_worldgen_lab("batch", "--snapshots", str(fixtures), "--out", str(out), "--failures", "2")

    assert result.returncode == 0, result.stderr
    assert (out / "summary.csv").exists()
    assert (out / "summary.json").exists()
    assert (out / "failures").exists()
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert [entry["worldSeed"] for entry in summary["snapshots"]] == [200, 300, 100]
    csv_lines = (out / "summary.csv").read_text(encoding="utf-8").splitlines()
    assert csv_lines[1].startswith("200,12,fail,")
    assert (out / "failures" / "200" / "index.html").exists()
    assert (out / "failures" / "300" / "index.html").exists()


def run_tests() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        test_render_writes_html_svg_metrics_and_overlay(Path(tmp))
    with tempfile.TemporaryDirectory() as tmp:
        test_batch_sorts_summary_and_renders_lowest_quality_failures(Path(tmp))


if __name__ == "__main__":
    run_tests()
