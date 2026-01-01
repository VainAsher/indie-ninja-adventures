"""
State Management - Network-serializable game state

Provides data structures for complete game state with:
- JSON serialization/deserialization
- Network transmission ready
- Deterministic state snapshots
- Support for rollback and replay
"""

from dataclasses import dataclass, field

import pygame

# Import health system
from game.health_system import HealthState

# ============================================================================
# Physics State
# ============================================================================


@dataclass
class PhysicsState:
    """
    Physics state for an entity (network-serializable)

    Contains position, velocity, and collision state for deterministic physics.
    """

    x: float
    y: float
    vx: float
    vy: float
    width: int
    height: int

    # Collision flags
    on_ground: bool = False
    on_wall: bool = False
    wall_dir: int = 0  # -1 left, 1 right, 0 none

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            "x": self.x,
            "y": self.y,
            "vx": self.vx,
            "vy": self.vy,
            "width": self.width,
            "height": self.height,
            "on_ground": self.on_ground,
            "on_wall": self.on_wall,
            "wall_dir": self.wall_dir,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PhysicsState":
        """Deserialize from dictionary"""
        return cls(**data)

    def get_rect(self) -> pygame.Rect:
        """Get pygame.Rect for collision detection"""
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def set_position(self, x: float, y: float):
        """Update position"""
        self.x = x
        self.y = y

    def set_velocity(self, vx: float, vy: float):
        """Update velocity"""
        self.vx = vx
        self.vy = vy


# ============================================================================
# Player State
# ============================================================================


