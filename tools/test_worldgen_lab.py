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
    zone_rows = ["D..............."] + ["................" for _ in range(15)]
    tile_rows = ["#" * 128, "#" + "." * 126 + "#"] + ["." * 128 for _ in range(126)]
    snapshot.write_text(
        json.dumps(
            {
                "worldSeed": 123,
                "megamap": {
                    "overlayRows": ["S.", ".E"],
                    "rooms": [
                        {"id": "0,0", "gridX": 0, "gridY": 0, "type": "start"},
                    ],
                    "metrics": {"roomCount": 2},
                },
                "labReport": {
                    "overallStatus": "pass",
                    "qualityScore": 100,
                    "warningCounts": {},
                    "zoneLegend": {"D": "door", ".": "walk"},
                    "tileLegend": {"#": "solid", ".": "air"},
                    "rooms": [
                        {
                            "roomKey": "0,0",
                            "roomType": "start",
                            "neighborDirs": ["up"],
                            "biomeIndex": 1,
                            "solidTiles": 130,
                            "platformTiles": 0,
                            "airTiles": 16254,
                            "zoneRows": zone_rows,
                            "tilePreviewRows": tile_rows,
                            "warnings": [],
                        }
                    ],
                },
                "progressionGraph": {
                    "centralHubId": "central_hub",
                    "criticalPath": ["central_hub", "forgotten_shrine"],
                    "nodes": [
                        {"id": "central_hub", "kind": "central_hub"},
                        {"id": "forgotten_shrine", "kind": "region_hub"},
                    ],
                },
                "hybridLayout": {
                    "assignments": [{"id": "central_hub", "gridX": 0, "gridY": 0}],
                    "connections": [{"from": "central_hub", "to": "forgotten_shrine"}],
                },
                "socketAnchorPlan": {
                    "connectionContracts": [{"id": "door_a"}],
                    "resolvedAnchors": [{"id": "spawn"}],
                },
                "validationReport": {
                    "valid": True,
                    "issueCount": 0,
                    "reachableCriticalAnchorCount": 1,
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
    assert (out / "world-detail.svg").exists()
    assert (out / "pipeline.svg").exists()
    assert (out / "pipeline.json").exists()
    assert (out / "metrics.json").exists()
    assert (out / "overlay.txt").exists()
    assert (out / "rooms" / "0_0.svg").exists()
    pipeline = json.loads((out / "pipeline.json").read_text(encoding="utf-8"))
    assert pipeline["act1Baseline"] is False
    assert pipeline["stages"][0]["name"] == "progressionGraph"


def write_snapshot(path: Path, seed: int, quality_score: int, status: str = "pass") -> None:
    zone_rows = ["D..............."] + ["................" for _ in range(15)]
    tile_rows = ["#" * 128, "#" + "." * 126 + "#"] + ["." * 128 for _ in range(126)]
    path.write_text(
        json.dumps(
            {
                "worldSeed": seed,
                "shape": "BLOB",
                "megamap": {
                    "overlayRows": ["S.", ".E"],
                    "rooms": [{"id": "0,0", "gridX": 0, "gridY": 0, "type": "start"}],
                    "metrics": {"roomCount": 2},
                },
                "rooms": [
                    {"id": "0,0", "gridX": 0, "gridY": 0, "type": "start", "tileChecksum": f"{seed:x}"}
                ],
                "labReport": {
                    "overallStatus": status,
                    "qualityScore": quality_score,
                    "warningCounts": {},
                    "zoneLegend": {"D": "door", ".": "walk"},
                    "tileLegend": {"#": "solid", ".": "air"},
                    "rooms": [
                        {
                            "roomKey": "0,0",
                            "roomType": "start",
                            "neighborDirs": ["up"],
                            "biomeIndex": 1,
                            "solidTiles": 130,
                            "platformTiles": 0,
                            "airTiles": 16254,
                            "zoneRows": zone_rows,
                            "tilePreviewRows": tile_rows,
                            "warnings": [],
                        }
                    ],
                },
                "progressionGraph": {"centralHubId": "central_hub", "criticalPath": ["central_hub"], "nodes": []},
                "hybridLayout": {"assignments": [], "connections": []},
                "socketAnchorPlan": {"connectionContracts": [], "resolvedAnchors": []},
                "validationReport": {"valid": status == "pass", "issueCount": 0},
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


def test_act1_renders_seed_420_baseline_from_existing_snapshot(tmp_path: Path) -> None:
    snapshot = tmp_path / "seed-420.json"
    write_snapshot(snapshot, 420, 100)
    out = tmp_path / "act1"

    result = run_worldgen_lab("act1", "--snapshot", str(snapshot), "--out", str(out))

    assert result.returncode == 0, result.stderr
    assert (out / "index.html").exists()
    assert (out / "snapshot.json").exists()
    pipeline = json.loads((out / "pipeline.json").read_text(encoding="utf-8"))
    assert pipeline["act1Baseline"] is True
    assert pipeline["worldSeed"] == 420


def test_compare_reports_quality_warning_and_room_checksum_deltas(tmp_path: Path) -> None:
    base = tmp_path / "base.json"
    candidate = tmp_path / "candidate.json"
    write_snapshot(base, 420, 80)
    write_snapshot(candidate, 420, 95)
    candidate_data = json.loads(candidate.read_text(encoding="utf-8"))
    candidate_data["rooms"][0]["tileChecksum"] = "changed"
    candidate_data["labReport"]["warningCounts"] = {"connected_down_edge_open_outside_door": 1}
    candidate.write_text(json.dumps(candidate_data), encoding="utf-8")
    out = tmp_path / "compare"

    result = run_worldgen_lab("compare", "--base", str(base), "--candidate", str(candidate), "--out", str(out))

    assert result.returncode == 0, result.stderr
    assert (out / "compare.html").exists()
    assert (out / "compare.csv").exists()
    report = json.loads((out / "compare.json").read_text(encoding="utf-8"))
    assert report["worldSeed"] == 420
    assert report["qualityDelta"] == 15
    assert report["roomChecksumChanges"] == 1
    assert report["warningDeltas"]["connected_down_edge_open_outside_door"] == 1


def run_tests() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        test_render_writes_html_svg_metrics_and_overlay(Path(tmp))
    with tempfile.TemporaryDirectory() as tmp:
        test_batch_sorts_summary_and_renders_lowest_quality_failures(Path(tmp))
    with tempfile.TemporaryDirectory() as tmp:
        test_act1_renders_seed_420_baseline_from_existing_snapshot(Path(tmp))
    with tempfile.TemporaryDirectory() as tmp:
        test_compare_reports_quality_warning_and_room_checksum_deltas(Path(tmp))


if __name__ == "__main__":
    run_tests()
