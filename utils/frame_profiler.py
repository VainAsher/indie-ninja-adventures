"""
Frame Profiler — lightweight per-section timer for performance analysis.

Usage:
    profiler = FrameProfiler(enabled=True, csv_path="docs/perf_baseline.csv")

    # Around each section in the game loop:
    profiler.begin("collision")
    collision_system.update(...)
    profiler.end("collision")

    # At end of every frame:
    profiler.frame()          # records all sections, writes CSV row

    # On exit:
    profiler.close()          # flushes and closes CSV

Design goals:
- Uses time.perf_counter() — nanosecond resolution, no GC pressure
- Writes CSV incrementally (no in-memory accumulation of 10,000+ rows)
- Zero overhead when enabled=False (all methods are no-ops via early return)
- Thread-safe: single-threaded game loop assumed, no locks needed
"""

import csv
import time
from collections import defaultdict
from pathlib import Path


class FrameProfiler:
    """
    Lightweight frame-level profiler.  Measures wall-clock time for named
    sections within each frame and writes results to CSV for offline analysis.
    """

    def __init__(self, enabled: bool = True, csv_path: str = "docs/perf_baseline.csv"):
        self.enabled = enabled
        self._starts: dict[str, float] = {}
        self._frame_data: dict[str, float] = defaultdict(float)
        self._frame_count: int = 0
        self._frame_start: float = 0.0
        self._csv_path = csv_path
        self._file = None
        self._writer = None

        # Section names in order for CSV columns
        self._sections = [
            "frame_total",
            "update",
            "physics",
            "collision",
            "enemy_manager",
            "ai",
            "render",
            "render_tiles",
            "render_particles",
            "render_hazards",
            "render_pickups",
            "render_portals",
            "render_enemies",
            "render_npcs",
            "render_player",
            "render_companions",
            "render_projectiles",
            "render_hud",
            "present",
        ]

        if enabled:
            Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
            self._file = open(csv_path, "w", newline="", encoding="utf-8")
            self._writer = csv.writer(self._file)
            header = ["frame"] + self._sections + ["fps_instantaneous"]
            self._writer.writerow(header)

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def begin_frame(self) -> None:
        """Call at the very start of each frame."""
        if not self.enabled:
            return
        self._frame_start = time.perf_counter()
        self._frame_data.clear()

    def end_frame(self) -> None:
        """Call at the very end of each frame (after present).  Writes CSV row."""
        if not self.enabled:
            return
        now = time.perf_counter()
        frame_ms = (now - self._frame_start) * 1000.0
        self._frame_data["frame_total"] = frame_ms
        fps = 1000.0 / frame_ms if frame_ms > 0 else 0.0

        row = [self._frame_count]
        for sec in self._sections:
            row.append(round(self._frame_data.get(sec, 0.0), 4))
        row.append(round(fps, 2))

        self._writer.writerow(row)
        self._frame_count += 1

        # Flush every 60 frames so data is readable mid-run
        if self._frame_count % 60 == 0:
            self._file.flush()

    def begin(self, section: str) -> None:
        """Mark the start of a named section."""
        if not self.enabled:
            return
        self._starts[section] = time.perf_counter()

    def end(self, section: str) -> None:
        """Mark the end of a named section; accumulates if called multiple times."""
        if not self.enabled:
            return
        start = self._starts.get(section)
        if start is None:
            return
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self._frame_data[section] = self._frame_data.get(section, 0.0) + elapsed_ms

    def close(self) -> None:
        """Flush and close the CSV file."""
        if not self.enabled or self._file is None:
            return
        self._file.flush()
        self._file.close()
        self._file = None
        print(f"[PROFILER] Wrote {self._frame_count} frames to {self._csv_path}")

    # ------------------------------------------------------------------
    # Reporting helpers (print to console for quick inspection)
    # ------------------------------------------------------------------

    def print_summary(self, last_n: int = 300) -> None:
        """
        Re-read the CSV and print per-section avg/max over the last N frames.
        Call this on exit.
        """
        if not self.enabled:
            return
        try:
            import statistics

            with open(self._csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            if not rows:
                print("[PROFILER] No data collected.")
                return

            rows = rows[-last_n:]  # last N frames
            print(f"\n{'='*60}")
            print(f"FRAME PROFILER SUMMARY — last {len(rows)} frames")
            print(f"{'='*60}")

            section_names = [c for c in rows[0].keys() if c not in ("frame", "fps_instantaneous")]

            for sec in section_names:
                values = [float(r[sec]) for r in rows if float(r[sec]) > 0]
                if not values:
                    continue
                avg = statistics.mean(values)
                p95 = sorted(values)[int(len(values) * 0.95)]
                mx = max(values)
                print(f"  {sec:<20s}  avg={avg:6.2f}ms  p95={p95:6.2f}ms  max={mx:6.2f}ms")

            fps_vals = [float(r["fps_instantaneous"]) for r in rows]
            avg_fps = statistics.mean(fps_vals)
            min_fps = min(fps_vals)
            p5_fps = sorted(fps_vals)[int(len(fps_vals) * 0.05)]
            print(f"\n  FPS  avg={avg_fps:.1f}  p5={p5_fps:.1f}  min={min_fps:.1f}")
            print(f"{'='*60}\n")

        except Exception as exc:
            print(f"[PROFILER] Summary failed: {exc}")
