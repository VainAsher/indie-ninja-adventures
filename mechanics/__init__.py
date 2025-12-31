"""
Player mechanics for Vain Asher Gaming's: Indie Ninja Adventures

Modular, self-contained mechanics that implement player movement and abilities:
- Movement (ground/air acceleration)
- Jumping (ground/double/wall/coyote/buffer)
- Dashing
- Wall sliding
- Crouching
- Health management (damage, invincibility, death)
"""

from .base import BaseMechanic
from .jump import JumpMechanic
from .movement import MovementMechanic
from .dash import DashMechanic
from .wall_slide import WallSlideMechanic
from .crouch import CrouchMechanic
from .damage import DamageMechanic
from .shuriken import ShurikenMechanic
from .teleport import TeleportMechanic
from .ninjutsu import NinjutsuMechanic

__all__ = [
    'BaseMechanic',
    'JumpMechanic',
    'MovementMechanic',
    'DashMechanic',
    'WallSlideMechanic',
    'CrouchMechanic',
    'DamageMechanic',
    'ShurikenMechanic',
    'TeleportMechanic',
    'NinjutsuMechanic',
]
