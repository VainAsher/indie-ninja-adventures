"""
Game systems for Vain Asher Gaming's: Indie Ninja Adventures

High-level systems that coordinate game logic:
- Physics simulation
- Collision detection
- Camera and rendering
- Input processing
- Pickup management
"""

from .collision_system import CollisionSystem
from .physics_system import PhysicsSystem
from .camera_system import CameraSystem, CameraConfig, CameraMode, SCREEN_PRESETS, get_recommended_window_size
from .save_system import SaveManager, SaveData, PlayerProgress, GameSettings, GameStatistics

__all__ = [
    'CollisionSystem',
    'PhysicsSystem',
    'CameraSystem',
    'CameraConfig',
    'CameraMode',
    'SCREEN_PRESETS',
    'get_recommended_window_size',
    'SaveManager',
    'SaveData',
    'PlayerProgress',
    'GameSettings',
    'GameStatistics',
]
