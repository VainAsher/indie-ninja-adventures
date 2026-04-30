import argparse
import csv
import html
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOM_COLORS = {
    "S": "#3fb950",
    "E": "#f85149",
    "B": "#d2a8ff",
    "$": "#f2cc60",
    "T": "#79c0ff",
    "P": "#a5d6ff",
    "#": "#8b949e",
    ".": "#161b22",
}


def read_snapshot(snapshot_path: Path) -> dict[str, Any]:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if not isinstance(snapshot, dict):
        raise ValueError(f"{snapshot_path} must contain a JSON object")
    return snapshot


def render_snapshot(snapshot_path: Path, out_dir: Path) -> list[Path]:
    snapshot = read_snapshot(snapshot_path)
    megamap = snapshot.get("megamap")
    lab_report = snapshot.get("labReport")
    if not isinstance(megamap, dict):
        raise ValueError(f"{snapshot_path} does not contain a megamap block")
    if not isinstance(lab_report, dict):
        raise ValueError(f"{snapshot_path} does not contain a labReport block")

    overlay_rows = list(megamap.get("overlayRows") or [])
    if not overlay_rows:
        raise ValueError(f"{snapshot_path} megamap.overlayRows is empty")

    out_dir.mkdir(parents=True, exist_ok=True)
    overlay_path = out_dir / "overlay.txt"
    metrics_path = out_dir / "metrics.json"
    svg_path = out_dir / "megamap.svg"
    index_path = out_dir / "index.html"

    overlay_path.write_text("\n".join(str(row) for row in overlay_rows) + "\n", encoding="utf-8")
    metrics = build_metrics(snapshot)
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    svg_path.write_text(render_svg([str(row) for row in overlay_rows], metrics), encoding="utf-8")
    index_path.write_text(render_html(metrics, lab_report), encoding="utf-8")

    return [index_path, svg_path, metrics_path, overlay_path]


def build_metrics(snapshot: dict[str, Any]) -> dict[str, Any]:
    megamap = snapshot.get("megamap") if isinstance(snapshot.get("megamap"), dict) else {}
    return {
        "generatorSchemaVersion": snapshot.get("generatorSchemaVersion"),
        "worldSeed": snapshot.get("worldSeed"),
        "shape": snapshot.get("shape"),
        "goldenSeedKey": megamap.get("goldenSeedKey"),
        "bounds": megamap.get("bounds", {}),
        "megamapMetrics": megamap.get("metrics", {}),
        "autotileSummary": megamap.get("autotileSummary", {}),
        "labReport": snapshot.get("labReport", {}),
    }


def render_svg(overlay_rows: list[str], metrics: dict[str, Any]) -> str:
    cell = 24
    padding = 12
    width_cells = max(len(row) for row in overlay_rows)
    height_cells = len(overlay_rows)
    width = width_cells * cell + padding * 2
    height = height_cells * cell + padding * 2 + 36
    title = html.escape(str(metrics.get("goldenSeedKey") or f"world seed {metrics.get('worldSeed')}"))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#0d1117"/>',
        f'<text x="{padding}" y="22" fill="#c9d1d9" font-family="monospace" '
        f'font-size="12">{title}</text>',
    ]
    for y, row in enumerate(overlay_rows):
        for x, symbol in enumerate(row):
            fill = ROOM_COLORS.get(symbol, ROOM_COLORS["#"])
            rect_x = padding + x * cell
            rect_y = padding + 24 + y * cell
            parts.append(
                f'<rect x="{rect_x}" y="{rect_y}" width="{cell - 2}" height="{cell - 2}" '
                f'fill="{fill}" stroke="#30363d" stroke-width="1"/>'
            )
            if symbol != ".":
                parts.append(
                    f'<text x="{rect_x + cell / 2:.1f}" y="{rect_y + cell / 2 + 4:.1f}" '
                    f'text-anchor="middle" fill="#0d1117" font-family="monospace" '
                    f'font-weight="700" font-size="12">{html.escape(symbol)}</text>'
                )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_html(metrics: dict[str, Any], lab_report: dict[str, Any]) -> str:
    seed = html.escape(str(metrics.get("worldSeed")))
    status = html.escape(str(lab_report.get("overallStatus", "unknown")))
    score = html.escape(str(lab_report.get("qualityScore", "unknown")))
    warning_counts = lab_report.get("warningCounts", {})
    warnings = json.dumps(warning_counts, indent=2, sort_keys=True)
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        "  <title>Worldgen Lab</title>\n"
        "  <style>\n"
        "    body { background: #0d1117; color: #c9d1d9; font-family: system-ui, sans-serif; margin: 24px; }\n"
        "    pre, code { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }\n"
        "    .metrics { display: flex; gap: 24px; flex-wrap: wrap; margin: 16px 0; }\n"
        "    .metric { border: 1px solid #30363d; border-radius: 6px; padding: 12px; min-width: 120px; }\n"
        "    img { image-rendering: pixelated; max-width: 100%; border: 1px solid #30363d; }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        f"  <h1>Worldgen Lab Seed {seed}</h1>\n"
        '  <div class="metrics">\n'
        f'    <div class="metric"><strong>Status</strong><br>{status}</div>\n'
        f'    <div class="metric"><strong>Quality</strong><br>{score}</div>\n'
        "  </div>\n"
        '  <img src="megamap.svg" alt="World megamap">\n'
        "  <h2>Warnings</h2>\n"
        f"  <pre>{html.escape(warnings)}</pre>\n"
        '  <p><a href="metrics.json">metrics.json</a> <a href="overlay.txt">overlay.txt</a></p>\n'
        "</body>\n"
        "</html>\n"
    )


