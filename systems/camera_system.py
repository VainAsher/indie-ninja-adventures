"""
Camera System - Responsive camera with letterboxing support

Features:
- Multiple camera modes (world, room, free)
- Smooth camera following (lerp with overshoot)
- Configurable deadzone (camera only moves when player leaves center area)
- World/room bounds clamping
- Responsive viewport with letterboxing
- Support for multiple aspect ratios
- Dynamic window resizing
- Camera effects (screen shake, pan, springy lerp)
"""

import pygame
import random
import math
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class CameraMode(Enum):
    """Camera follow modes"""
    WORLD_CLAMP = "world_clamp"  # Follow player, clamp to world boundaries
    ROOM_CLAMP = "room_clamp"    # Follow player, clamp to current room boundaries
    FREE = "free"                 # Free camera, no following or clamping
    LOCKED = "locked"             # Camera fixed in place


@dataclass
class CameraConfig:
    """Camera configuration"""
    # Virtual game resolution (internal rendering resolution)
    game_width: int = 1280
    game_height: int = 720

    # Camera follow behavior
    follow_speed: float = 0.1  # Lower = smoother (lerp factor)
    spring_stiffness: float = 0.15  # Overshoot stiffness (0 = no spring, 0.2 = bouncy)
    deadzone_width: int = 200  # Horizontal deadzone
    deadzone_height: int = 150  # Vertical deadzone

    # World bounds (will be set dynamically)
    world_width: int = 1280
    world_height: int = 1280

    # Room bounds (for room-clamped mode)
    room_x: int = 0
    room_y: int = 0
    room_width: int = 1280
    room_height: int = 1280

    # Camera effects
    enable_shake: bool = True
    enable_pan: bool = True
    enable_spring: bool = True


