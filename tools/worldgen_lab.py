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

ZONE_COLORS = {
    "?": "#6e7681",
    ".": "#202b36",
    "#": "#8b949e",
    "=": "#79c0ff",
    "D": "#f85149",
    " ": "#0d1117",
    "V": "#3fb950",
    "$": "#f2cc60",
    "T": "#d2a8ff",
    "v": "#ffa657",
    "C": "#7ee787",
    "+": "#a5d6ff",
    "^": "#ff7b72",
    "i": "#a5d6ff",
    "~": "#58a6ff",
    "!": "#ff00ff",
}

TILE_COLORS = {
    ".": "#0d1117",
    "#": "#8b949e",
    "=": "#79c0ff",
    "i": "#a5d6ff",
    "~": "#58a6ff",
    "^": "#f85149",
    "L": "#d2a8ff",
    "g": "#7ee787",
    "c": "#3fb950",
    "!": "#ff00ff",
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
    world_detail_path = out_dir / "world-detail.svg"
    index_path = out_dir / "index.html"
    rooms_dir = out_dir / "rooms"

    overlay_path.write_text("\n".join(str(row) for row in overlay_rows) + "\n", encoding="utf-8")
    metrics = build_metrics(snapshot)
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    svg_path.write_text(render_svg([str(row) for row in overlay_rows], metrics), encoding="utf-8")
    world_detail_path.write_text(render_world_detail_svg(snapshot, metrics), encoding="utf-8")
    room_paths = render_room_svgs(lab_report, rooms_dir)
    index_path.write_text(render_html(metrics, lab_report, room_paths), encoding="utf-8")

    return [index_path, svg_path, world_detail_path, metrics_path, overlay_path, *room_paths]


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


def render_html(metrics: dict[str, Any], lab_report: dict[str, Any], room_paths: list[Path] | None = None) -> str:
    seed = html.escape(str(metrics.get("worldSeed")))
    status = html.escape(str(lab_report.get("overallStatus", "unknown")))
    score = html.escape(str(lab_report.get("qualityScore", "unknown")))
    warning_counts = lab_report.get("warningCounts", {})
    warnings = json.dumps(warning_counts, indent=2, sort_keys=True)
    rooms = lab_report.get("rooms", [])
    rows = []
    if isinstance(rooms, list):
        for room in rooms:
            if not isinstance(room, dict):
                continue
            room_key = str(room.get("roomKey", "room"))
            href = f"rooms/{safe_room_filename(room_key)}.svg"
            rows.append(
                "<tr>"
                f'<td><a href="{html.escape(href)}">{html.escape(room_key)}</a></td>'
                f"<td>{html.escape(str(room.get('roomType', 'unknown')))}</td>"
                f"<td>{html.escape(','.join(str(d) for d in room.get('neighborDirs', [])))}</td>"
                f"<td>{html.escape(str(room.get('biomeIndex', '')))}</td>"
                f"<td>{html.escape(str(len(room.get('warnings', []))))}</td>"
                "</tr>"
            )
    room_table = "\n".join(rows)
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
        "    img { image-rendering: pixelated; max-width: 100%; border: 1px solid #30363d; background: #0d1117; }\n"
        "    table { border-collapse: collapse; margin-top: 16px; width: 100%; }\n"
        "    th, td { border: 1px solid #30363d; padding: 6px 8px; text-align: left; }\n"
        "    a { color: #79c0ff; }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        f"  <h1>Worldgen Lab Seed {seed}</h1>\n"
        '  <div class="metrics">\n'
        f'    <div class="metric"><strong>Status</strong><br>{status}</div>\n'
        f'    <div class="metric"><strong>Quality</strong><br>{score}</div>\n'
        "  </div>\n"
        "  <h2>Expanded World Detail</h2>\n"
        '  <img src="world-detail.svg" alt="Expanded world detail">\n'
        "  <h2>Macro Map</h2>\n"
        '  <img src="megamap.svg" alt="World megamap">\n'
        "  <h2>Rooms</h2>\n"
        "  <table><thead><tr><th>Room</th><th>Type</th><th>Dirs</th><th>Biome</th><th>Warnings</th></tr></thead>\n"
        f"  <tbody>{room_table}</tbody></table>\n"
        "  <h2>Warnings</h2>\n"
        f"  <pre>{html.escape(warnings)}</pre>\n"
        '  <p><a href="metrics.json">metrics.json</a> <a href="overlay.txt">overlay.txt</a></p>\n'
        "</body>\n"
        "</html>\n"
    )


