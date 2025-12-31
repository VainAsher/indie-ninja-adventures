"""
Game Clock System - Fixed timestep physics with variable render

Implements the Glenn Fiedler fixed timestep pattern:
- Physics runs at fixed 60Hz (deterministic)
- Rendering runs at variable rate with interpolation
- Prevents "spiral of death" with frame time clamping

Reference: https://gafferongames.com/post/fix_your_timestep/
"""

import time
import logging
from typing import Optional
from core.event_bus import EventBus, TickEvent, RenderEvent


class GameClock:
    """
    Fixed timestep physics with variable render (Glenn Fiedler pattern)

    Features:
    - Fixed 60Hz physics ticks for deterministic simulation
    - Variable render rate with interpolation alpha
    - Accumulator prevents spiral of death
    - Performance tracking (avg tick/render time)
    - Emits TickEvent and RenderEvent via event bus

    Usage:
        clock = GameClock(event_bus, logger)
        while running:
            clock.tick()
            event_bus.process()
    """

    PHYSICS_HZ = 60
    PHYSICS_DT = 1.0 / PHYSICS_HZ  # 0.01667s (~16.67ms)
    MAX_FRAME_TIME = 0.25  # Prevent spiral of death (250ms cap)

    def __init__(self, event_bus: EventBus, logger: Optional[logging.Logger] = None):
        """
        Initialize game clock

        Args:
            event_bus: Event bus for emitting tick/render events
            logger: Logger instance (optional)
        """
        self.event_bus = event_bus
        self.logger = logger

        self.accumulator = 0.0
        self.current_time = time.perf_counter()
        self.tick_count = 0
        self.frame_count = 0

        # Performance tracking
        self.avg_tick_time = 0.0
        self.avg_render_time = 0.0
        self._last_perf_log = 0.0

        if self.logger:
            self.logger.info(
                f"GameClock initialized: {self.PHYSICS_HZ}Hz physics "
                f"({self.PHYSICS_DT*1000:.2f}ms per tick)"
            )

    def tick(self) -> bool:
        """
        Update clock and emit tick/render events

        This should be called once per game loop iteration.
        Emits TickEvent(s) for fixed timestep physics and one RenderEvent.

        Returns:
            True if should continue, False if should quit (currently always True)
        """
        new_time = time.perf_counter()
        frame_time = new_time - self.current_time

        # Prevent spiral of death
        if frame_time > self.MAX_FRAME_TIME:
            if self.logger:
                self.logger.warning(
                    f"Frame time {frame_time*1000:.1f}ms exceeds max "
                    f"{self.MAX_FRAME_TIME*1000:.1f}ms, clamping"
                )
            frame_time = self.MAX_FRAME_TIME

        self.current_time = new_time
        self.accumulator += frame_time

        # Fixed timestep physics (may run 0, 1, or multiple times)
        tick_start = time.perf_counter()
        ticks_this_frame = 0

        while self.accumulator >= self.PHYSICS_DT:
            # Emit physics tick event
            tick_event = TickEvent(dt=self.PHYSICS_DT, tick_number=self.tick_count)
            tick_event.frame_number = self.frame_count
            self.event_bus.emit(tick_event, immediate=True)

            self.accumulator -= self.PHYSICS_DT
            self.tick_count += 1
            ticks_this_frame += 1

            # Safety: prevent infinite loop if physics is too slow
            if ticks_this_frame > 10:
                if self.logger:
                    self.logger.error(
                        f"Physics falling behind! {ticks_this_frame} ticks in one frame. "
                        f"Resetting accumulator."
                    )
                self.accumulator = 0.0
                break

        tick_elapsed = time.perf_counter() - tick_start
        self.avg_tick_time = 0.9 * self.avg_tick_time + 0.1 * tick_elapsed

        # Variable timestep render with interpolation alpha
        alpha = self.accumulator / self.PHYSICS_DT
        render_start = time.perf_counter()

        render_event = RenderEvent(dt=frame_time, alpha=alpha)
        render_event.frame_number = self.frame_count
        self.event_bus.emit(render_event, immediate=True)

        render_elapsed = time.perf_counter() - render_start
        self.avg_render_time = 0.9 * self.avg_render_time + 0.1 * render_elapsed

        self.frame_count += 1

        # Log performance periodically (every 5 seconds)
        if self.logger and (self.current_time - self._last_perf_log) >= 5.0:
            self._log_performance()
            self._last_perf_log = self.current_time

        return True

    def get_interpolation_alpha(self) -> float:
        """
        Get current interpolation factor for rendering

        Returns:
            Alpha value between 0.0 and 1.0 for state interpolation
        """
        return self.accumulator / self.PHYSICS_DT

    def get_current_tick(self) -> int:
        """Get current physics tick number"""
        return self.tick_count

    def get_current_frame(self) -> int:
        """Get current render frame number"""
        return self.frame_count

    def _log_performance(self):
        """Log performance statistics"""
        fps = self.frame_count / (self.current_time - (self.current_time - 5.0))
        self.logger.debug(
            f"Performance: "
            f"FPS={fps:.1f} "
            f"tick={self.avg_tick_time*1000:.2f}ms "
            f"render={self.avg_render_time*1000:.2f}ms "
            f"ticks={self.tick_count} "
            f"frames={self.frame_count}"
        )

    def reset(self):
        """Reset clock state (useful for testing)"""
        self.accumulator = 0.0
        self.current_time = time.perf_counter()
        self.tick_count = 0
        self.frame_count = 0
        self.avg_tick_time = 0.0
        self.avg_render_time = 0.0
        self._last_perf_log = 0.0

        if self.logger:
            self.logger.info("GameClock reset")


class Timer:
    """
    Countdown timer for mechanics

    Useful for cooldowns, buffers, and timed mechanics.
    Must be updated manually by calling update(dt).
    """

    def __init__(self, duration: float, callback: Optional[callable] = None):
        """
        Initialize timer

        Args:
            duration: Timer duration in seconds
            callback: Optional callback when timer expires
        """
        self.duration = duration
        self.remaining = 0.0
        self.callback = callback
        self.active = False

    def start(self, duration: Optional[float] = None):
        """
        Start/restart timer

        Args:
            duration: Optional new duration (uses default if not provided)
        """
        if duration is not None:
            self.duration = duration
        self.remaining = self.duration
        self.active = True

    def update(self, dt: float):
        """
        Update timer (call from tick handler)

        Args:
            dt: Delta time in seconds
        """
        if not self.active:
            return

        self.remaining = max(0.0, self.remaining - dt)
        if self.remaining == 0.0:
            self.active = False
            if self.callback:
                self.callback()

    def is_active(self) -> bool:
        """Check if timer is running"""
        return self.active and self.remaining > 0.0

    def get_remaining(self) -> float:
        """Get remaining time in seconds"""
        return self.remaining

    def get_progress(self) -> float:
        """Get progress as ratio (0.0 to 1.0)"""
        if self.duration == 0.0:
            return 1.0
        return 1.0 - (self.remaining / self.duration)

    def reset(self):
        """Reset timer to inactive state"""
        self.remaining = 0.0
        self.active = False

    def __bool__(self) -> bool:
        """Allow timer to be used in boolean context"""
        return self.is_active()
