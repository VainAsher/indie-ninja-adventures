"""
Ability Gate System - Metroidvania-style Progression Gates

This module provides ability-gated obstacles that block player progression
until specific abilities are unlocked:
- HIGH_LEDGE: Requires double jump to reach
- VERTICAL_WALL: Requires wall jump to climb
- WIDE_GAP: Requires dash to cross
- LOW_PASSAGE: Requires crouch to pass through
- LOCKED_DOOR: Requires key item or switch activation

Version: v0.6.0 (Phase 5)
"""

from dataclasses import dataclass
from enum import Enum

# ============================================================
# Gate Types
# ============================================================


class GateType(Enum):
    """Types of ability gates"""

    HIGH_LEDGE = "high_ledge"  # Requires double jump
    VERTICAL_WALL = "vertical_wall"  # Requires wall jump
    WIDE_GAP = "wide_gap"  # Requires dash
    LOW_PASSAGE = "low_passage"  # Requires crouch
    LOCKED_DOOR = "locked_door"  # Requires key/switch


class AbilityRequirement(Enum):
    """Abilities required to pass gates"""

    BASIC_MOVEMENT = "basic_movement"  # Always available
    JUMP = "jump"  # Always available
    DOUBLE_JUMP = "double_jump"
    WALL_JUMP = "wall_jump"
    DASH = "dash"
    CROUCH = "crouch"
    WALL_CLING = "wall_cling"
    SLOW_WALK = "slow_walk"
    SHURIKEN = "shuriken"
    TELEPORT = "teleport"
    NINJUTSU = "ninjutsu"
    KEY_ITEM = "key_item"  # Specific key for locked door


# ============================================================
# Gate Definitions
# ============================================================


@dataclass
class GateDefinition:
    """Definition for an ability gate type"""

    gate_type: GateType
    required_ability: AbilityRequirement
    display_name: str
    description: str
    width: int  # Width in pixels
    height: int  # Height in pixels
    passable: bool  # Can player pass through with ability?
    visual_hint: str  # Text to display above gate


# Gate type definitions
GATE_DEFINITIONS = {
    GateType.HIGH_LEDGE: GateDefinition(
        gate_type=GateType.HIGH_LEDGE,
        required_ability=AbilityRequirement.DOUBLE_JUMP,
        display_name="High Ledge",
        description="A tall ledge that requires double jump to reach",
        width=64,  # 2 tiles wide
        height=96,  # 3 tiles tall (unreachable with single jump)
        passable=True,
        visual_hint="Double Jump Required",
    ),
    GateType.VERTICAL_WALL: GateDefinition(
        gate_type=GateType.VERTICAL_WALL,
        required_ability=AbilityRequirement.WALL_JUMP,
        display_name="Vertical Wall",
        description="A tall wall shaft that requires wall jumping to climb",
        width=64,  # 2 tiles wide
        height=192,  # 6 tiles tall
        passable=True,
        visual_hint="Wall Jump Required",
    ),
    GateType.WIDE_GAP: GateDefinition(
        gate_type=GateType.WIDE_GAP,
        required_ability=AbilityRequirement.DASH,
        display_name="Wide Gap",
        description="A gap too wide to jump across without dashing",
        width=128,  # 4 tiles wide (too wide for normal jump)
        height=32,  # Just a gap marker
        passable=True,
        visual_hint="Dash Required",
    ),
    GateType.LOW_PASSAGE: GateDefinition(
        gate_type=GateType.LOW_PASSAGE,
        required_ability=AbilityRequirement.CROUCH,
        display_name="Low Passage",
        description="A low passage that requires crouching to pass through",
        width=96,  # 3 tiles wide
        height=28,  # Height of crouched player (must crouch to fit)
        passable=True,
        visual_hint="Crouch Required",
    ),
    GateType.LOCKED_DOOR: GateDefinition(
        gate_type=GateType.LOCKED_DOOR,
        required_ability=AbilityRequirement.KEY_ITEM,
        display_name="Locked Door",
        description="A locked door that requires a key or switch to open",
        width=32,  # 1 tile wide
        height=64,  # 2 tiles tall
        passable=False,  # Blocks movement until unlocked
        visual_hint="Key Required",
    ),
}


