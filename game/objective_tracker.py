"""
Objective Tracker - Mission Objective Tracking System

This module provides objective tracking for missions:
- 6 objective types: kill enemies, collect items, activate switches,
  reach location, time challenge, defeat boss
- Event-based progress tracking
- Objective completion detection
- Integration with mission manager

Version: v0.6.0
"""

from dataclasses import dataclass, field

from core import EventBus
from core.event_bus import TickEvent
from game.mission_registry import ObjectiveType, get_mission_registry

# ============================================================
# Objective Events (to subscribe to)
# ============================================================


@dataclass
class EnemyDeathEvent:
    """Event emitted when enemy dies"""

    enemy_id: str
    enemy_type: str
    position: tuple[float, float]


@dataclass
class ItemCollectedEvent:
    """Event emitted when item is collected"""

    item_id: str
    quantity: int
    position: tuple[float, float]


@dataclass
class SwitchActivatedEvent:
    """Event emitted when switch is activated"""

    switch_id: str
    position: tuple[float, float]


@dataclass
class BossDeathEvent:
    """Event emitted when boss dies"""

    boss_id: str
    boss_type: str
    position: tuple[float, float]


@dataclass
class PlayerPositionUpdateEvent:
    """Event emitted when player moves (for reach location objectives)"""

    player_x: float
    player_y: float


# ============================================================
# Objective State Tracking
# ============================================================


@dataclass
class ObjectiveState:
    """
    State tracking for a single objective.

    Tracks progress towards objective completion.
    """

    objective_id: str
    objective_type: ObjectiveType
    target_value: int  # Target count (enemies to kill, items to collect, etc.)
    location_id: str | None = None
    item_id: str | None = None
    boss_id: str | None = None
    current_value: int = 0  # Current progress
    is_complete: bool = False

    # Type-specific tracking
    tracked_entity_ids: set[str] = field(default_factory=set)  # For switches, specific enemies
    target_position: tuple[float, float] | None = None  # For reach location
    target_radius: float = 100.0  # For reach location

    # Time challenge tracking
    time_limit_seconds: float | None = None
    elapsed_time: float = 0.0

    def update_progress(self, increment: int = 1) -> bool:
        """
        Update objective progress.

        Args:
            increment: Amount to increment progress

        Returns:
            True if objective just completed
        """
        if self.is_complete:
            return False

        self.current_value += increment

        # Check if complete
        if self.current_value >= self.target_value:
            self.is_complete = True
            return True

        return False

    def check_location_reached(self, player_x: float, player_y: float) -> bool:
        """
        Check if player reached target location.

        Args:
            player_x: Player X position
            player_y: Player Y position

        Returns:
            True if location reached
        """
        if self.target_position is None:
            return False

        # Calculate distance
        dx = player_x - self.target_position[0]
        dy = player_y - self.target_position[1]
        distance = (dx * dx + dy * dy) ** 0.5

        return distance <= self.target_radius

    def check_time_limit(self) -> bool:
        """
        Check if time limit exceeded.

        Returns:
            True if time limit exceeded (mission failed)
        """
        if self.time_limit_seconds is None:
            return False

        return self.elapsed_time > self.time_limit_seconds

    def get_remaining_time(self) -> float | None:
        """Get remaining time for time challenge"""
        if self.time_limit_seconds is None:
            return None

        remaining = self.time_limit_seconds - self.elapsed_time
        return max(0.0, remaining)

    def get_progress_ratio(self) -> float:
        """Get progress as ratio (0.0 to 1.0)"""
        if self.target_value == 0:
            return 1.0
        return min(1.0, self.current_value / self.target_value)


# ============================================================
# Objective Tracker
# ============================================================


