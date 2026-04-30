import argparse
import html
import json
from pathlib import Path


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


def render_bundle(snapshot_path: Path, out_dir: Path) -> list[Path]:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    megamap = snapshot.get("megamap")
    if not isinstance(megamap, dict):
        raise ValueError(f"{snapshot_path} does not contain a megamap block")

    out_dir.mkdir(parents=True, exist_ok=True)
    overlay_rows = list(megamap.get("overlayRows") or [])
    if not overlay_rows:
        raise ValueError(f"{snapshot_path} megamap.overlayRows is empty")

    overlay_path = out_dir / "overlay.txt"
    overlay_path.write_text("\n".join(overlay_rows) + "\n", encoding="utf-8")

    metrics_path = out_dir / "metrics.json"
    metrics = {
        "generatorSchemaVersion": snapshot.get("generatorSchemaVersion"),
        "worldSeed": snapshot.get("worldSeed"),
        "shape": snapshot.get("shape"),
        "goldenSeedKey": megamap.get("goldenSeedKey"),
        "bounds": megamap.get("bounds", {}),
        "metrics": megamap.get("metrics", {}),
        "autotileSummary": megamap.get("autotileSummary", {}),
    }
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    svg_path = out_dir / "megamap.svg"
    svg_path.write_text(render_svg(overlay_rows, metrics), encoding="utf-8")
    return [overlay_path, metrics_path, svg_path]


def render_svg(overlay_rows: list[str], metrics: dict) -> str:
    cell = 24
    padding = 12
    width_cells = max(len(row) for row in overlay_rows)
    height_cells = len(overlay_rows)
    width = width_cells * cell + padding * 2
    height = height_cells * cell + padding * 2 + 36
    title = html.escape(str(metrics.get("goldenSeedKey") or "worldgen snapshot"))

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


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a worldgen snapshot megamap bundle.")
    parser.add_argument("snapshot", help="Path to a worldgen snapshot JSON file.")
    parser.add_argument("--out", default="build/worldgen-viewer", help="Output directory for overlay files.")
    args = parser.parse_args()

    written = render_bundle(Path(args.snapshot), Path(args.out))
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
