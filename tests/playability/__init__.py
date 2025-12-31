"""
Playability Testing Framework

Validates that procedurally generated worlds are actually playable
by simulating player movement and testing reachability.
"""

from .validators import (
    PlayabilityValidator,
    ReachabilityValidator,
    JumpabilityValidator,
    NavigabilityValidator,
    SafetyValidator,
)

from .simulator import (
    PlayerSimulator,
    MovementAction,
    SimulationResult,
)

from .metrics import (
    PlayabilityMetrics,
    RoomMetrics,
    WorldMetrics,
)

__all__ = [
    # Validators
    'PlayabilityValidator',
    'ReachabilityValidator',
    'JumpabilityValidator',
    'NavigabilityValidator',
    'SafetyValidator',

    # Simulator
    'PlayerSimulator',
    'MovementAction',
    'SimulationResult',

    # Metrics
    'PlayabilityMetrics',
    'RoomMetrics',
    'WorldMetrics',
]
