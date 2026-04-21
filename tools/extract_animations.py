#!/usr/bin/env python3
"""
Extract player animation sprite sheets from template packs.

Supports either ZIP archives or extracted directories.

Default ZIP mode:
  --zip1 "C:/Users/asher/Downloads/001 Player Template Moves.zip"
  --zip2 "C:/Users/asher/Downloads/002 Player Template Moves - Sword.zip"

Directory mode (recommended when packs are already extracted):
  --unarmed-dir "C:/.../001 Player Template Moves"
  --sword-dir   "C:/.../002 Player Template Moves - Sword"
  --pistol-dir  "C:/.../003 Player Template Moves - Pistol"

Writes to:
  assets/sprites/player/unarmed/
  assets/sprites/player/sword/
  assets/sprites/player/pistol/
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


# ZIP basename -> engine filename (assets/sprites/player/unarmed/)
UNARMED_MAP = {
    "001-Standing Idle-Sheet.png": "idle_spritesheet.png",
    "001-Standing Fighting-Sheet.png": "combat_idle_spritesheet.png",
    "001-Standing Idly-Sheet.png": "fidget_spritesheet.png",
    "001-Standing Walk-Sheet.png": "walk_spritesheet.png",
    "001-Standing Direct Punch Combo-Sheet.png": "punch1_spritesheet.png",
    "001-Standing Cross Punch Combo-Sheet.png": "punch2_spritesheet.png",
    "003-Standing Kick-Sheet.png": "kick_spritesheet.png",
    "001-Standing Block Idle-Sheet.png": "block_idle_spritesheet.png",
    "001-Standing Block Hit (Normal)-Sheet.png": "block_hit_normal_spritesheet.png",
    "001-Standing Block Hit (Hard)-Sheet.png": "block_hit_hard_spritesheet.png",
    "001-Standing Hit Upper Body-Sheet.png": "hurt_upper_spritesheet.png",
    "001-Standing Hit Lower Body-Sheet.png": "hurt_lower_spritesheet.png",
    "001-Standing Death(Defeat) A-Sheet.png": "death_spritesheet.png",
    "001-Standing Death A Getting Up-Sheet.png": "revive_spritesheet.png",
    "001-Standing Death(Defeat) B-Sheet.png": "death2_spritesheet.png",
    "001-Standing Death(Defeat) B Getting Up-Sheet.png": "revive2_spritesheet.png",
    "001-Run-Sheet.png": "run_spritesheet.png",
    "001-Run Skid Turn-Sheet.png": "skid_spritesheet.png",
    "001-Run Flying Kick-Sheet.png": "run_kick_spritesheet.png",
    "001-Run Stop-Sheet.png": "run_stop_spritesheet.png",
    "001-Jump-Sheet.png": "jumpfall_spritesheet.png",
    "001-Jump Front Flip-Sheet.png": "flip_spritesheet.png",
    "001-Jump Direct Punch Combo-Sheet.png": "air_punch1_spritesheet.png",
    "001-Jump Cross Punch Combo-Sheet.png": "air_punch2_spritesheet.png",
    "001-Jump Kick-Sheet.png": "air_kick_spritesheet.png",
    "001-Jump Block Idle-Sheet.png": "air_block_spritesheet.png",
    "001-Jump Block Hit-Sheet.png": "air_block_hit_spritesheet.png",
    "001-Crouch Idle-Sheet.png": "crouch_idle_spritesheet.png",
    "001-Crouch Walk-Sheet.png": "crouch_walk_spritesheet.png",
    "001-Crouch Punch-Sheet.png": "crouch_punch_spritesheet.png",
    "001-Crouch Kick-Sheet.png": "crouch_kick_spritesheet.png",
    "001-Crouch Block Idle-Sheet.png": "crouch_block_spritesheet.png",
    "001-Crouch Block Hit-Sheet.png": "crouch_block_hit_spritesheet.png",
    "001-Crouch Hit-Sheet.png": "crouch_hurt_spritesheet.png",
    "001-Climb Idle (Back)-Sheet.png": "climb_idle_back_spritesheet.png",
    "001-Climb Idle (Side)-Sheet.png": "climb_idle_side_spritesheet.png",
    "001-Climb (Up) (Down) (Back)-Sheet.png": "climb_back_spritesheet.png",
    "001-Climb (Up) (Down) (Side)-Sheet.png": "climb_side_spritesheet.png",
    "001-Climb (Right)-Sheet.png": "climb_right_spritesheet.png",
    "001-Climb (Left)-Sheet.png": "climb_left_spritesheet.png",
    "001-Climb Ledge Grab (Back)-Sheet.png": "ledge_grab_back_spritesheet.png",
    "001-Climb Ledge Idle (Back)-Sheet.png": "ledge_idle_back_spritesheet.png",
    "001-Climb Ledge Climbing (Back)-Sheet.png": "ledge_climb_back_spritesheet.png",
    "001-Climb Ledge Grab (Side)-Sheet.png": "ledge_grab_spritesheet.png",
    "001-Climb Ledge Idle (Side)-Sheet.png": "ledge_idle_spritesheet.png",
    "001-Climb Ledge Climbing (Side)-Sheet.png": "ledge_climb_spritesheet.png",
    "001-Water Surface Idle-Sheet.png": "swim_surface_idle_spritesheet.png",
    "001-Water Surface Swimming-Sheet.png": "swim_surface_spritesheet.png",
    "001-Water Bottom Idle-Sheet.png": "swim_idle_spritesheet.png",
    "001-Water Bottom Swimming (Front)-Sheet.png": "swim_spritesheet.png",
    "001-Water Bottom Swimming (Up)-Sheet.png": "swim_up_spritesheet.png",
    "001-Water Bottom Swimming (Down)-Sheet.png": "swim_down_spritesheet.png",
    "001-Prone Idle-Sheet.png": "prone_idle_spritesheet.png",
    "001-Prone Crawling-Sheet.png": "prone_walk_spritesheet.png",
    "001-Prone Hit-Sheet.png": "prone_hurt_spritesheet.png",
    "001-Prone Death(Defeat)-Sheet.png": "prone_death_spritesheet.png",
    "001-Prone Death(Defeat) Waking Up-Sheet.png": "prone_revive_spritesheet.png",
    "001-Dash-Sheet.png": "dash_spritesheet.png",
    "001-Roll-Sheet.png": "roll_spritesheet.png",
    "001-Slide-Sheet.png": "slide_spritesheet.png",
    "001-Wall Jump Land-Sheet.png": "wall_land_spritesheet.png",
    "001-Wall Jump Slide-Sheet.png": "wall_slide_spritesheet.png",
    "001-Push-Pull Idle-Sheet.png": "push_idle_spritesheet.png",
    "001-Push-Sheet.png": "push_spritesheet.png",
    "001-Pull-Sheet.png": "pull_spritesheet.png",
    "001-Door Enter-Sheet.png": "door_enter_spritesheet.png",
    "001-Door Exit-Sheet.png": "door_exit_spritesheet.png",
    "001-Push Button (Side)-Sheet.png": "button_spritesheet.png",
    "001-Pull Lever (Ground)-Sheet.png": "lever_spritesheet.png",
    "001-Pickup Standing-Sheet.png": "pickup_spritesheet.png",
    "001-Pickup Crouch-Sheet.png": "pickup_crouch_spritesheet.png",
    "001-Open Chest (Back)-Sheet.png": "chest_back_spritesheet.png",
    "001-Open Chest (Side)-Sheet.png": "chest_side_spritesheet.png",
    "001- Rope Hanging Idle-Sheet.png": "rope_idle_spritesheet.png",
    "001- Rope Swinging-Sheet.png": "rope_swing_spritesheet.png",
    "001-Sitting-Sheet.png": "sit_spritesheet.png",
    "001-Asleep-Sheet.png": "sleep_spritesheet.png",
    "001-Talking-Sheet.png": "talk_spritesheet.png",
    "001- Victory-Sheet.png": "victory_spritesheet.png",
    "001-Drink-Sheet.png": "drink_spritesheet.png",
    "001- Dance Twerk-Sheet.png": "dance_spritesheet.png",
}

# Sword-specific map entries (not derived from UNARMED_MAP).
SWORD_EXTRA_MAP = {
    "001- Dash Attack - Sword-Sheet.png": "dash_attack_spritesheet.png",
}

# Sword names that need normalizing before UNARMED_MAP lookup.
SWORD_ALIAS_MAP = {
    "001-Death(Defeat) A-Sheet.png": "001-Standing Death(Defeat) A-Sheet.png",
    "001-Death(Defeat) B-Sheet.png": "001-Standing Death(Defeat) B-Sheet.png",
    "002-Death A Getting Up-Sheet.png": "001-Standing Death A Getting Up-Sheet.png",
    "002-Death(Defeat) B Getting Up-Sheet.png": "001-Standing Death(Defeat) B Getting Up-Sheet.png",
}

# Pistol names that do not match unarmed naming exactly after suffix strip.
PISTOL_ALIAS_MAP = {
    "001-Block Hit (Normal)-Sheet.png": "001-Standing Block Hit (Normal)-Sheet.png",
    "002-Block Hit (Hard)-Sheet.png": "001-Standing Block Hit (Hard)-Sheet.png",
    "001-Death(Defeat) A-Sheet.png": "001-Standing Death(Defeat) A-Sheet.png",
    "001-Death(Defeat) B-Sheet.png": "001-Standing Death(Defeat) B-Sheet.png",
    "002-Death A Getting Up-Sheet.png": "001-Standing Death A Getting Up-Sheet.png",
    "002-Death(Defeat) B Getting Up-Sheet.png": "001-Standing Death(Defeat) B Getting Up-Sheet.png",
    "001-Standing Kick-Sheet.png": "003-Standing Kick-Sheet.png",
}

# Pistol-specific substitutions for gameplay keys currently used by runtime.
PISTOL_SPECIAL_MAP = {
    "001-Standing Aim Front-Sheet.png": "combat_idle_spritesheet.png",
    "001-Standing Shoot Front-Sheet.png": "attack_combo_d0_spritesheet.png",
}


def strip_weapon_suffix(basename: str, weapon: str) -> str:
    suffixes = [
        f" - {weapon}-Sheet.png",
        f"- {weapon}-Sheet.png",
        f" - {weapon} -Sheet.png",
        f"-{weapon}-Sheet.png",
    ]
    for suffix in suffixes:
        if basename.endswith(suffix):
            return basename[: -len(suffix)] + "-Sheet.png"
    return basename


def resolve_sword_dest(basename: str) -> str | None:
    if "Effect-Sheet.png" in basename:
        return None
    if basename in SWORD_EXTRA_MAP:
        return SWORD_EXTRA_MAP[basename]
    stripped = strip_weapon_suffix(basename, "Sword")
    stripped = SWORD_ALIAS_MAP.get(stripped, stripped)
    return UNARMED_MAP.get(stripped)


def resolve_pistol_dest(basename: str) -> str | None:
    if "Effect-Sheet.png" in basename:
        return None
    stripped = strip_weapon_suffix(basename, "Pistol")
    stripped = PISTOL_ALIAS_MAP.get(stripped, stripped)
    if stripped in PISTOL_SPECIAL_MAP:
        return PISTOL_SPECIAL_MAP[stripped]
    return UNARMED_MAP.get(stripped)


def write_sheet(
    src_name: str,
    data: bytes,
    out_dir: Path,
    dest_name: str,
    overwrite: bool,
    written_this_run: set[Path],
) -> tuple[bool, bool]:
    dest = out_dir / dest_name
    if dest in written_this_run:
        return False, True
    if dest.exists() and not overwrite:
        return False, True
    dest.write_bytes(data)
    written_this_run.add(dest)
    return True, False


def extract_unarmed_zip(
    z: zipfile.ZipFile,
    out_dir: Path,
    verbose: bool,
    overwrite: bool,
) -> tuple[int, int, list[str]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    extracted, skipped, unmapped = 0, 0, []
    written: set[Path] = set()

    for entry in z.infolist():
        if not entry.filename.endswith("-Sheet.png"):
            continue
        basename = entry.filename.split("/")[-1]
        dest_name = UNARMED_MAP.get(basename)
        if dest_name is None:
            unmapped.append(basename)
            continue
        ok, skip = write_sheet(
            basename, z.read(entry.filename), out_dir, dest_name, overwrite, written
        )
        extracted += 1 if ok else 0
        skipped += 1 if skip else 0
        if ok and verbose:
            print(f"  [unarmed] {basename} -> {dest_name}")
    return extracted, skipped, unmapped


def extract_unarmed_dir(
    src_dir: Path,
    out_dir: Path,
    verbose: bool,
    overwrite: bool,
) -> tuple[int, int, list[str]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    extracted, skipped, unmapped = 0, 0, []
    written: set[Path] = set()

    files = sorted(src_dir.rglob("*-Sheet.png"), key=lambda p: p.name)
    for src in files:
        basename = src.name
        dest_name = UNARMED_MAP.get(basename)
        if dest_name is None:
            unmapped.append(basename)
            continue
        ok, skip = write_sheet(
            basename, src.read_bytes(), out_dir, dest_name, overwrite, written
        )
        extracted += 1 if ok else 0
        skipped += 1 if skip else 0
        if ok and verbose:
            print(f"  [unarmed] {basename} -> {dest_name}")
    return extracted, skipped, unmapped


def extract_sword_combos_zip(
    z: zipfile.ZipFile,
    out_dir: Path,
    verbose: bool,
    overwrite: bool,
    written: set[Path],
) -> int:
    extracted = 0
    patterns = [
        ("Standing Attack Combo - Sword", "attack_combo", 8),
        ("Jump Attack Combo - Sword", "air_attack", 5),
        ("Crouch Attack Combo - Sword", "crouch_attack", 5),
    ]
    for zip_pattern, out_prefix, max_n in patterns:
        combo_entries = sorted(
            [
                e
                for e in z.infolist()
                if "-Sheet.png" in e.filename
                and zip_pattern in e.filename
                and "Effect" not in e.filename
                and "002 Player Template Moves - Sword" in e.filename
            ],
            key=lambda e: e.filename,
        )
        for idx, entry in enumerate(combo_entries[:max_n]):
            fname = f"{out_prefix}_d{idx}_spritesheet.png"
            ok, _ = write_sheet(
                entry.filename, z.read(entry.filename), out_dir, fname, overwrite, written
            )
            if ok:
                extracted += 1
                if verbose:
                    print(f"  [sword] combo {idx} -> {fname}")

        stab_entries = [
            e
            for e in z.infolist()
            if "-Sheet.png" in e.filename
            and zip_pattern.replace("Attack Combo", "Attack Stab") in e.filename
            and "002 Player Template Moves - Sword" in e.filename
            and "Effect" not in e.filename
        ]
        if stab_entries:
            fname = (
                f"{out_prefix.replace('attack', 'stab').replace('air_', 'air_')}_spritesheet.png"
            )
            ok, _ = write_sheet(
                stab_entries[0].filename,
                z.read(stab_entries[0].filename),
                out_dir,
                fname,
                overwrite,
                written,
            )
            if ok:
                extracted += 1
    return extracted


def extract_sword_combos_dir(
    src_dir: Path,
    out_dir: Path,
    verbose: bool,
    overwrite: bool,
    written: set[Path],
) -> int:
    extracted = 0
    files = sorted(src_dir.rglob("*-Sheet.png"), key=lambda p: p.name)
    patterns = [
        ("Standing Attack Combo - Sword", "attack_combo", 8),
        ("Jump Attack Combo - Sword", "air_attack", 5),
        ("Crouch Attack Combo - Sword", "crouch_attack", 5),
    ]
    for basename_pattern, out_prefix, max_n in patterns:
        combo_files = [
            p
            for p in files
            if basename_pattern in p.name and "Effect" not in p.name
        ]
        combo_files.sort(key=lambda p: p.name)
        for idx, src in enumerate(combo_files[:max_n]):
            fname = f"{out_prefix}_d{idx}_spritesheet.png"
            ok, _ = write_sheet(
                src.name, src.read_bytes(), out_dir, fname, overwrite, written
            )
            if ok:
                extracted += 1
                if verbose:
                    print(f"  [sword] combo {idx} -> {fname}")

        stab_files = [
            p
            for p in files
            if basename_pattern.replace("Attack Combo", "Attack Stab") in p.name
            and "Effect" not in p.name
        ]
        if stab_files:
            stab_files.sort(key=lambda p: p.name)
            fname = (
                f"{out_prefix.replace('attack', 'stab').replace('air_', 'air_')}_spritesheet.png"
            )
            ok, _ = write_sheet(
                stab_files[0].name,
                stab_files[0].read_bytes(),
                out_dir,
                fname,
                overwrite,
                written,
            )
            if ok:
                extracted += 1
    return extracted


def extract_sword_zip(
    z: zipfile.ZipFile,
    out_dir: Path,
    verbose: bool,
    overwrite: bool,
) -> tuple[int, int, list[str]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    extracted, skipped, unmapped = 0, 0, []
    written: set[Path] = set()

    for entry in z.infolist():
        if not entry.filename.endswith("-Sheet.png"):
            continue
        if "002 Player Template Moves - Sword" not in entry.filename:
            continue
        basename = entry.filename.split("/")[-1]
        if "Effect-Sheet.png" in basename:
            continue
        dest_name = resolve_sword_dest(basename)
        if dest_name is None:
            unmapped.append(basename)
            continue
        ok, skip = write_sheet(
            basename, z.read(entry.filename), out_dir, dest_name, overwrite, written
        )
        extracted += 1 if ok else 0
        skipped += 1 if skip else 0
        if ok and verbose:
            print(f"  [sword]   {basename} -> {dest_name}")

    extracted += extract_sword_combos_zip(z, out_dir, verbose, overwrite, written)
    return extracted, skipped, unmapped


def extract_sword_dir(
    src_dir: Path,
    out_dir: Path,
    verbose: bool,
    overwrite: bool,
) -> tuple[int, int, list[str]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    extracted, skipped, unmapped = 0, 0, []
    written: set[Path] = set()

    files = sorted(src_dir.rglob("*-Sheet.png"), key=lambda p: p.name)
    for src in files:
        basename = src.name
        if "Effect-Sheet.png" in basename:
            continue
        dest_name = resolve_sword_dest(basename)
        if dest_name is None:
            unmapped.append(basename)
            continue
        ok, skip = write_sheet(
            basename, src.read_bytes(), out_dir, dest_name, overwrite, written
        )
        extracted += 1 if ok else 0
        skipped += 1 if skip else 0
        if ok and verbose:
            print(f"  [sword]   {basename} -> {dest_name}")

    extracted += extract_sword_combos_dir(src_dir, out_dir, verbose, overwrite, written)
    return extracted, skipped, unmapped


def extract_pistol_zip(
    z: zipfile.ZipFile,
    out_dir: Path,
    verbose: bool,
    overwrite: bool,
) -> tuple[int, int, list[str]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    extracted, skipped, unmapped = 0, 0, []
    written: set[Path] = set()

    for entry in z.infolist():
        if not entry.filename.endswith("-Sheet.png"):
            continue
        if "003 Player Template Moves - Pistol" not in entry.filename:
            continue
        basename = entry.filename.split("/")[-1]
        dest_name = resolve_pistol_dest(basename)
        if dest_name is None:
            unmapped.append(basename)
            continue
        ok, skip = write_sheet(
            basename, z.read(entry.filename), out_dir, dest_name, overwrite, written
        )
        extracted += 1 if ok else 0
        skipped += 1 if skip else 0
        if ok and verbose:
            print(f"  [pistol]  {basename} -> {dest_name}")
    return extracted, skipped, unmapped


def extract_pistol_dir(
    src_dir: Path,
    out_dir: Path,
    verbose: bool,
    overwrite: bool,
) -> tuple[int, int, list[str]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    extracted, skipped, unmapped = 0, 0, []
    written: set[Path] = set()

    files = sorted(src_dir.rglob("*-Sheet.png"), key=lambda p: p.name)
    for src in files:
        basename = src.name
        dest_name = resolve_pistol_dest(basename)
        if dest_name is None:
            unmapped.append(basename)
            continue
        ok, skip = write_sheet(
            basename, src.read_bytes(), out_dir, dest_name, overwrite, written
        )
        extracted += 1 if ok else 0
        skipped += 1 if skip else 0
        if ok and verbose:
            print(f"  [pistol]  {basename} -> {dest_name}")
    return extracted, skipped, unmapped


def ensure_exists(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract animation sprite sheets.")
    parser.add_argument(
        "--zip1",
        default="C:/Users/asher/Downloads/001 Player Template Moves.zip",
        help="Path to unarmed ZIP (used when --unarmed-dir is not provided)",
    )
    parser.add_argument(
        "--zip2",
        default="C:/Users/asher/Downloads/002 Player Template Moves - Sword.zip",
        help="Path to sword/pistol ZIP (used when --sword-dir/--pistol-dir are not provided)",
    )
    parser.add_argument("--unarmed-dir", help="Path to extracted unarmed directory")
    parser.add_argument("--sword-dir", help="Path to extracted sword directory")
    parser.add_argument("--pistol-dir", help="Path to extracted pistol directory")
    parser.add_argument("--repo-root", default=".", help="Repository root directory")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    player_dir = repo_root / "assets" / "sprites" / "player"
    print(f"Extracting to: {player_dir}")

    # Unarmed source
    if args.unarmed_dir:
        src = Path(args.unarmed_dir)
        ensure_exists(src, "unarmed dir")
        ex, sk, um = extract_unarmed_dir(src, player_dir / "unarmed", args.verbose, args.overwrite)
    else:
        z1 = Path(args.zip1)
        ensure_exists(z1, "unarmed zip")
        with zipfile.ZipFile(z1) as z:
            ex, sk, um = extract_unarmed_zip(z, player_dir / "unarmed", args.verbose, args.overwrite)
    print(f"\nUnarmed: {ex} extracted, {sk} skipped, {len(um)} unmapped")
    if um:
        for n in sorted(set(um))[:10]:
            print(f"  UNMAPPED: {n}")
        if len(set(um)) > 10:
            print(f"  ... and {len(set(um)) - 10} more")

    # Sword source
    if args.sword_dir:
        src = Path(args.sword_dir)
        ensure_exists(src, "sword dir")
        ex, sk, um = extract_sword_dir(src, player_dir / "sword", args.verbose, args.overwrite)
    else:
        z2 = Path(args.zip2)
        ensure_exists(z2, "sword zip")
        with zipfile.ZipFile(z2) as z:
            ex, sk, um = extract_sword_zip(z, player_dir / "sword", args.verbose, args.overwrite)
    print(f"\nSword:   {ex} extracted, {sk} skipped, {len(um)} unmapped")
    if um:
        for n in sorted(set(um))[:10]:
            print(f"  UNMAPPED: {n}")
        if len(set(um)) > 10:
            print(f"  ... and {len(set(um)) - 10} more")

    # Pistol source
    if args.pistol_dir:
        src = Path(args.pistol_dir)
        ensure_exists(src, "pistol dir")
        ex, sk, um = extract_pistol_dir(src, player_dir / "pistol", args.verbose, args.overwrite)
    elif args.sword_dir:
        print("\nPistol:  skipped (no --pistol-dir provided)")
        ex, sk, um = 0, 0, []
    else:
        z2 = Path(args.zip2)
        ensure_exists(z2, "pistol zip")
        with zipfile.ZipFile(z2) as z:
            ex, sk, um = extract_pistol_zip(z, player_dir / "pistol", args.verbose, args.overwrite)
    if args.pistol_dir or not args.sword_dir:
        print(f"\nPistol:  {ex} extracted, {sk} skipped, {len(um)} unmapped")
        if um:
            for n in sorted(set(um))[:10]:
                print(f"  UNMAPPED: {n}")
            if len(set(um)) > 10:
                print(f"  ... and {len(set(um)) - 10} more")

    unarmed_count = len(list((player_dir / "unarmed").glob("*.png")))
    sword_count = len(list((player_dir / "sword").glob("*.png")))
    pistol_count = len(list((player_dir / "pistol").glob("*.png")))
    print(f"\nFinal counts: unarmed={unarmed_count} sword={sword_count} pistol={pistol_count}")
    print("Done.")


if __name__ == "__main__":
    main()