def get_gate_definition(gate_type: GateType) -> GateDefinition | None:
    """Get gate definition by type"""
    return GATE_DEFINITIONS.get(gate_type)


# ============================================================
# Ability Gate Entity
# ============================================================


@dataclass
class AbilityGate:
    """
    An ability gate that blocks progression until player has required ability.

    Gates can be:
    - Physical obstacles (HIGH_LEDGE, VERTICAL_WALL, WIDE_GAP, LOW_PASSAGE)
    - Locked barriers (LOCKED_DOOR)
    """

    gate_id: str
    gate_type: GateType
    x: float  # Position (top-left)
    y: float
    width: int
    height: int
    required_ability: AbilityRequirement
    unlocked: bool = False  # For LOCKED_DOOR type
    key_id: str | None = None  # Key item ID (for LOCKED_DOOR)

    def get_rect(self) -> tuple[float, float, int, int]:
        """Get bounding rectangle (x, y, width, height)"""
        return (self.x, self.y, self.width, self.height)

    def get_center(self) -> tuple[float, float]:
        """Get center position"""
        return (self.x + self.width / 2, self.y + self.height / 2)

    def check_collision(
        self, player_x: float, player_y: float, player_width: int, player_height: int
    ) -> bool:
        """
        Check if player collides with gate.

        Args:
            player_x, player_y: Player position
            player_width, player_height: Player dimensions

        Returns:
            True if collision detected
        """
        # AABB collision detection
        return (
            player_x < self.x + self.width
            and player_x + player_width > self.x
            and player_y < self.y + self.height
            and player_y + player_height > self.y
        )

    def can_pass(self, unlocked_abilities: set[AbilityRequirement]) -> bool:
        """
        Check if player can pass through gate with current abilities.

        Args:
            unlocked_abilities: Set of abilities player has unlocked

        Returns:
            True if player can pass
        """
        # LOCKED_DOOR requires explicit unlocking
        if self.gate_type == GateType.LOCKED_DOOR:
            return self.unlocked

        # Physical gates require the ability
        return self.required_ability in unlocked_abilities

    def unlock(self):
        """Unlock the gate (for LOCKED_DOOR type)"""
        if self.gate_type == GateType.LOCKED_DOOR:
            self.unlocked = True

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            "gate_id": self.gate_id,
            "gate_type": self.gate_type.value,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "required_ability": self.required_ability.value,
            "unlocked": self.unlocked,
            "key_id": self.key_id,
        }

    @staticmethod
    def from_dict(data: dict) -> "AbilityGate":
        """Deserialize from dictionary"""
        return AbilityGate(
            gate_id=data["gate_id"],
            gate_type=GateType(data["gate_type"]),
            x=data["x"],
            y=data["y"],
            width=data["width"],
            height=data["height"],
            required_ability=AbilityRequirement(data["required_ability"]),
            unlocked=data.get("unlocked", False),
            key_id=data.get("key_id"),
        )


# ============================================================
# Gate Factory
# ============================================================


def create_gate(
    gate_type: GateType, gate_id: str, x: float, y: float, key_id: str | None = None
) -> AbilityGate:
    """
    Create an ability gate at specified position.

    Args:
        gate_type: Type of gate to create
        gate_id: Unique gate ID
        x, y: Position
        key_id: Optional key item ID (for LOCKED_DOOR)

    Returns:
        AbilityGate instance
    """
    definition = get_gate_definition(gate_type)
    if definition is None:
        raise ValueError(f"Unknown gate type: {gate_type}")

    return AbilityGate(
        gate_id=gate_id,
        gate_type=gate_type,
        x=x,
        y=y,
        width=definition.width,
        height=definition.height,
        required_ability=definition.required_ability,
        unlocked=False,
        key_id=key_id,
    )


