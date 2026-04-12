#!/usr/bin/env python3
"""
Animation sprite-sheet extraction script.

Reads:
  001 Player Template Moves.zip     → unarmed set
  002 Player Template Moves - Sword.zip → sword + pistol sets

Writes to:
  assets/sprites/player/unarmed/   (79 sheets)
  assets/sprites/player/sword/     (70+ sheets)
  assets/sprites/player/pistol/    (staged but not wired)

Usage:
  python tools/extract_animations.py \
    --zip1 "C:/Users/asher/Downloads/001 Player Template Moves.zip" \
    --zip2 "C:/Users/asher/Downloads/002 Player Template Moves - Sword.zip" \
    [--repo-root .]
"""

import argparse
import os
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Unarmed mapping: ZIP basename → engine filename (assets/sprites/player/unarmed/)
# ---------------------------------------------------------------------------
UNARMED_MAP = {
    "001-Standing Idle-Sheet.png":                    "idle_spritesheet.png",
    "001-Standing Fighting-Sheet.png":                "combat_idle_spritesheet.png",
    "001-Standing Idly-Sheet.png":                    "fidget_spritesheet.png",
    "001-Standing Walk-Sheet.png":                    "walk_spritesheet.png",
    "001-Standing Direct Punch Combo-Sheet.png":      "punch1_spritesheet.png",
    "001-Standing Cross Punch Combo-Sheet.png":       "punch2_spritesheet.png",
    "003-Standing Kick-Sheet.png":                    "kick_spritesheet.png",
    "001-Standing Block Idle-Sheet.png":              "block_idle_spritesheet.png",
    "001-Standing Block Hit (Normal)-Sheet.png":      "block_hit_normal_spritesheet.png",
    "001-Standing Block Hit (Hard)-Sheet.png":        "block_hit_hard_spritesheet.png",
    "001-Standing Hit Upper Body-Sheet.png":          "hurt_upper_spritesheet.png",
    "001-Standing Hit Lower Body-Sheet.png":          "hurt_lower_spritesheet.png",
    "001-Standing Death(Defeat) A-Sheet.png":         "death_spritesheet.png",
    "001-Standing Death A Getting Up-Sheet.png":      "revive_spritesheet.png",
    "001-Standing Death(Defeat) B-Sheet.png":         "death2_spritesheet.png",
    "001-Standing Death(Defeat) B Getting Up-Sheet.png": "revive2_spritesheet.png",
    "001-Run-Sheet.png":                              "run_spritesheet.png",
    "001-Run Skid Turn-Sheet.png":                    "skid_spritesheet.png",
    "001-Run Flying Kick-Sheet.png":                  "run_kick_spritesheet.png",
    "001-Run Stop-Sheet.png":                         "run_stop_spritesheet.png",
    "001-Jump-Sheet.png":                             "jumpfall_spritesheet.png",
    "001-Jump Front Flip-Sheet.png":                  "flip_spritesheet.png",
    "001-Jump Direct Punch Combo-Sheet.png":          "air_punch1_spritesheet.png",
    "001-Jump Cross Punch Combo-Sheet.png":           "air_punch2_spritesheet.png",
    "001-Jump Kick-Sheet.png":                        "air_kick_spritesheet.png",
    "001-Jump Block Idle-Sheet.png":                  "air_block_spritesheet.png",
    "001-Jump Block Hit-Sheet.png":                   "air_block_hit_spritesheet.png",
    "001-Crouch Idle-Sheet.png":                      "crouch_idle_spritesheet.png",
    "001-Crouch Walk-Sheet.png":                      "crouch_walk_spritesheet.png",
    "001-Crouch Punch-Sheet.png":                     "crouch_punch_spritesheet.png",
    "001-Crouch Kick-Sheet.png":                      "crouch_kick_spritesheet.png",
    "001-Crouch Block Idle-Sheet.png":                "crouch_block_spritesheet.png",
    "001-Crouch Block Hit-Sheet.png":                 "crouch_block_hit_spritesheet.png",
    "001-Crouch Hit-Sheet.png":                       "crouch_hurt_spritesheet.png",
    "001-Climb Idle (Back)-Sheet.png":                "climb_idle_back_spritesheet.png",
    "001-Climb Idle (Side)-Sheet.png":                "climb_idle_side_spritesheet.png",
    "001-Climb (Up) (Down) (Back)-Sheet.png":         "climb_back_spritesheet.png",
    "001-Climb (Up) (Down) (Side)-Sheet.png":         "climb_side_spritesheet.png",
    "001-Climb (Right)-Sheet.png":                    "climb_right_spritesheet.png",
    "001-Climb (Left)-Sheet.png":                     "climb_left_spritesheet.png",
    "001-Climb Ledge Grab (Back)-Sheet.png":          "ledge_grab_back_spritesheet.png",
    "001-Climb Ledge Idle (Back)-Sheet.png":          "ledge_idle_back_spritesheet.png",
    "001-Climb Ledge Climbing (Back)-Sheet.png":      "ledge_climb_back_spritesheet.png",
    "001-Climb Ledge Grab (Side)-Sheet.png":          "ledge_grab_spritesheet.png",
    "001-Climb Ledge Idle (Side)-Sheet.png":          "ledge_idle_spritesheet.png",
    "001-Climb Ledge Climbing (Side)-Sheet.png":      "ledge_climb_spritesheet.png",
    "001-Water Surface Idle-Sheet.png":               "swim_surface_idle_spritesheet.png",
    "001-Water Surface Swimming-Sheet.png":           "swim_surface_spritesheet.png",
    "001-Water Bottom Idle-Sheet.png":                "swim_idle_spritesheet.png",
    "001-Water Bottom Swimming (Front)-Sheet.png":    "swim_spritesheet.png",
    "001-Water Bottom Swimming (Up)-Sheet.png":       "swim_up_spritesheet.png",
    "001-Water Bottom Swimming (Down)-Sheet.png":     "swim_down_spritesheet.png",
    "001-Prone Idle-Sheet.png":                       "prone_idle_spritesheet.png",
    "001-Prone Crawling-Sheet.png":                   "prone_walk_spritesheet.png",
    "001-Prone Hit-Sheet.png":                        "prone_hurt_spritesheet.png",
    "001-Prone Death(Defeat)-Sheet.png":              "prone_death_spritesheet.png",
    "001-Prone Death(Defeat) Waking Up-Sheet.png":    "prone_revive_spritesheet.png",
    "001-Dash-Sheet.png":                             "dash_spritesheet.png",
    "001-Roll-Sheet.png":                             "roll_spritesheet.png",
    "001-Slide-Sheet.png":                            "slide_spritesheet.png",
    "001-Wall Jump Land-Sheet.png":                   "wall_land_spritesheet.png",
    "001-Wall Jump Slide-Sheet.png":                  "wall_slide_spritesheet.png",
    "001-Push-Pull Idle-Sheet.png":                   "push_idle_spritesheet.png",
    "001-Push-Sheet.png":                             "push_spritesheet.png",
    "001-Pull-Sheet.png":                             "pull_spritesheet.png",
    "001-Door Enter-Sheet.png":                       "door_enter_spritesheet.png",
    "001-Door Exit-Sheet.png":                        "door_exit_spritesheet.png",
    "001-Push Button (Side)-Sheet.png":               "button_spritesheet.png",
    "001-Pull Lever (Ground)-Sheet.png":              "lever_spritesheet.png",
    "001-Pickup Standing-Sheet.png":                  "pickup_spritesheet.png",
    "001-Pickup Crouch-Sheet.png":                    "pickup_crouch_spritesheet.png",
    "001-Open Chest (Back)-Sheet.png":                "chest_back_spritesheet.png",
    "001-Open Chest (Side)-Sheet.png":                "chest_side_spritesheet.png",
    "001- Rope Hanging Idle-Sheet.png":               "rope_idle_spritesheet.png",
    "001- Rope Swinging-Sheet.png":                   "rope_swing_spritesheet.png",
    "001-Sitting-Sheet.png":                          "sit_spritesheet.png",
    "001-Asleep-Sheet.png":                           "sleep_spritesheet.png",
    "001-Talking-Sheet.png":                          "talk_spritesheet.png",
    "001- Victory-Sheet.png":                         "victory_spritesheet.png",
    "001-Drink-Sheet.png":                            "drink_spritesheet.png",
    "001- Dance Twerk-Sheet.png":                     "dance_spritesheet.png",
}