class CameraSystem:
    """
    Responsive camera system with smooth following and letterboxing

    The camera follows the player smoothly and handles different window sizes
    by rendering to a virtual resolution and scaling with letterboxing.
    """

    def __init__(self, config: Optional[CameraConfig] = None):
        self.config = config or CameraConfig()

        # Camera mode
        self.mode = CameraMode.WORLD_CLAMP

        # Camera position (top-left of viewport in world space)
        self.x = 0.0
        self.y = 0.0

        # Target position (where camera wants to be)
        self.target_x = 0.0
        self.target_y = 0.0

        # Spring velocity (for overshoot effect)
        self.velocity_x = 0.0
        self.velocity_y = 0.0

        # Free camera movement speed
        self.free_cam_speed = 5.0

        # Virtual game surface (internal resolution)
        self.game_surface = pygame.Surface((self.config.game_width, self.config.game_height))

        # Current window size
        self.window_width = self.config.game_width
        self.window_height = self.config.game_height

        # Letterbox bars
        self.letterbox_top = 0
        self.letterbox_left = 0
        self.render_width = self.window_width
        self.render_height = self.window_height

        # Camera effects
        self.shake_intensity = 0.0
        self.shake_duration = 0.0
        self.shake_offset_x = 0.0
        self.shake_offset_y = 0.0

        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0
        self.pan_target_x = 0.0
        self.pan_target_y = 0.0

    def set_world_bounds(self, width: int, height: int):
        """Set the world boundaries for camera clamping"""
        self.config.world_width = width
        self.config.world_height = height

    def set_room_bounds(self, x: int, y: int, width: int, height: int):
        """Set the current room boundaries for room-clamped mode"""
        self.config.room_x = x
        self.config.room_y = y
        self.config.room_width = width
        self.config.room_height = height

    def set_mode(self, mode: CameraMode):
        """Change camera mode"""
        self.mode = mode

    def move_free_camera(self, dx: float, dy: float):
        """
        Move camera in free mode

        Args:
            dx: Delta X movement
            dy: Delta Y movement
        """
        if self.mode == CameraMode.FREE:
            self.x += dx * self.free_cam_speed
            self.y += dy * self.free_cam_speed

    def add_screen_shake(self, intensity: float, duration: float):
        """
        Add screen shake effect

        Args:
            intensity: Shake intensity in pixels (max offset)
            duration: Shake duration in seconds
        """
        if not self.config.enable_shake:
            return

        # Use max intensity if multiple shakes overlap
        if intensity > self.shake_intensity:
            self.shake_intensity = intensity
            self.shake_duration = duration

    def add_camera_pan(self, offset_x: float, offset_y: float, speed: float = 0.1):
        """
        Pan camera by offset amount (smooth pan to offset)

        Args:
            offset_x: Target X offset in pixels
            offset_y: Target Y offset in pixels
            speed: Pan speed (0.1 = smooth, 1.0 = instant)
        """
        if not self.config.enable_pan:
            return

        self.pan_target_x = offset_x
        self.pan_target_y = offset_y

    def _update_shake(self, dt: float):
        """Update screen shake effect"""
        if self.shake_duration <= 0:
            self.shake_offset_x = 0.0
            self.shake_offset_y = 0.0
            return

        # Decay shake over time
        self.shake_duration -= dt

        if self.shake_duration > 0:
            # Random offset based on intensity
            angle = random.uniform(0, 2 * math.pi)
            magnitude = random.uniform(0, self.shake_intensity)

            self.shake_offset_x = math.cos(angle) * magnitude
            self.shake_offset_y = math.sin(angle) * magnitude
        else:
            self.shake_offset_x = 0.0
            self.shake_offset_y = 0.0

    def _update_pan(self, dt: float):
        """Update camera pan effect"""
        # Smooth lerp to pan target
        pan_speed = 0.1
        self.pan_offset_x += (self.pan_target_x - self.pan_offset_x) * pan_speed
        self.pan_offset_y += (self.pan_target_y - self.pan_offset_y) * pan_speed

        # Reset if close enough
        if abs(self.pan_target_x - self.pan_offset_x) < 0.5:
            self.pan_offset_x = self.pan_target_x
        if abs(self.pan_target_y - self.pan_offset_y) < 0.5:
            self.pan_offset_y = self.pan_target_y

    def update(self, target_x: float, target_y: float, dt: float = 0.0167):
        """
        Update camera to follow target (usually the player)

        Args:
            target_x: Target X position in world space
            target_y: Target Y position in world space
            dt: Delta time in seconds (default 60 FPS)
        """
        # Update camera effects
        self._update_shake(dt)
        self._update_pan(dt)

        # Skip following if in FREE or LOCKED mode
        if self.mode == CameraMode.LOCKED:
            return
        elif self.mode == CameraMode.FREE:
            # No automatic following in free mode
            return

        # Calculate deadzone bounds (center of screen)
        deadzone_left = self.x + (self.config.game_width / 2) - (self.config.deadzone_width / 2)
        deadzone_right = self.x + (self.config.game_width / 2) + (self.config.deadzone_width / 2)
        deadzone_top = self.y + (self.config.game_height / 2) - (self.config.deadzone_height / 2)
        deadzone_bottom = self.y + (self.config.game_height / 2) + (self.config.deadzone_height / 2)

        # Update target position based on deadzone
        if target_x < deadzone_left:
            self.target_x = target_x - (self.config.game_width / 2) + (self.config.deadzone_width / 2)
        elif target_x > deadzone_right:
            self.target_x = target_x - (self.config.game_width / 2) - (self.config.deadzone_width / 2)

        if target_y < deadzone_top:
            self.target_y = target_y - (self.config.game_height / 2) + (self.config.deadzone_height / 2)
        elif target_y > deadzone_bottom:
            self.target_y = target_y - (self.config.game_height / 2) - (self.config.deadzone_height / 2)

        # Smooth lerp to target with optional spring overshoot
        if self.config.enable_spring and self.config.spring_stiffness > 0:
            # Spring-based movement (with overshoot)
            dx = self.target_x - self.x
            dy = self.target_y - self.y

            # Apply spring force to velocity
            self.velocity_x += dx * self.config.spring_stiffness
            self.velocity_y += dy * self.config.spring_stiffness

            # Apply damping (prevents infinite oscillation)
            damping = 0.8
            self.velocity_x *= damping
            self.velocity_y *= damping

            # Update position with velocity
            self.x += self.velocity_x
            self.y += self.velocity_y
        else:
            # Simple lerp (no overshoot)
            self.x += (self.target_x - self.x) * self.config.follow_speed
            self.y += (self.target_y - self.y) * self.config.follow_speed

        # Clamp based on mode
        if self.mode == CameraMode.WORLD_CLAMP:
            # Clamp to world bounds
            self.x = max(0, min(self.x, self.config.world_width - self.config.game_width))
            self.y = max(0, min(self.y, self.config.world_height - self.config.game_height))
        elif self.mode == CameraMode.ROOM_CLAMP:
            # Clamp to room bounds
            min_x = self.config.room_x
            max_x = self.config.room_x + self.config.room_width - self.config.game_width
            min_y = self.config.room_y
            max_y = self.config.room_y + self.config.room_height - self.config.game_height

            # If room is smaller than viewport, center the room
            if self.config.room_width <= self.config.game_width:
                self.x = self.config.room_x - (self.config.game_width - self.config.room_width) / 2
            else:
                self.x = max(min_x, min(self.x, max_x))

            if self.config.room_height <= self.config.game_height:
                self.y = self.config.room_y - (self.config.game_height - self.config.room_height) / 2
            else:
                self.y = max(min_y, min(self.y, max_y))

    def world_to_screen(self, world_x: float, world_y: float) -> Tuple[float, float]:
        """
        Convert world coordinates to screen coordinates

        Args:
            world_x: X position in world space
            world_y: Y position in world space

        Returns:
            (screen_x, screen_y) tuple
        """
        # Apply camera position
        screen_x = world_x - self.x
        screen_y = world_y - self.y

        # Apply camera effects (shake + pan)
        screen_x += self.shake_offset_x + self.pan_offset_x
        screen_y += self.shake_offset_y + self.pan_offset_y

        return (screen_x, screen_y)

    def screen_to_world(self, screen_x: float, screen_y: float) -> Tuple[float, float]:
        """
        Convert screen coordinates to world coordinates

        Args:
            screen_x: X position in screen space
            screen_y: Y position in screen space

        Returns:
            (world_x, world_y) tuple
        """
        world_x = screen_x + self.x
        world_y = screen_y + self.y
        return (world_x, world_y)

    def apply(self, rect: pygame.Rect) -> pygame.Rect:
        """
        Apply camera transform to a rect (for rendering)

        Args:
            rect: World-space rect

        Returns:
            Screen-space rect
        """
        return pygame.Rect(
            rect.x - int(self.x) + int(self.shake_offset_x + self.pan_offset_x),
            rect.y - int(self.y) + int(self.shake_offset_y + self.pan_offset_y),
            rect.width,
            rect.height
        )

    def handle_resize(self, window_width: int, window_height: int):
        """
        Handle window resize and calculate letterboxing

        Args:
            window_width: New window width
            window_height: New window height
        """
        self.window_width = window_width
        self.window_height = window_height

        # Calculate aspect ratios
        game_aspect = self.config.game_width / self.config.game_height
        window_aspect = window_width / window_height

        if window_aspect > game_aspect:
            # Window is wider - letterbox left/right
            self.render_height = window_height
            self.render_width = int(window_height * game_aspect)
            self.letterbox_left = (window_width - self.render_width) // 2
            self.letterbox_top = 0
        else:
            # Window is taller - letterbox top/bottom
            self.render_width = window_width
            self.render_height = int(window_width / game_aspect)
            self.letterbox_left = 0
            self.letterbox_top = (window_height - self.render_height) // 2

    def get_game_surface(self) -> pygame.Surface:
        """Get the virtual game surface to render to"""
        return self.game_surface

    def present(self, screen: pygame.Surface):
        """
        Present the game surface to the actual window with letterboxing

        Args:
            screen: The actual pygame display surface
        """
        # Fill letterbox bars with black
        screen.fill((0, 0, 0))

        # Scale and blit game surface with letterboxing
        scaled_surface = pygame.transform.scale(
            self.game_surface,
            (self.render_width, self.render_height)
        )
        screen.blit(scaled_surface, (self.letterbox_left, self.letterbox_top))

    def get_viewport_rect(self) -> pygame.Rect:
        """Get the current viewport rectangle in world space"""
        return pygame.Rect(
            int(self.x),
            int(self.y),
            self.config.game_width,
            self.config.game_height
        )


# Common screen size presets
SCREEN_PRESETS = {
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "1440p": (2560, 1440),
    "4K": (3840, 2160),
    "16:9_small": (1366, 768),
    "16:9_medium": (1600, 900),
    "16:10_laptop": (1440, 900),
    "16:10_large": (1920, 1200),
    "ultrawide": (2560, 1080),
    "windowed": (960, 540),
}


def get_recommended_window_size() -> Tuple[int, int]:
    """
    Get recommended window size based on display

    Returns:
        (width, height) tuple
    """
    display_info = pygame.display.Info()
    display_width = display_info.current_w
    display_height = display_info.current_h

    # Use 80% of screen height for windowed mode
    target_height = int(display_height * 0.8)
    target_width = int(target_height * 16 / 9)  # 16:9 aspect ratio

    return (target_width, target_height)