class ObjectiveTracker:
    """
    Tracks objectives for active mission.

    Subscribes to game events and updates objective progress.
    """

    def __init__(self, event_bus: EventBus):
        """
        Initialize objective tracker.

        Args:
            event_bus: Event bus for subscribing to events
        """
        self.event_bus = event_bus
        self.active_mission_id: str | None = None
        self.objectives: dict[str, ObjectiveState] = {}

        # Subscribe to events
        self._subscribe_to_events()

    def _subscribe_to_events(self):
        """Subscribe to game events"""
        self.event_bus.subscribe(TickEvent, self._on_tick)
        self.event_bus.subscribe(EnemyDeathEvent, self._on_enemy_death)
        self.event_bus.subscribe(ItemCollectedEvent, self._on_item_collected)
        self.event_bus.subscribe(SwitchActivatedEvent, self._on_switch_activated)
        self.event_bus.subscribe(BossDeathEvent, self._on_boss_death)
        self.event_bus.subscribe(PlayerPositionUpdateEvent, self._on_player_position_update)

    def start_mission_objectives(self, mission_id: str):
        """
        Start tracking objectives for a mission.

        Args:
            mission_id: Mission identifier
        """
        # Get mission definition
        mission_registry = get_mission_registry()
        mission_def = mission_registry.get_mission(mission_id)

        if mission_def is None:
            print(f"[ERROR] Mission not found: {mission_id}")
            return

        # Clear previous objectives
        self.objectives.clear()

        # Set active mission
        self.active_mission_id = mission_id

        # Create objective states
        for i, obj_def in enumerate(mission_def.objectives):
            obj_id = f"{mission_id}_obj_{i}"

            # Derive target count from mission data (supports multiple schema variants)
            base_target = (
                obj_def.count if getattr(obj_def, "count", None) is not None else obj_def.target
            )
            target_value = base_target if base_target is not None else 1

            obj_state = ObjectiveState(
                objective_id=obj_id,
                objective_type=obj_def.objective_type,
                target_value=target_value,
                location_id=obj_def.location,
                item_id=obj_def.item,
                boss_id=obj_def.boss,
            )

            # Type-specific initialization
            if obj_def.objective_type == ObjectiveType.REACH_LOCATION:
                obj_state.target_position = None
                obj_state.target_radius = 100.0

            elif obj_def.objective_type == ObjectiveType.TIME_CHALLENGE:
                # Use time_limit from objective definition
                if obj_def.time_limit is not None:
                    obj_state.time_limit_seconds = obj_def.time_limit
                elif mission_def.time_limit is not None:
                    obj_state.time_limit_seconds = mission_def.time_limit

            elif obj_def.objective_type == ObjectiveType.ACTIVATE_SWITCHES:
                # Track specific switch IDs if provided
                # In a real implementation, this would track specific switches
                pass

            self.objectives[obj_id] = obj_state

        print(f"[OBJECTIVES] Started tracking {len(self.objectives)} objectives for {mission_id}")

    def stop_mission_objectives(self):
        """Stop tracking objectives (mission ended)"""
        self.active_mission_id = None
        self.objectives.clear()

    def set_location_targets(
        self,
        targets: dict[str, tuple[float, float]],
        default_radius: float = 100.0,
        fallback_id: str | None = None,
    ):
        """
        Resolve reach-location objectives to concrete positions.

        Args:
            targets: Mapping of location_id -> (x, y) in pixels
            default_radius: Radius for reach check
            fallback_id: Optional location_id to use if specific target missing
        """
        for obj in self.objectives.values():
            if obj.objective_type != ObjectiveType.REACH_LOCATION:
                continue

            target_id = obj.location_id or fallback_id
            target_pos = targets.get(target_id) if target_id else None

            if target_pos is None and fallback_id:
                target_pos = targets.get(fallback_id)

            if target_pos:
                obj.target_position = target_pos
                obj.target_radius = default_radius

    def get_active_objectives(self) -> list[ObjectiveState]:
        """Get list of active objectives"""
        return list(self.objectives.values())

    def get_incomplete_objectives(self) -> list[ObjectiveState]:
        """Get list of incomplete objectives"""
        return [obj for obj in self.objectives.values() if not obj.is_complete]

    def get_complete_objectives(self) -> list[ObjectiveState]:
        """Get list of complete objectives"""
        return [obj for obj in self.objectives.values() if obj.is_complete]

    def are_all_objectives_complete(self) -> bool:
        """Check if all objectives are complete"""
        if not self.objectives:
            return False
        return all(obj.is_complete for obj in self.objectives.values())

    def get_objective_progress(self, objective_id: str) -> ObjectiveState | None:
        """Get objective state by ID"""
        return self.objectives.get(objective_id)

    def update(self, dt: float):
        """
        Update time-based objectives.

        Args:
            dt: Delta time in seconds
        """
        # Check time challenge objectives
        for obj in self.objectives.values():
            if obj.objective_type == ObjectiveType.TIME_CHALLENGE:
                if obj.is_complete:
                    continue

                obj.elapsed_time += dt

                if obj.check_time_limit():
                    # Time limit exceeded
                    print("[OBJECTIVE] Time limit exceeded!")
                    # Note: Mission manager should handle failure

    def _on_tick(self, event: TickEvent):
        """Advance time-based objectives on fixed ticks."""
        if self.active_mission_id is None:
            return
        self.update(event.dt)

    # ============================================================
    # Event Handlers
    # ============================================================

    def _on_enemy_death(self, event: EnemyDeathEvent):
        """Handle enemy death event"""
        if self.active_mission_id is None:
            return

        # Update kill objectives
        for obj in self.objectives.values():
            if obj.objective_type == ObjectiveType.KILL_ALL_ENEMIES and not obj.is_complete:
                # Check if specific enemy type is required
                just_completed = obj.update_progress(1)

                if just_completed:
                    self._on_objective_complete(obj)

    def _on_item_collected(self, event: ItemCollectedEvent):
        """Handle item collection event"""
        if self.active_mission_id is None:
            return

        # Update collect objectives
        for obj in self.objectives.values():
            if obj.objective_type == ObjectiveType.COLLECT_ITEMS and not obj.is_complete:
                # Check if specific item is required
                if obj.item_id and obj.item_id != event.item_id:
                    continue
                just_completed = obj.update_progress(event.quantity)

                if just_completed:
                    self._on_objective_complete(obj)

    def _on_switch_activated(self, event: SwitchActivatedEvent):
        """Handle switch activation event"""
        if self.active_mission_id is None:
            return

        # Update switch objectives
        for obj in self.objectives.values():
            if obj.objective_type == ObjectiveType.ACTIVATE_SWITCHES and not obj.is_complete:
                # Check if this switch is tracked
                if obj.tracked_entity_ids:
                    # Specific switches required
                    if event.switch_id in obj.tracked_entity_ids:
                        just_completed = obj.update_progress(1)
                        if just_completed:
                            self._on_objective_complete(obj)
                else:
                    # Any switch counts
                    just_completed = obj.update_progress(1)
                    if just_completed:
                        self._on_objective_complete(obj)

    def _on_boss_death(self, event: BossDeathEvent):
        """Handle boss death event"""
        if self.active_mission_id is None:
            return

        # Update boss objectives
        for obj in self.objectives.values():
            if obj.objective_type == ObjectiveType.DEFEAT_BOSS and not obj.is_complete:
                if obj.boss_id and obj.boss_id not in (event.boss_id, event.boss_type):
                    continue
                just_completed = obj.update_progress(1)

                if just_completed:
                    self._on_objective_complete(obj)

    def _on_player_position_update(self, event: PlayerPositionUpdateEvent):
        """Handle player position update event"""
        if self.active_mission_id is None:
            return

        # Update reach location objectives
        for obj in self.objectives.values():
            if obj.objective_type == ObjectiveType.REACH_LOCATION and not obj.is_complete:
                if obj.check_location_reached(event.player_x, event.player_y):
                    obj.is_complete = True
                    obj.current_value = obj.target_value
                    self._on_objective_complete(obj)

    def _on_objective_complete(self, obj: ObjectiveState):
        """
        Handle objective completion.

        Args:
            obj: Completed objective state
        """
        # Get mission definition for description
        mission_registry = get_mission_registry()
        mission_def = mission_registry.get_mission(self.active_mission_id)

        if mission_def:
            # Find objective definition
            obj_index = int(obj.objective_id.split("_")[-1])
            if obj_index < len(mission_def.objectives):
                obj_def = mission_def.objectives[obj_index]
                description = obj_def.description
            else:
                description = "Unknown objective"
        else:
            description = "Unknown objective"

        print(f"[OBJECTIVE] Completed: {description}")

        # Import here to avoid circular dependency
        from game.mission_manager import get_mission_manager

        # Notify mission manager
        mission_manager = get_mission_manager()
        if mission_manager:
            mission_manager.complete_objective(
                self.active_mission_id, obj.objective_id, description
            )

            # Check if all objectives complete
            if self.are_all_objectives_complete():
                mission_manager.unlock_exit(self.active_mission_id)


