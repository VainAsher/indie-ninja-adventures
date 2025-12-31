"""
Event Bus System - Central pub/sub event system for decoupled communication

This module provides a thread-safe event bus with priority-based event handling,
supporting all game events from physics ticks to player actions.
"""

import time
import threading
from typing import Dict, List, Callable, Type, Deque, Optional
from collections import defaultdict, deque
from dataclasses import dataclass


# ============================================================================
# Event Base Classes
# ============================================================================

class Event:
    """Base event class with timestamp"""
    def __init__(self):
        self.timestamp = time.time()
        self.frame_number = 0  # Set by clock system


# ============================================================================
# Timing Events
# ============================================================================

@dataclass
class TickEvent(Event):
    """Fixed timestep physics tick (60Hz)"""
    dt: float  # Always 1/60 for determinism
    tick_number: int

    def __init__(self, dt: float, tick_number: int):
        super().__init__()
        self.dt = dt
        self.tick_number = tick_number


@dataclass
class RenderEvent(Event):
    """Variable timestep render event"""
    dt: float  # Time since last render
    alpha: float  # Interpolation factor (0-1)

    def __init__(self, dt: float, alpha: float):
        super().__init__()
        self.dt = dt
        self.alpha = alpha


# ============================================================================
# Input Events
# ============================================================================

@dataclass
class InputCommandEvent(Event):
    """Player input command (network-ready)"""
    player_id: int
    command: 'InputCommand'  # Forward reference

    def __init__(self, player_id: int, command):
        super().__init__()
        self.player_id = player_id
        self.command = command


# ============================================================================
# Physics Events
# ============================================================================

@dataclass
class CollisionEvent(Event):
    """Collision between entity and tile"""
    entity_id: int
    collision_type: str  # 'ground', 'wall_left', 'wall_right', 'ceiling'
    normal: tuple  # Collision normal vector (nx, ny)
    tile_rect: Optional[object] = None  # pygame.Rect

    def __init__(self, entity_id: int, collision_type: str,
                 normal: tuple, tile_rect=None):
        super().__init__()
        self.entity_id = entity_id
        self.collision_type = collision_type
        self.normal = normal
        self.tile_rect = tile_rect


@dataclass
class VelocityChangeEvent(Event):
    """Velocity modification (for logging/debugging)"""
    entity_id: int
    old_vx: float
    old_vy: float
    new_vx: float
    new_vy: float
    reason: str  # e.g., "jump", "dash", "collision"

    def __init__(self, entity_id: int, old_vx: float, old_vy: float,
                 new_vx: float, new_vy: float, reason: str):
        super().__init__()
        self.entity_id = entity_id
        self.old_vx = old_vx
        self.old_vy = old_vy
        self.new_vx = new_vx
        self.new_vy = new_vy
        self.reason = reason


# ============================================================================
# Game Events
# ============================================================================

@dataclass
class PickupCollectedEvent(Event):
    """Pickup item collected"""
    player_id: int
    pickup_type: str  # 'coin', 'health', 'life'
    value: int

    def __init__(self, player_id: int, pickup_type: str, value: int):
        super().__init__()
        self.player_id = player_id
        self.pickup_type = pickup_type
        self.value = value


@dataclass
class PlayerDamagedEvent(Event):
    """Player took damage"""
    player_id: int
    damage: int
    source: str  # 'hazard', 'enemy', etc.

    def __init__(self, player_id: int, damage: int, source: str):
        super().__init__()
        self.player_id = player_id
        self.damage = damage
        self.source = source


@dataclass
class StateTransitionEvent(Event):
    """State machine transition"""
    from_state: str
    to_state: str

    def __init__(self, from_state: str, to_state: str):
        super().__init__()
        self.from_state = from_state
        self.to_state = to_state


# ============================================================================
# Event Bus Implementation
# ============================================================================