# ---------------------------------------------------------------------------
# Sword mapping: ZIP basename (with " - Sword" suffix) → engine filename
# Keys are the actual ZIP basenames. We match by stripping " - Sword" to find
# a match in the unarmed map, then use the same engine filename in sword/.
# Sword-specific sheets (not in unarmed set) are listed explicitly below.
# ---------------------------------------------------------------------------
SWORD_EXTRA_MAP = {
    # Sword-specific attack combos (not in unarmed set)
    "001-Standing Attack Combo - Sword 1 Hit Effect-Sheet.png": None,  # skip effects
    "001- Dash Attack - Sword-Sheet.png":                        "dash_attack_spritesheet.png",
    # The main combo sheets are named with sequential sub-directories in the ZIP;
    # extract_sword_combos() handles them separately.
}

def extract_unarmed(z: zipfile.ZipFile, out_dir: Path, verbose: bool) -> tuple[int, int, list[str]]:
    """Extract unarmed sheets from ZIP 001. Returns (extracted, skipped, unmapped)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    extracted, skipped, unmapped = 0, 0, []

    for entry in z.infolist():
        if not entry.filename.endswith("-Sheet.png"):
            continue
        basename = entry.filename.split("/")[-1]
        dest_name = UNARMED_MAP.get(basename)
        if dest_name is None:
            unmapped.append(basename)
            continue
        dest = out_dir / dest_name
        if dest.exists():
            skipped += 1
            continue
        data = z.read(entry.filename)
        dest.write_bytes(data)
        extracted += 1
        if verbose:
            print(f"  [unarmed] {basename} → {dest_name}")

    return extracted, skipped, unmapped


def extract_sword(z: zipfile.ZipFile, out_dir: Path, verbose: bool) -> tuple[int, int, list[str]]:
    """Extract sword sheets from ZIP 002 (entries with ' - Sword-Sheet.png' suffix).
    Falls back to matching the unarmed map after stripping the sword suffix."""
    out_dir.mkdir(parents=True, exist_ok=True)
    extracted, skipped, unmapped = 0, 0, []

    for entry in z.infolist():
        if not entry.filename.endswith("-Sheet.png"):
            continue
        # Only process entries in the sword section
        if "002 Player Template Moves - Sword" not in entry.filename:
            continue
        basename = entry.filename.split("/")[-1]

        # Skip effect sheets (visual overlays only — not player sprites)
        if "Effect-Sheet.png" in basename:
            continue

        # Determine engine filename
        dest_name = None

        # Check sword-extra map first
        if basename in SWORD_EXTRA_MAP:
            dest_name = SWORD_EXTRA_MAP[basename]
            if dest_name is None:
                continue  # explicitly skipped

        # Derive from unarmed map by stripping " - Sword" suffix variants
        if dest_name is None:
            stripped = basename
            for suffix in [" - Sword-Sheet.png", "- Sword-Sheet.png"]:
                if stripped.endswith(suffix):
                    stripped = stripped[: -len(suffix)] + "-Sheet.png"
                    break
            dest_name = UNARMED_MAP.get(stripped)

        if dest_name is None:
            unmapped.append(basename)
            continue

        dest = out_dir / dest_name
        if dest.exists():
            skipped += 1
            continue
        data = z.read(entry.filename)
        dest.write_bytes(data)
        extracted += 1
        if verbose:
            print(f"  [sword]   {basename} → {dest_name}")

    # Handle sword attack combos (multi-sheet per attack direction)
    extracted2 = extract_sword_combos(z, out_dir, verbose)
    extracted += extracted2

    return extracted, skipped, unmapped


def extract_sword_combos(z: zipfile.ZipFile, out_dir: Path, verbose: bool) -> int:
    """Extract Standing/Jump/Crouch Attack Combo sword sheets as d0..d7 / d0..d4."""
    extracted = 0

    patterns = [
        # (zip_basename_pattern, output_prefix, max_index)
        ("Standing Attack Combo - Sword", "attack_combo", 8),
        ("Jump Attack Combo - Sword",     "air_attack",   5),
        ("Crouch Attack Combo - Sword",   "crouch_attack", 5),
    ]

    for zip_pattern, out_prefix, max_n in patterns:
        combo_entries = sorted([
            e for e in z.infolist()
            if "-Sheet.png" in e.filename
            and zip_pattern in e.filename
            and "Effect" not in e.filename
            and "002 Player Template Moves - Sword" in e.filename
        ], key=lambda e: e.filename)

        for idx, entry in enumerate(combo_entries[:max_n]):
            fname = f"{out_prefix}_d{idx}_spritesheet.png"
            dest = out_dir / fname
            if dest.exists():
                continue
            data = z.read(entry.filename)
            dest.write_bytes(data)
            extracted += 1
            if verbose:
                print(f"  [sword]   combo {idx} → {fname}")

        # Also register the stab variant if present
        stab_entries = [
            e for e in z.infolist()
            if "-Sheet.png" in e.filename
            and zip_pattern.replace("Attack Combo", "Attack Stab") in e.filename
            and "002 Player Template Moves - Sword" in e.filename
            and "Effect" not in e.filename
        ]
        if stab_entries:
            stab_key = f"{out_prefix.replace('attack', 'stab').replace('air_', 'air_')}_spritesheet.png"
            dest = out_dir / stab_key
            if not dest.exists():
                data = z.read(stab_entries[0].filename)
                dest.write_bytes(data)
                extracted += 1

    return extracted


def extract_pistol(z: zipfile.ZipFile, out_dir: Path, verbose: bool) -> tuple[int, int]:
    """Stage pistol sheets to /pistol/ (not yet wired to engine). Returns (extracted, skipped)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    extracted, skipped = 0, 0

    for entry in z.infolist():
        if not entry.filename.endswith("-Sheet.png"):
            continue
        if "003 Player Template Moves - Pistol" not in entry.filename:
            continue
        basename = entry.filename.split("/")[-1]
        if "Effect-Sheet.png" in basename:
            continue

        # Strip " - Pistol" suffix to get a sensible name
        stripped = basename
        for suffix in [" - Pistol-Sheet.png", "- Pistol-Sheet.png"]:
            if stripped.endswith(suffix):
                stripped = stripped[: -len(suffix)].lower().replace(" ", "_") + "_spritesheet.png"
                break
        else:
            stripped = basename.lower().replace(" ", "_")

        dest = out_dir / stripped
        if dest.exists():
            skipped += 1
            continue
        data = z.read(entry.filename)
        dest.write_bytes(data)
        extracted += 1

    return extracted, skipped