@dataclass
class PlayerState:
    """
    Complete player state (network-serializable)

    Contains all player data needed for deterministic simulation and
    network synchronization.
    """

    player_id: int
    physics: PhysicsState

    # Health state (using HealthState system)
    health_state: HealthState = field(default_factory=lambda: HealthState(current_hp=3, max_hp=3))

    # Movement state
    facing: int = 1  # -1 left, 1 right
    crouching: bool = False
    is_dashing: bool = False
    is_throwing: bool = False
    throw_cooldown: float = 0.0
    is_slow_walking: bool = False
    is_running: bool = False

    # Combat/attack state
    attack_stage: int = 0
    attack_timer: float = 0.0
    is_air_attacking: bool = False

    # Teleport/Ninjutsu state
    is_teleporting_phase: bool = False
    teleport_cooldown: float = 0.0
    teleport_cast_time: float = 0.0
    is_teleporting_invuln: bool = False
    ninjutsu_active: bool = False
    ninjutsu_casting: bool = False
    ninjutsu_selected: str = ""
    ninjutsu_cooldowns: dict = field(default_factory=dict)

    # Resources
    stamina: float = 0.0
    stamina_max: float = 0.0
    stamina_regen_rate: float = 0.0
    mana: float = 0.0
    mana_max: float = 0.0
    mana_regen_rate: float = 0.0

    # Shuriken ammo
    shuriken_ammo: int = 0
    shuriken_max: int = 0

    # Timers (store remaining time for serialization)
    coyote_time: float = 0.0
    jump_buffer_time: float = 0.0
    dash_cooldown: float = 0.0
    dash_time: float = 0.0
    wall_jump_lock: float = 0.0

    # Jump state
    jumps_left: int = 2
    max_jumps: int = 2

    # Wall interaction state
    wall_slide_stamina: float = 3.0  # Stamina for wall clinging (legacy)
    wall_slide_stamina_max: float = 3.0
    is_wall_sliding: bool = False
    wall_coyote_time: float = 0.0  # Buffer after leaving wall for wall jump
    is_wall_hanging: bool = False
    is_ceiling_hanging: bool = False
    last_wall_dir: int = 0

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            "player_id": self.player_id,
            "physics": self.physics.to_dict(),
            "health_state": {
                "current_hp": self.health_state.current_hp,
                "max_hp": self.health_state.max_hp,
                "invincibility_frames": self.health_state.invincibility_frames,
                "invincibility_duration": self.health_state.invincibility_duration,
            },
            "facing": self.facing,
            "crouching": self.crouching,
            "is_dashing": self.is_dashing,
            "is_throwing": self.is_throwing,
            "throw_cooldown": self.throw_cooldown,
            "is_slow_walking": self.is_slow_walking,
            "is_running": self.is_running,
            "attack_stage": self.attack_stage,
            "attack_timer": self.attack_timer,
            "is_air_attacking": self.is_air_attacking,
            "is_teleporting_phase": self.is_teleporting_phase,
            "teleport_cooldown": self.teleport_cooldown,
            "teleport_cast_time": self.teleport_cast_time,
            "is_teleporting_invuln": self.is_teleporting_invuln,
            "ninjutsu_active": self.ninjutsu_active,
            "ninjutsu_casting": self.ninjutsu_casting,
            "ninjutsu_selected": self.ninjutsu_selected,
            "ninjutsu_cooldowns": self.ninjutsu_cooldowns,
            "stamina": self.stamina,
            "stamina_max": self.stamina_max,
            "stamina_regen_rate": self.stamina_regen_rate,
            "mana": self.mana,
            "mana_max": self.mana_max,
            "mana_regen_rate": self.mana_regen_rate,
            "shuriken_ammo": self.shuriken_ammo,
            "shuriken_max": self.shuriken_max,
            "coyote_time": self.coyote_time,
            "jump_buffer_time": self.jump_buffer_time,
            "dash_cooldown": self.dash_cooldown,
            "dash_time": self.dash_time,
            "wall_jump_lock": self.wall_jump_lock,
            "jumps_left": self.jumps_left,
            "max_jumps": self.max_jumps,
            "wall_slide_stamina": self.wall_slide_stamina,
            "wall_slide_stamina_max": self.wall_slide_stamina_max,
            "is_wall_sliding": self.is_wall_sliding,
            "wall_coyote_time": self.wall_coyote_time,
            "is_wall_hanging": self.is_wall_hanging,
            "is_ceiling_hanging": self.is_ceiling_hanging,
            "last_wall_dir": self.last_wall_dir,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerState":
        """Deserialize from dictionary"""
        physics_data = data.pop("physics")
        wall_coyote_time = data.pop("wall_coyote_time", 0.0)
        is_wall_hanging = data.pop("is_wall_hanging", False)
        is_ceiling_hanging = data.pop("is_ceiling_hanging", False)
        wall_slide_stamina_max = data.pop(
            "wall_slide_stamina_max", data.get("wall_slide_stamina", 3.0)
        )
        # Resource defaults
        stamina = data.pop("stamina", 0.0)
        stamina_max = data.pop("stamina_max", 0.0)
        stamina_regen_rate = data.pop("stamina_regen_rate", 0.0)
        mana = data.pop("mana", 0.0)
        mana_max = data.pop("mana_max", 0.0)
        mana_regen_rate = data.pop("mana_regen_rate", 0.0)
        shuriken_ammo = data.pop("shuriken_ammo", 0)
        shuriken_max = data.pop("shuriken_max", 0)
        is_slow_walking = data.pop("is_slow_walking", False)
        is_running = data.pop("is_running", False)
        is_teleporting_phase = data.pop("is_teleporting_phase", False)
        teleport_cooldown = data.pop("teleport_cooldown", 0.0)
        teleport_cast_time = data.pop("teleport_cast_time", 0.0)
        is_teleporting_invuln = data.pop("is_teleporting_invuln", False)
        ninjutsu_active = data.pop("ninjutsu_active", False)
        ninjutsu_casting = data.pop("ninjutsu_casting", False)
        ninjutsu_selected = data.pop("ninjutsu_selected", "")
        ninjutsu_cooldowns = data.pop("ninjutsu_cooldowns", {})
        is_throwing = data.pop("is_throwing", False)
        throw_cooldown = data.pop("throw_cooldown", 0.0)
        attack_stage = data.pop("attack_stage", 0)
        attack_timer = data.pop("attack_timer", 0.0)
        is_air_attacking = data.pop("is_air_attacking", False)

        # Handle health state (with backwards compatibility)
        if "health_state" in data:
            # New format with HealthState
            health_data = data.pop("health_state")
            health_state = HealthState(
                current_hp=health_data.get("current_hp", 3),
                max_hp=health_data.get("max_hp", 3),
                invincibility_frames=health_data.get("invincibility_frames", 0),
                invincibility_duration=health_data.get("invincibility_duration", 60),
            )
        else:
            # Old format with primitive health fields - migrate to HealthState
            old_health = data.pop("health", 5)
            old_max_health = data.pop("max_health", 5)
            old_invincibility_time = data.pop("invincibility_time", 0.0)

            # Convert invincibility_time (float seconds) to frames (int)
            # Assuming 60 FPS: frames = time * 60
            invincibility_frames = int(old_invincibility_time * 60)

            health_state = HealthState(
                current_hp=old_health,
                max_hp=old_max_health,
                invincibility_frames=invincibility_frames,
                invincibility_duration=60,
            )

        return cls(
            physics=PhysicsState.from_dict(physics_data),
            health_state=health_state,
            wall_coyote_time=wall_coyote_time,
            is_wall_hanging=is_wall_hanging,
            is_ceiling_hanging=is_ceiling_hanging,
            wall_slide_stamina_max=wall_slide_stamina_max,
            stamina=stamina,
            stamina_max=stamina_max,
            stamina_regen_rate=stamina_regen_rate,
            mana=mana,
            mana_max=mana_max,
            mana_regen_rate=mana_regen_rate,
            shuriken_ammo=shuriken_ammo,
            shuriken_max=shuriken_max,
            is_teleporting_phase=is_teleporting_phase,
            teleport_cooldown=teleport_cooldown,
            teleport_cast_time=teleport_cast_time,
            is_teleporting_invuln=is_teleporting_invuln,
            ninjutsu_active=ninjutsu_active,
            ninjutsu_casting=ninjutsu_casting,
            ninjutsu_selected=ninjutsu_selected,
            ninjutsu_cooldowns=ninjutsu_cooldowns,
            is_throwing=is_throwing,
            throw_cooldown=throw_cooldown,
            is_slow_walking=is_slow_walking,
            is_running=is_running,
            last_wall_dir=data.pop("last_wall_dir", 0),
            attack_stage=attack_stage,
            attack_timer=attack_timer,
            is_air_attacking=is_air_attacking,
            **data,
        )

    def is_alive(self) -> bool:
        """Check if player is alive"""
        return self.health_state.is_alive()

    def is_invincible(self) -> bool:
        """Check if player is currently invincible"""
        return self.health_state.is_invincible()