# ============================================================
# Gate Manager
# ============================================================


class GateManager:
    """
    Manages ability gates in the level.

    Responsibilities:
    - Track all gates in level
    - Check player collisions with gates
    - Handle gate unlocking
    - Provide gate state for rendering
    """

    def __init__(self):
        self.gates: dict[str, AbilityGate] = {}
        self.next_gate_id = 0

    def add_gate(self, gate_type: GateType, x: float, y: float, key_id: str | None = None) -> str:
        """
        Add a gate to the level.

        Args:
            gate_type: Type of gate
            x, y: Position
            key_id: Optional key ID (for LOCKED_DOOR)

        Returns:
            Gate ID
        """
        gate_id = f"gate_{self.next_gate_id}"
        self.next_gate_id += 1

        gate = create_gate(gate_type, gate_id, x, y, key_id)
        self.gates[gate_id] = gate

        return gate_id

    def remove_gate(self, gate_id: str):
        """Remove a gate from the level"""
        if gate_id in self.gates:
            del self.gates[gate_id]

    def get_gate(self, gate_id: str) -> AbilityGate | None:
        """Get gate by ID"""
        return self.gates.get(gate_id)

    def unlock_gate(self, gate_id: str):
        """Unlock a gate"""
        gate = self.gates.get(gate_id)
        if gate:
            gate.unlock()

    def check_gate_collision(
        self,
        player_x: float,
        player_y: float,
        player_width: int,
        player_height: int,
        unlocked_abilities: set[AbilityRequirement],
    ) -> str | None:
        """
        Check if player collides with any impassable gates.

        Args:
            player_x, player_y: Player position
            player_width, player_height: Player dimensions
            unlocked_abilities: Set of abilities player has

        Returns:
            Gate ID if collision with impassable gate, None otherwise
        """
        for gate_id, gate in self.gates.items():
            if gate.check_collision(player_x, player_y, player_width, player_height):
                # If player can't pass, this is a blocking collision
                if not gate.can_pass(unlocked_abilities):
                    return gate_id

        return None

    def get_gates_near_position(self, x: float, y: float, radius: float) -> list[AbilityGate]:
        """
        Get gates near a position (for rendering visual hints).

        Args:
            x, y: Center position
            radius: Search radius

        Returns:
            List of gates within radius
        """
        nearby_gates = []
        for gate in self.gates.values():
            gate_center_x, gate_center_y = gate.get_center()
            dx = gate_center_x - x
            dy = gate_center_y - y
            distance = (dx * dx + dy * dy) ** 0.5

            if distance <= radius:
                nearby_gates.append(gate)

        return nearby_gates

    def clear(self):
        """Clear all gates"""
        self.gates.clear()
        self.next_gate_id = 0

    def get_all_gates(self) -> list[AbilityGate]:
        """Get all gates"""
        return list(self.gates.values())

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            "gates": {gate_id: gate.to_dict() for gate_id, gate in self.gates.items()},
            "next_gate_id": self.next_gate_id,
        }

    @staticmethod
    def from_dict(data: dict) -> "GateManager":
        """Deserialize from dictionary"""
        manager = GateManager()
        manager.next_gate_id = data.get("next_gate_id", 0)

        for gate_id, gate_data in data.get("gates", {}).items():
            gate = AbilityGate.from_dict(gate_data)
            manager.gates[gate_id] = gate

        return manager


# ============================================================
# Helper Functions
# ============================================================


def get_required_ability_for_gate(gate_type: GateType) -> AbilityRequirement:
    """Get the ability required to pass a gate type"""
    definition = get_gate_definition(gate_type)
    return definition.required_ability if definition else AbilityRequirement.BASIC_MOVEMENT


def get_visual_hint(gate_type: GateType) -> str:
    """Get the visual hint text for a gate type"""
    definition = get_gate_definition(gate_type)
    return definition.visual_hint if definition else "Gate"
