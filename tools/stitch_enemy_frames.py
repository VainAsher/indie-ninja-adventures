"""
stitch_enemy_frames.py
----------------------
Stitch per-enemy individual PNG frames into horizontal spritesheets for the
animation engine (AnimationRegistry.loadEnemySheets).

Source: "enemy placeholder animations. single frame per png.zip"
Output: assets/sprites/enemies/<type>/<state>.png

Default ZIP path: C:\\Users\\asher\\OneDrive\\Desktop\\New folder (4)\\
                  enemy placeholder animations. single frame per png.zip

Usage:
    python tools/stitch_enemy_frames.py
    python tools/stitch_enemy_frames.py --zip "path/to/enemy animations.zip"
    python tools/stitch_enemy_frames.py --out "custom/output/dir"

Output structure:
    assets/sprites/enemies/
      swordsman/  idle.png walk.png attack_a.png attack_b.png hit.png dead.png jump.png
      skeleton/   idle.png walk.png attack_a.png attack_b.png hit.png dead.png jump.png shield_block.png
      slime/      idle.png walk.png attack_a.png attack_b.png attack_c.png hit.png dead.png
      grunt/      idle.png walk.png attack_a.png attack_b.png hit.png dead.png jump.png
      wolf/       idle.png run.png  attack_a.png attack_b.png hit.png dead.png jump.png
"""

import argparse
import os
import re
import sys
import zipfile
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed. Run:  pip install Pillow")
    sys.exit(1)

# ── Default paths ─────────────────────────────────────────────────────────────

DEFAULT_ZIP = (
    r"C:\Users\asher\OneDrive\Desktop\New folder (4)"
    r"\enemy placeholder animations. single frame per png.zip"
)

# Script lives in tools/, repo root is one level up
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = (
    REPO_ROOT / "java" / "client" / "src" / "main" / "resources" / "assets" / "sprites" / "enemies"
)

# ── Folder → enemy type mapping ───────────────────────────────────────────────
#
# ZIP contains folders "1 Enemy", "2 Enemy" ... "5 Enemy".
# Each folder has a "PNG" subdirectory with individual frames.

FOLDER_MAP = {
    "1 Enemy": "swordsman",  # greatsword skeleton
    "2 Enemy": "skeleton",  # sword + shield skeleton
    "3 Enemy": "slime",  # slime (ground-only)
    "4 Enemy": "spearman",  # skeleton spearman (longer reach)
    "5 Enemy": "archer",  # skeleton archer (kiter, bow)
}

# ── Frame-group rules per enemy type ──────────────────────────────────────────
#
# For each output sheet we specify which source frame prefix(es) to collect.
# Frames are sorted numerically by their trailing number (A1 < A2 < ... < A12).
#
# Format: { output_filename: [list of prefix patterns to include] }
#   Prefix patterns are matched case-insensitively against the bare PNG name.
#   First matching pattern wins for each source file.

FRAME_GROUPS = {
    "swordsman": {
        "idle.png": ["idle-"],
        "walk.png": ["walk-"],
        "attack_a.png": ["attack-a"],
        "attack_b.png": ["attack-b"],
        "hit.png": ["hit-"],
        "dead.png": ["dead-"],
        "jump.png": ["jump-"],
    },
    "skeleton": {
        "idle.png": ["idle-"],
        "walk.png": ["walk-"],
        "attack_a.png": ["attack-a"],
        "attack_b.png": ["attack-b"],
        "hit.png": ["hit-"],
        "dead.png": ["dead-"],
        "jump.png": ["jump-"],
        "shield_block.png": ["shield-block", "shield_block"],
    },
    "slime": {
        "idle.png": ["idle-"],
        "walk.png": ["walk-"],
        "attack_a.png": ["attack-a"],
        "attack_b.png": ["attack-b"],
        "attack_c.png": ["attack-c"],
        "hit.png": ["hit-"],
        "dead.png": ["dead-"],
        # slime has no jump
    },
    "spearman": {
        "idle.png": ["idle-"],
        "walk.png": ["walk-"],
        "attack_a.png": ["attack-a"],
        "attack_b.png": ["attack-b"],
        "hit.png": ["hit-"],
        "dead.png": ["dead-"],
        "jump.png": ["jump-"],
    },
    "archer": {
        "idle.png": ["idle-"],
        "run.png": ["run-"],  # archer kites using run anim
        "walk.png": ["run-"],  # walk alias -> same run sheet
        "attack_a.png": ["attack-a"],
        "attack_b.png": ["attack-b"],
        "hit.png": ["hit-"],
        "dead.png": ["dead-"],
        "jump.png": ["jump-"],
    },
}


def natural_sort_key(name: str):
    """Sort filenames with embedded numbers naturally: a1 < a2 < a10."""
    parts = re.split(r"(\d+)", name.lower())
    return [int(p) if p.isdigit() else p for p in parts]


def stitch_frames(frames: list[Image.Image], output_path: Path) -> int:
    """Stitch frames left-to-right into a single horizontal PNG. Returns frame count."""
    if not frames:
        return 0
    w = sum(f.width for f in frames)
    h = max(f.height for f in frames)
    sheet = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    x = 0
    for f in frames:
        sheet.paste(f.convert("RGBA"), (x, 0))
        x += f.width
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(str(output_path))
    return len(frames)


