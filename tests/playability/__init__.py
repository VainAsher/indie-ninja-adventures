"""
Playability Testing Framework

Validates that procedurally generated worlds are actually playable
by simulating player movement and testing reachability.
"""

from .metrics import (
    PlayabilityMetrics,
    RoomMetrics,
    WorldMetrics,
)
from .simulator import (
    MovementAction,
    PlayerSimulator,
    SimulationResult,
)
from .validators import (
    JumpabilityValidator,
    NavigabilityValidator,
    PlayabilityValidator,
    ReachabilityValidator,
    SafetyValidator,
)

__all__ = [
    # Validators
    "PlayabilityValidator",
    "ReachabilityValidator",
    "JumpabilityValidator",
    "NavigabilityValidator",
    "SafetyValidator",
    # Simulator
    "PlayerSimulator",
    "MovementAction",
    "SimulationResult",
    # Metrics
    "PlayabilityMetrics",
    "RoomMetrics",
    "WorldMetrics",
]
