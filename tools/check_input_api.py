"""
Quick check to prevent new direct uses of pygame.key.get_pressed outside approved files.

Usage:
    python tools/check_input_api.py

Allowed files: demo_game.py (entry point) and network/input_pipeline.py (input wiring).
"""

import sys
from pathlib import Path


ALLOWED = {
    Path("demo_game.py").resolve(),
    Path("network/input_pipeline.py").resolve(),
    Path("ui/menu_system.py").resolve(),        # interface docs mention get_pressed
    Path("ui/tutorial_system.py").resolve(),    # interface docs mention get_pressed
    Path("entities/player.py").resolve(),       # docstring references get_pressed
    Path("legacy/main.py").resolve(),           # legacy entrypoint
    Path(__file__).resolve(),                   # this checker references get_pressed
}


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    violations = []
    for path in repo_root.rglob("*.py"):
        # Skip virtual envs or caches
        if ".venv" in path.parts or "__pycache__" in path.parts:
            continue
        if path.resolve() in ALLOWED:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "pygame.key.get_pressed" in text:
            violations.append(path.relative_to(repo_root))

    if violations:
        print("[INPUT CHECK] Direct pygame.key.get_pressed usage found in:")
        for v in violations:
            print(f"  - {v}")
        print("\nUse InputPipeline keys/commands instead.")
        return 1

    print("[INPUT CHECK] OK - no raw get_pressed usage outside approved files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