def matches_prefix(filename: str, prefixes: list[str]) -> bool:
    name_low = filename.lower()
    return any(name_low.startswith(p.lower()) for p in prefixes)


def process_enemy(
    zip_ref: zipfile.ZipFile, folder: str, enemy_type: str, out_dir: Path, groups: dict
) -> dict:
    """Extract + stitch all animation groups for one enemy type. Returns stats dict."""
    stats = {}

    # Collect all PNG paths inside this folder's PNG subdirectory
    png_prefix = folder + "/PNG/"
    # Also handle nested subdirs within the folder (some ZIPs vary)
    all_paths = [
        zi
        for zi in zip_ref.infolist()
        if not zi.is_dir() and folder in zi.filename and zi.filename.lower().endswith(".png")
    ]

    if not all_paths:
        print(f"  WARNING: No PNGs found under '{folder}/' — skipping {enemy_type}")
        return stats

    # Print audit: unique bare names for this enemy
    bare_names = sorted({Path(zi.filename).name for zi in all_paths}, key=natural_sort_key)
    print(f"\n  [{enemy_type}] found {len(bare_names)} source frames")
    print(f"    sample: {bare_names[:6]}{'...' if len(bare_names) > 6 else ''}")

    type_out = out_dir / enemy_type
    type_out.mkdir(parents=True, exist_ok=True)

    for output_file, prefix_list in groups.items():
        # Collect matching frames, sorted naturally
        matching = [zi for zi in all_paths if matches_prefix(Path(zi.filename).name, prefix_list)]
        matching.sort(key=lambda zi: natural_sort_key(Path(zi.filename).name))

        if not matching:
            stats[output_file] = 0
            continue

        # Load images from ZIP
        images = []
        for zi in matching:
            with zip_ref.open(zi) as f:
                try:
                    img = Image.open(f).copy()
                    images.append(img)
                except Exception as e:
                    print(f"    WARNING: could not load {zi.filename}: {e}")

        if not images:
            stats[output_file] = 0
            continue

        count = stitch_frames(images, type_out / output_file)
        stats[output_file] = count
        w, h = images[0].width, images[0].height
        print(f"    {output_file:20s}  {count:2d} frames  ({w}×{h} px each)")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Stitch enemy frame PNGs into spritesheets.")
    parser.add_argument("--zip", default=DEFAULT_ZIP, help="Path to the enemy animation ZIP")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output directory")
    args = parser.parse_args()

    zip_path = Path(args.zip)
    out_dir = Path(args.out)

    if not zip_path.exists():
        print(f"ERROR: ZIP not found: {zip_path}")
        print(f'Pass the correct path with:  --zip "path/to/enemy animations.zip"')
        sys.exit(1)

    print(f"Source ZIP : {zip_path}")
    print(f"Output dir : {out_dir}")
    print()

    summary = {}
    with zipfile.ZipFile(zip_path, "r") as zf:
        # List top-level entries to show what's inside
        top_dirs = sorted({zi.filename.split("/")[0] for zi in zf.infolist()})
        print(f"ZIP top-level entries: {top_dirs}")

        for folder, enemy_type in FOLDER_MAP.items():
            # Try to find the folder — handle spaces and case variation
            actual_folder = next(
                (
                    d
                    for d in top_dirs
                    if d.lower().replace(" ", "") == folder.lower().replace(" ", "")
                ),
                folder,
            )
            groups = FRAME_GROUPS.get(enemy_type, {})
            stats = process_enemy(zf, actual_folder, enemy_type, out_dir, groups)
            summary[enemy_type] = stats

    # ── Summary report ────────────────────────────────────────────────────────
    print("\n" + "-" * 60)
    print("SUMMARY")
    print("-" * 60)
    total_sheets = 0
    for etype, stats in summary.items():
        present = [(f, c) for f, c in stats.items() if c > 0]
        missing = [f for f, c in stats.items() if c == 0]
        print(f"\n{etype}:")
        for fname, count in present:
            print(f"  OK  {fname}  ({count} frames)")
        for fname in missing:
            print(f"  --  {fname}  (no frames found - key will use placeholder)")
        total_sheets += len(present)

    print(f"\n{total_sheets} spritesheets written to {out_dir}")
    print("\nNext step: run the Java build -- loadEnemySheets() will pick these up automatically.")
    print("Build with:  cd java && gradle buildAll")

    # Write a README in the output dir
    readme = out_dir / "README.md"
    with open(readme, "w") as f:
        f.write("# Enemy Spritesheets\n\n")
        f.write("Generated by `tools/stitch_enemy_frames.py` from the enemy animation ZIP.\n\n")
        f.write("| Type | Source folder | Notes |\n")
        f.write("|------|--------------|-------|\n")
        f.write("| swordsman | 1 Enemy | Greatsword skeleton; slow heavy attacks |\n")
        f.write("| skeleton  | 2 Enemy | Sword+shield skeleton; GUARD blocks melee |\n")
        f.write("| slime     | 3 Enemy | Multi-hit; no jump |\n")
        f.write("| spearman  | 4 Enemy | Skeleton spearman; longer attack reach |\n")
        f.write("| archer    | 5 Enemy | Skeleton archer/kiter; uses run sheet |\n")
        f.write("| bat       | (none)  | Placeholder until flying art arrives |\n\n")
        f.write("Re-run the script to regenerate after updating source frames.\n")


if __name__ == "__main__":
    main()