def command_render(args: argparse.Namespace) -> int:
    written = render_snapshot(Path(args.snapshot), Path(args.out))
    for path in written:
        print(path)
    return 0


def command_batch(args: argparse.Namespace) -> int:
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    snapshot_dir = Path(args.snapshots) if args.snapshots else generate_snapshots(args, out_dir)
    records = load_snapshot_records(snapshot_dir)
    if not records:
        raise ValueError(f"{snapshot_dir} does not contain any snapshot JSON files")

    records.sort(key=lambda record: (record["qualityScore"], str(record["worldSeed"]), record["sourceFile"]))
    write_summary(records, out_dir)

    failures_dir = out_dir / "failures"
    failures_dir.mkdir(parents=True, exist_ok=True)
    for record in records[: max(args.failures, 0)]:
        render_snapshot(Path(record["sourcePath"]), failures_dir / failure_dir_name(record))

    print(out_dir / "summary.csv")
    print(out_dir / "summary.json")
    return 0


def generate_snapshots(args: argparse.Namespace, out_dir: Path) -> Path:
    if args.seeds is None or args.rooms is None or args.shape is None:
        raise ValueError("batch generated mode requires --seeds, --rooms, --shape, and --out")

    snapshots_dir = out_dir / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    repo_root = Path(__file__).resolve().parents[1]
    java_dir = repo_root / "java"
    gradle = java_dir / ("gradlew.bat" if sys.platform.startswith("win") else "gradlew")

    for seed in range(1, args.seeds + 1):
        snapshot_path = snapshots_dir / f"seed-{seed}.json"
        subprocess.run(
            [
                str(gradle),
                ":shadowascent:worldgenSnapshot",
                f"-Pseed={seed}",
                f"-Prooms={args.rooms}",
                f"-Pshape={args.shape}",
                f"-Pout={snapshot_path}",
                "--no-daemon",
            ],
            cwd=java_dir,
            check=True,
        )
    return snapshots_dir


def load_snapshot_records(snapshot_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for snapshot_path in sorted(snapshot_dir.glob("*.json")):
        snapshot = read_snapshot(snapshot_path)
        lab_report = snapshot.get("labReport")
        if not isinstance(lab_report, dict):
            raise ValueError(f"{snapshot_path} does not contain a labReport block")
        quality_score = lab_report.get("qualityScore")
        if not isinstance(quality_score, (int, float)):
            raise ValueError(f"{snapshot_path} labReport.qualityScore must be numeric")
        warning_counts = lab_report.get("warningCounts")
        if not isinstance(warning_counts, dict):
            warning_counts = {}
        records.append(
            {
                "worldSeed": snapshot.get("worldSeed"),
                "qualityScore": quality_score,
                "overallStatus": lab_report.get("overallStatus", "unknown"),
                "warningCountTotal": sum_numeric_values(warning_counts),
                "warningCounts": warning_counts,
                "sourceFile": snapshot_path.name,
                "sourcePath": str(snapshot_path),
            }
        )
    return records


def sum_numeric_values(values: dict[str, Any]) -> int | float:
    total: int | float = 0
    for value in values.values():
        if isinstance(value, (int, float)):
            total += value
    return total


def write_summary(records: list[dict[str, Any]], out_dir: Path) -> None:
    csv_path = out_dir / "summary.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "worldSeed",
                "qualityScore",
                "overallStatus",
                "warningCountTotal",
                "sourceFile",
            ],
        )
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "worldSeed": record["worldSeed"],
                    "qualityScore": record["qualityScore"],
                    "overallStatus": record["overallStatus"],
                    "warningCountTotal": record["warningCountTotal"],
                    "sourceFile": record["sourceFile"],
                }
            )

    json_path = out_dir / "summary.json"
    json_path.write_text(
        json.dumps({"snapshots": records}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def failure_dir_name(record: dict[str, Any]) -> str:
    seed = record.get("worldSeed")
    raw_name = str(seed) if seed is not None else Path(str(record["sourceFile"])).stem
    safe = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in raw_name)
    return safe or "snapshot"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render and batch Worldgen Lab snapshots.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    render = subparsers.add_parser("render", help="Render one snapshot to a static report.")
    render.add_argument("snapshot", help="Path to a worldgen snapshot JSON file.")
    render.add_argument("--out", required=True, help="Output directory.")
    render.set_defaults(func=command_render)

    batch = subparsers.add_parser("batch", help="Summarize and render low-quality snapshots.")
    source = batch.add_mutually_exclusive_group(required=True)
    source.add_argument("--snapshots", help="Directory containing snapshot JSON files.")
    source.add_argument("--seeds", type=int, help="Number of snapshots to generate before summarizing.")
    batch.add_argument("--rooms", type=int, help="Room count for generated snapshot mode.")
    batch.add_argument("--shape", help="World shape for generated snapshot mode.")
    batch.add_argument("--out", required=True, help="Output directory.")
    batch.add_argument("--failures", type=int, default=5, help="Number of worst snapshots to render.")
    batch.set_defaults(func=command_batch)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"worldgen_lab: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