class EventBus:
    """
    Thread-safe event bus with priority queues

    Features:
    - Type-safe subscription by event class
    - Priority-based handler execution (higher = earlier)
    - Queue-based processing for deterministic ordering
    - Thread-safe for networking

    Usage:
        bus = EventBus(logger)
        bus.subscribe(TickEvent, my_handler, priority=10)
        bus.emit(TickEvent(dt=0.0167, tick_number=123))
        bus.process()  # Call once per frame to dispatch all events
    """

    def __init__(self, logger=None):
        self.subscribers: Dict[Type[Event], List[tuple]] = defaultdict(list)
        self.event_queue: Deque[Event] = deque()
        self.logger = logger
        self._lock = threading.Lock()
        self._stats = defaultdict(int)  # Event type -> count

    def subscribe(self, event_type: Type[Event], handler: Callable, priority: int = 0):
        """
        Subscribe to event type with optional priority (higher = earlier)

        Args:
            event_type: Event class to subscribe to
            handler: Callable that takes event as parameter
            priority: Handler priority (default 0, higher executes first)
        """
        with self._lock:
            self.subscribers[event_type].append((priority, handler))
            # Sort by priority descending
            self.subscribers[event_type].sort(key=lambda x: x[0], reverse=True)

            if self.logger:
                self.logger.debug(
                    f"Subscribed {handler.__name__} to {event_type.__name__} "
                    f"(priority {priority})"
                )

    def unsubscribe(self, event_type: Type[Event], handler: Callable):
        """
        Unsubscribe from event type

        Args:
            event_type: Event class to unsubscribe from
            handler: Handler to remove
        """
        with self._lock:
            original_count = len(self.subscribers[event_type])
            self.subscribers[event_type] = [
                (p, h) for p, h in self.subscribers[event_type] if h != handler
            ]
            removed = original_count - len(self.subscribers[event_type])

            if self.logger and removed > 0:
                self.logger.debug(
                    f"Unsubscribed {handler.__name__} from {event_type.__name__}"
                )

    def emit(self, event: Event, immediate: bool = False):
        """
        Emit event (queued by default, immediate optional)

        Args:
            event: Event instance to emit
            immediate: If True, dispatch immediately (bypasses queue)
        """
        if immediate:
            self._dispatch(event)
        else:
            with self._lock:
                self.event_queue.append(event)

    def process(self):
        """
        Process all queued events (call once per frame)

        This method dispatches all queued events to their subscribers in FIFO order.
        Should be called once per game loop iteration.
        """
        # Atomically swap out the queue
        with self._lock:
            events = list(self.event_queue)
            self.event_queue.clear()

        # Dispatch without holding lock
        for event in events:
            self._dispatch(event)

    def _dispatch(self, event: Event):
        """
        Dispatch event to subscribers

        Args:
            event: Event to dispatch
        """
        event_type = type(event)
        handlers = self.subscribers.get(event_type, [])

        # Update stats
        self._stats[event_type.__name__] += 1

        if self.logger:
            self.logger.debug(
                f"Dispatching {event_type.__name__} to {len(handlers)} handlers"
            )

        for priority, handler in handlers:
            try:
                handler(event)
            except Exception as e:
                if self.logger:
                    self.logger.error(
                        f"Error in event handler {handler.__name__} "
                        f"for {event_type.__name__}: {e}",
                        exc_info=True
                    )
                else:
                    # If no logger, re-raise to avoid silent failures
                    raise

    def get_stats(self) -> Dict[str, int]:
        """Get event dispatch statistics"""
        return dict(self._stats)

    def reset_stats(self):
        """Reset event statistics"""
        self._stats.clear()

    def get_subscriber_count(self, event_type: Type[Event]) -> int:
        """Get number of subscribers for an event type"""
        return len(self.subscribers.get(event_type, []))

    def create_tick_event(self, dt: float, tick_number: int = 0) -> 'TickEvent':
        """
        Helper to create a TickEvent

        Args:
            dt: Delta time
            tick_number: Optional tick number

        Returns:
            TickEvent instance
        """
        return TickEvent(dt=dt, tick_number=tick_number)

    def clear_all_subscribers(self):
        """Clear all event subscribers (use with caution)"""
        with self._lock:
            self.subscribers.clear()
            if self.logger:
                self.logger.warning("Cleared all event subscribers")