def render_world_detail_svg(snapshot: dict[str, Any], metrics: dict[str, Any]) -> str:
    lab_report = snapshot.get("labReport") if isinstance(snapshot.get("labReport"), dict) else {}
    rooms = lab_report.get("rooms") if isinstance(lab_report.get("rooms"), list) else []
    megamap = snapshot.get("megamap") if isinstance(snapshot.get("megamap"), dict) else {}
    room_positions = room_positions_by_key(megamap, rooms)
    if not room_positions:
        return blank_svg("No room detail available", 480, 160)

    min_x = min(pos[0] for pos in room_positions.values())
    min_y = min(pos[1] for pos in room_positions.values())
    max_x = max(pos[0] for pos in room_positions.values())
    max_y = max(pos[1] for pos in room_positions.values())
    room_px = 88
    gap = 14
    pad = 18
    width = (max_x - min_x + 1) * (room_px + gap) + pad * 2
    height = (max_y - min_y + 1) * (room_px + gap) + pad * 2 + 28
    title = html.escape(str(metrics.get("goldenSeedKey") or f"world seed {metrics.get('worldSeed')}"))
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#0d1117"/>',
        f'<text x="{pad}" y="20" fill="#c9d1d9" font-family="monospace" font-size="12">{title}</text>',
    ]
    for room in rooms:
        if not isinstance(room, dict):
            continue
        key = str(room.get("roomKey", ""))
        if key not in room_positions:
            continue
        gx, gy = room_positions[key]
        x = pad + (gx - min_x) * (room_px + gap)
        y = pad + 28 + (gy - min_y) * (room_px + gap)
        warnings = room.get("warnings", [])
        stroke = "#f85149" if isinstance(warnings, list) and warnings else "#30363d"
        parts.append(f'<rect x="{x}" y="{y}" width="{room_px}" height="{room_px}" fill="#161b22" stroke="{stroke}" stroke-width="2"/>')
        parts.extend(tile_preview_rects(room.get("tilePreviewRows", []), x + 4, y + 14, 80, 80))
        parts.append(
            f'<text x="{x + 4}" y="{y + 10}" fill="#c9d1d9" font-family="monospace" font-size="8">'
            f'{html.escape(key)} {html.escape(str(room.get("roomType", ""))[:10])}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_room_svgs(lab_report: dict[str, Any], rooms_dir: Path) -> list[Path]:
    rooms = lab_report.get("rooms") if isinstance(lab_report.get("rooms"), list) else []
    rooms_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for room in rooms:
        if not isinstance(room, dict):
            continue
        path = rooms_dir / f"{safe_room_filename(str(room.get('roomKey', 'room')))}.svg"
        path.write_text(render_room_detail_svg(room, lab_report), encoding="utf-8")
        written.append(path)
    return written


def render_room_detail_svg(room: dict[str, Any], lab_report: dict[str, Any]) -> str:
    width = 620
    height = 360
    key = html.escape(str(room.get("roomKey", "room")))
    room_type = html.escape(str(room.get("roomType", "unknown")))
    warnings = room.get("warnings", [])
    warning_text = ", ".join(str(w) for w in warnings) if isinstance(warnings, list) and warnings else "none"
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#0d1117"/>',
        f'<text x="16" y="24" fill="#c9d1d9" font-family="monospace" font-size="16">{key} {room_type}</text>',
        f'<text x="16" y="44" fill="#8b949e" font-family="monospace" font-size="11">dirs={html.escape(",".join(str(d) for d in room.get("neighborDirs", [])))} biome={html.escape(str(room.get("biomeIndex", "")))}</text>',
        f'<text x="16" y="62" fill="#8b949e" font-family="monospace" font-size="11">warnings={html.escape(warning_text)}</text>',
        '<text x="16" y="90" fill="#c9d1d9" font-family="monospace" font-size="12">16x16 zone plan</text>',
        '<text x="248" y="90" fill="#c9d1d9" font-family="monospace" font-size="12">128x128 tile preview</text>',
    ]
    parts.extend(zone_rects(room.get("zoneRows", []), 16, 104, 12))
    parts.extend(tile_preview_rects(room.get("tilePreviewRows", []), 248, 104, 256, 256))
    parts.extend(legend_rows(lab_report.get("zoneLegend", {}), 16, 312, "zone"))
    parts.extend(legend_rows(lab_report.get("tileLegend", {}), 520, 104, "tile"))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def zone_rects(zone_rows: Any, x: int, y: int, cell: int) -> list[str]:
    rows = [str(row) for row in zone_rows] if isinstance(zone_rows, list) else []
    parts: list[str] = []
    for row_index, row in enumerate(rows):
        for col_index, symbol in enumerate(row):
            fill = ZONE_COLORS.get(symbol, ZONE_COLORS["!"])
            parts.append(
                f'<rect x="{x + col_index * cell}" y="{y + row_index * cell}" width="{cell}" height="{cell}" '
                f'fill="{fill}" stroke="#0d1117" stroke-width="0.5"/>'
            )
    return parts