# ============================================================
# Objective Display Helpers
# ============================================================


def get_objective_display_text(objective: ObjectiveState, mission_id: str) -> str:
    """
    Get display text for objective.

    Args:
        objective: Objective state
        mission_id: Mission identifier

    Returns:
        Display text string
    """
    # Get mission definition
    mission_registry = get_mission_registry()
    mission_def = mission_registry.get_mission(mission_id)

    if mission_def is None:
        return "Unknown objective"

    # Find objective definition
    obj_index = int(objective.objective_id.split("_")[-1])
    if obj_index >= len(mission_def.objectives):
        return "Unknown objective"

    obj_def = mission_def.objectives[obj_index]

    # Format based on type
    if objective.objective_type == ObjectiveType.KILL_ALL_ENEMIES:
        return f"{obj_def.description} ({objective.current_value}/{objective.target_value})"

    elif objective.objective_type == ObjectiveType.COLLECT_ITEMS:
        return f"{obj_def.description} ({objective.current_value}/{objective.target_value})"

    elif objective.objective_type == ObjectiveType.ACTIVATE_SWITCHES:
        return f"{obj_def.description} ({objective.current_value}/{objective.target_value})"

    elif objective.objective_type == ObjectiveType.REACH_LOCATION:
        status = "Complete" if objective.is_complete else "In Progress"
        return f"{obj_def.description} - {status}"

    elif objective.objective_type == ObjectiveType.TIME_CHALLENGE:
        remaining = objective.get_remaining_time()
        if remaining is not None:
            return f"{obj_def.description} - {remaining:.1f}s remaining"
        else:
            return obj_def.description

    elif objective.objective_type == ObjectiveType.DEFEAT_BOSS:
        status = "Complete" if objective.is_complete else "In Progress"
        return f"{obj_def.description} - {status}"

    return obj_def.description


def get_objective_icon(objective_type: ObjectiveType) -> str:
    """
    Get icon/symbol for objective type.

    Args:
        objective_type: Objective type

    Returns:
        Icon character
    """
    icons = {
        ObjectiveType.KILL_ALL_ENEMIES: "[X]",
        ObjectiveType.COLLECT_ITEMS: "[*]",
        ObjectiveType.ACTIVATE_SWITCHES: "[S]",
        ObjectiveType.REACH_LOCATION: "[->]",
        ObjectiveType.TIME_CHALLENGE: "[T]",
        ObjectiveType.DEFEAT_BOSS: "[B]",
    }

    return icons.get(objective_type, "[?]")


# ============================================================
# Global Objective Tracker Instance
# ============================================================

_objective_tracker: ObjectiveTracker | None = None


def initialize_objective_tracker(event_bus: EventBus):
    """Initialize the global objective tracker"""
    global _objective_tracker
    _objective_tracker = ObjectiveTracker(event_bus)


def get_objective_tracker() -> ObjectiveTracker | None:
    """Get the global objective tracker instance"""
    return _objective_tracker