# ============================================================================
# Game State
# ============================================================================


@dataclass
class GameState:
    """
    Complete game state (network-serializable)

    Contains all game data needed for deterministic simulation,
    network synchronization, and save/load.
    """

    tick_number: int = 0
    level_index: int = 1
    total_score: int = 0
    game_time: float = 0.0

    # Player states (indexed by player_id)
    players: dict[int, PlayerState] = field(default_factory=dict)

    # Level state
    coins_collected: int = 0
    total_coins: int = 0
    exit_unlocked: bool = False

    # Pickup positions (for respawn/network sync)
    # Stored as (x, y) tuples
    active_coins: list[tuple[float, float]] = field(default_factory=list)
    active_healths: list[tuple[float, float]] = field(default_factory=list)
    active_lives: list[tuple[float, float]] = field(default_factory=list)

    # Level metadata
    level_seed: int | None = None
    level_width: int = 0
    level_height: int = 0

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            "tick_number": self.tick_number,
            "level_index": self.level_index,
            "total_score": self.total_score,
            "game_time": self.game_time,
            "players": {pid: p.to_dict() for pid, p in self.players.items()},
            "coins_collected": self.coins_collected,
            "total_coins": self.total_coins,
            "exit_unlocked": self.exit_unlocked,
            "active_coins": self.active_coins,
            "active_healths": self.active_healths,
            "active_lives": self.active_lives,
            "level_seed": self.level_seed,
            "level_width": self.level_width,
            "level_height": self.level_height,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameState":
        """Deserialize from dictionary"""
        players_data = data.pop("players")
        players = {int(pid): PlayerState.from_dict(p) for pid, p in players_data.items()}
        return cls(players=players, **data)

    def get_player(self, player_id: int) -> PlayerState | None:
        """Get player state by ID"""
        return self.players.get(player_id)

    def add_player(
        self, player_id: int, spawn_x: float, spawn_y: float, width: int = 24, height: int = 48
    ):
        """Add player to game state"""
        physics = PhysicsState(x=spawn_x, y=spawn_y, vx=0.0, vy=0.0, width=width, height=height)
        self.players[player_id] = PlayerState(player_id=player_id, physics=physics)

    def remove_player(self, player_id: int):
        """Remove player from game state"""
        if player_id in self.players:
            del self.players[player_id]


# ============================================================================
# State Manager
# ============================================================================


class StateManager:
    """
    Manages game state with snapshot capability

    Provides centralized access to game state with support for:
    - State snapshots for network sync
    - State history for rollback
    - State cloning for prediction
    """

    def __init__(self):
        self.current_state = GameState()
        self.snapshot_history: list[dict] = []  # For rollback/replay
        self.max_history = 300  # Keep last 5 seconds at 60Hz

    def get_state(self) -> GameState:
        """Get current game state"""
        return self.current_state

    def set_state(self, state: GameState):
        """Set current game state (e.g., after loading)"""
        self.current_state = state

    def get_player_state(self, player_id: int) -> PlayerState | None:
        """Get player state by ID"""
        return self.current_state.get_player(player_id)

    def add_player(
        self, player_id: int, spawn_x: float, spawn_y: float, width: int = 24, height: int = 48
    ):
        """Add player to game"""
        self.current_state.add_player(player_id, spawn_x, spawn_y, width, height)

    def remove_player(self, player_id: int):
        """Remove player from game"""
        self.current_state.remove_player(player_id)

    def snapshot(self) -> dict:
        """
        Create snapshot for network sync or replay

        Returns:
            Dictionary representation of current state
        """
        return self.current_state.to_dict()

    def save_snapshot(self):
        """Save current state to history"""
        self.snapshot_history.append(self.snapshot())

        # Limit history size
        if len(self.snapshot_history) > self.max_history:
            self.snapshot_history.pop(0)

    def restore(self, snapshot: dict):
        """
        Restore from snapshot (for rollback)

        Args:
            snapshot: State dictionary to restore
        """
        self.current_state = GameState.from_dict(snapshot)

    def restore_from_history(self, ticks_back: int) -> bool:
        """
        Restore state from history

        Args:
            ticks_back: Number of ticks to go back

        Returns:
            True if successful, False if history doesn't go back that far
        """
        if ticks_back >= len(self.snapshot_history):
            return False

        snapshot = self.snapshot_history[-(ticks_back + 1)]
        self.restore(snapshot)
        return True

    def clear_history(self):
        """Clear snapshot history"""
        self.snapshot_history.clear()

    def get_history_size(self) -> int:
        """Get number of snapshots in history"""
        return len(self.snapshot_history)