def tile_preview_rects(tile_rows: Any, x: int, y: int, width: int, height: int) -> list[str]:
    rows = [str(row) for row in tile_rows] if isinstance(tile_rows, list) else []
    if not rows:
        return [f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="#161b22" stroke="#30363d"/>']
    max_cols = max(len(row) for row in rows)
    target_cols = 40 if width <= 100 else min(128, max_cols)
    target_rows = 40 if height <= 100 else min(128, len(rows))
    sample_y = max(1, -(-len(rows) // target_rows))
    sample_x = max(1, -(-max_cols // target_cols))
    draw_rows = rows[::sample_y][:height]
    sampled_width = max((len(row[::sample_x]) for row in draw_rows), default=1)
    cell_w = max(1, width / max(1, sampled_width))
    cell_h = max(1, height / max(1, len(draw_rows)))
    parts: list[str] = []
    for row_index, row in enumerate(draw_rows):
        sampled = row[::sample_x]
        run_symbol: str | None = None
        run_start = 0
        run_length = 0
        for col_index, symbol in enumerate(sampled):
            if run_symbol is None:
                run_symbol = symbol
                run_start = col_index
                run_length = 1
                continue
            if symbol == run_symbol:
                run_length += 1
                continue
            parts.append(tile_run_rect(x, y, row_index, run_start, run_length, run_symbol, cell_w, cell_h))
            run_symbol = symbol
            run_start = col_index
            run_length = 1
        if run_symbol is not None:
            parts.append(tile_run_rect(x, y, row_index, run_start, run_length, run_symbol, cell_w, cell_h))
    return parts


def tile_run_rect(
    x: int,
    y: int,
    row_index: int,
    run_start: int,
    run_length: int,
    symbol: str,
    cell_w: float,
    cell_h: float,
) -> str:
    fill = TILE_COLORS.get(symbol, TILE_COLORS["!"])
    return (
        f'<rect x="{x + run_start * cell_w:.2f}" y="{y + row_index * cell_h:.2f}" '
        f'width="{run_length * cell_w:.2f}" height="{cell_h:.2f}" fill="{fill}"/>'
    )


def legend_rows(legend: Any, x: int, y: int, label: str) -> list[str]:
    if not isinstance(legend, dict):
        return []
    parts = [f'<text x="{x}" y="{y}" fill="#8b949e" font-family="monospace" font-size="10">{html.escape(label)} legend</text>']
    offset = 14
    for symbol, name in list(legend.items())[:10]:
        color_map = ZONE_COLORS if label == "zone" else TILE_COLORS
        fill = color_map.get(str(symbol), "#ff00ff")
        safe_symbol = html.escape(str(symbol) if str(symbol) != " " else "space")
        parts.append(f'<rect x="{x}" y="{y + offset - 8}" width="8" height="8" fill="{fill}" stroke="#30363d"/>')
        parts.append(
            f'<text x="{x + 12}" y="{y + offset}" fill="#8b949e" font-family="monospace" font-size="9">'
            f'{safe_symbol} {html.escape(str(name))}</text>'
        )
        offset += 12
    return parts


def room_positions_by_key(megamap: dict[str, Any], lab_rooms: list[Any]) -> dict[str, tuple[int, int]]:
    positions: dict[str, tuple[int, int]] = {}
    rooms = megamap.get("rooms") if isinstance(megamap.get("rooms"), list) else []
    for room in rooms:
        if not isinstance(room, dict):
            continue
        key = str(room.get("id", room.get("roomKey", "")))
        gx = room.get("gridX")
        gy = room.get("gridY")
        if isinstance(gx, int) and isinstance(gy, int) and key:
            positions[key] = (gx, gy)
    for index, room in enumerate(lab_rooms):
        if not isinstance(room, dict):
            continue
        key = str(room.get("roomKey", ""))
        if key and key not in positions:
            try:
                gx_s, gy_s = key.split(",", 1)
                positions[key] = (int(gx_s), int(gy_s))
            except ValueError:
                positions[key] = (index, 0)
    return positions


def safe_room_filename(room_key: str) -> str:
    safe = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in room_key)
    return safe or "room"


def blank_svg(message: str, width: int, height: int) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
        '<rect width="100%" height="100%" fill="#0d1117"/>\n'
        f'<text x="16" y="32" fill="#c9d1d9" font-family="monospace" font-size="14">{html.escape(message)}</text>\n'
        "</svg>\n"
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
