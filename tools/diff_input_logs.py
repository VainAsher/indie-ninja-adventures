"""
Diff two input command logs (JSONL) produced by --log-input.

Usage:
    python tools/diff_input_logs.py path/to/record.log path/to/replay.log

Outputs first differing frame and a short summary of total frames/unique frames.
"""

import json
import sys
from pathlib import Path
from itertools import zip_longest


def load_log(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    if len(sys.argv) != 3:
        print("usage: python tools/diff_input_logs.py <record_log> <replay_log>")
        return 1

    rec_path = Path(sys.argv[1])
    rep_path = Path(sys.argv[2])

    rec = load_log(rec_path)
    rep = load_log(rep_path)

    first_diff = None
    for idx, (a, b) in enumerate(zip_longest(rec, rep, fillvalue=None)):
        if a != b:
            first_diff = (idx, a, b)
            break

    print(f"Record frames: {len(rec)}")
    print(f"Replay frames: {len(rep)}")

    if first_diff:
        idx, a, b = first_diff
        print(f"\nFirst difference at frame {idx}:")
        print(f"  record: {a}")
        print(f"  replay: {b}")
        return 1
    else:
        print("\nLogs match for all compared frames.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