def main():
    parser = argparse.ArgumentParser(description="Extract animation sprite sheets from ZIPs.")
    parser.add_argument("--zip1", default="C:/Users/asher/Downloads/001 Player Template Moves.zip",
                        help="Path to unarmed ZIP")
    parser.add_argument("--zip2", default="C:/Users/asher/Downloads/002 Player Template Moves - Sword.zip",
                        help="Path to sword/pistol ZIP")
    parser.add_argument("--repo-root", default=".", help="Repository root directory")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    player_dir = repo_root / "assets" / "sprites" / "player"

    print(f"Extracting to: {player_dir}")

    with zipfile.ZipFile(args.zip1) as z1:
        ex, sk, um = extract_unarmed(z1, player_dir / "unarmed", args.verbose)
        print(f"\nUnarmed: {ex} extracted, {sk} skipped, {len(um)} unmapped")
        if um:
            for n in um[:10]:
                print(f"  UNMAPPED: {n}")
            if len(um) > 10:
                print(f"  ... and {len(um) - 10} more")

    with zipfile.ZipFile(args.zip2) as z2:
        ex, sk, um = extract_sword(z2, player_dir / "sword", args.verbose)
        print(f"\nSword:   {ex} extracted, {sk} skipped, {len(um)} unmapped")
        if um:
            for n in um[:10]:
                print(f"  UNMAPPED: {n}")
            if len(um) > 10:
                print(f"  ... and {len(um) - 10} more")

        ex, sk = extract_pistol(z2, player_dir / "pistol", args.verbose)
        print(f"\nPistol:  {ex} extracted, {sk} skipped (staged — not yet wired)")

    # Summary
    unarmed_count = len(list((player_dir / "unarmed").glob("*.png"))) if (player_dir / "unarmed").exists() else 0
    sword_count   = len(list((player_dir / "sword").glob("*.png")))   if (player_dir / "sword").exists()   else 0
    pistol_count  = len(list((player_dir / "pistol").glob("*.png")))  if (player_dir / "pistol").exists()  else 0
    print(f"\nFinal counts:  unarmed={unarmed_count}  sword={sword_count}  pistol={pistol_count}")
    print("\nDone. Verify: open 3 sheets, confirm 80px tall, RGBA, transparent background.")


if __name__ == "__main__":
    main()
