"""
Ninjutsu Mechanic - Stance/select/cast with Purify effect.
"""

from config.physics_constants import TILE_SIZE
from core.event_bus import EventBus
from core.logger import MechanicLogger
from core.state import PlayerState
from mechanics.base import BaseMechanic


class NinjutsuMechanic(BaseMechanic):
    PURIFY_COOLDOWN = 12.0
    PURIFY_CAST_TIME = 0.4
    PURIFY_MANA_COST = 25.0
    PURIFY_RADIUS_TILES = 5

    def __init__(
        self, entity_id: int, event_bus: EventBus, logger: MechanicLogger, hazard_manager=None
    ):
        super().__init__(entity_id, event_bus, logger)
        self.hazard_manager = hazard_manager
        self.stance_requested = False
        self.cast_requested = False
        self.selected = "purify"

    def set_hazard_manager(self, hazard_manager):
        self.hazard_manager = hazard_manager

    def request_stance(self):
        self.stance_requested = True

    def request_cast(self, selected: str | None = None):
        self.cast_requested = True
        if selected:
            self.selected = selected

    def on_tick(self, state: PlayerState, dt: float):
        if not self.enabled:
            return

        # Cooldowns tick
        cd = state.ninjutsu_cooldowns.get(self.selected, 0.0)
        if cd > 0.0:
            cd = max(0.0, cd - dt)
            state.ninjutsu_cooldowns[self.selected] = cd

        # Casting in progress
        if state.ninjutsu_casting:
            state.ninjutsu_casting = state.ninjutsu_casting and False  # reset if overriden

        # Stance tracking
        if self.stance_requested:
            state.ninjutsu_active = True
        else:
            state.ninjutsu_active = False
        self.stance_requested = False

        # Cast handling
        if self.cast_requested:
            self.cast_requested = False
            if self.selected == "purify":
                self._cast_purify(state)

    def _cast_purify(self, state: PlayerState):
        current_cd = state.ninjutsu_cooldowns.get("purify", 0.0)
        if current_cd > 0.0:
            return
        if state.mana < self.PURIFY_MANA_COST:
            return
        state.mana = max(0.0, state.mana - self.PURIFY_MANA_COST)
        state.ninjutsu_casting = True
        state.ninjutsu_selected = "purify"
        state.ninjutsu_cooldowns["purify"] = self.PURIFY_COOLDOWN
        # Clear hazard (permanent)
        if self.hazard_manager:
            radius_px = self.PURIFY_RADIUS_TILES * TILE_SIZE
            self.hazard_manager.clear_poison_area(state.physics.x, state.physics.y, radius_px)
        state.ninjutsu_casting = False

    def can_activate(self, state: PlayerState) -> bool:
        if not self.enabled:
            return False
        cd = (
            state.ninjutsu_cooldowns.get("purify", 0.0)
            if isinstance(state.ninjutsu_cooldowns, dict)
            else 0.0
        )
        return cd <= 0.0 and state.mana >= self.PURIFY_MANA_COST

    def reset(self, state: PlayerState):
        self.stance_requested = False
        self.cast_requested = False
        state.ninjutsu_active = False
        state.ninjutsu_casting = False
        state.ninjutsu_cooldowns = {}
