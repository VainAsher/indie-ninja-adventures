"""
Companion Orbs - Yin & Yang spirit companions

Visual representation of The Hollowed Ninja's emotional companions.

Yin & Yang are twin ethereal spirit-orbs that orbit the player:
- Yin: Left side, steady white glow (represents calm, reflection)
- Yang: Right side, flickering gold glow (represents energy, joy)

Symbolic meaning:
- Represent family/children
- Present in Acts 0, 3, 4
- Absent in Acts 1-2 (consumed by Veil Maiden)
- Return as constellation in postgame (visible but distant)

Version: v0.7.0
"""

import pygame
import math
from typing import Tuple, Optional


class CompanionOrbs:
    """
    Manages Yin & Yang companion orbs that orbit the player.

    The orbs are purely visual (cosmetic) companions that provide
    emotional weight to the story. They disappear when consumed by
    the Veil Maiden and never return physically (only as stars).
    """

    def __init__(self):
        """Initialize companion orbs."""
        # Visibility state (controlled by story)
        self.yin_active: bool = True
        self.yang_active: bool = True

        # Orbit parameters
        self.orbit_radius: float = 35.0  # Distance from player center
        self.orbit_angle: float = 0.0  # Current orbit angle (radians)
        self.orbit_speed: float = 0.8  # Radians per second (slow rotation)

        # Yin (left/white) parameters
        self.yin_size: int = 8  # Radius in pixels
        self.yin_color: Tuple[int, int, int] = (220, 220, 255)  # Soft white-blue
        self.yin_glow_size: int = 16  # Glow radius
        self.yin_pulse_speed: float = 2.0  # Pulse animation speed
        self.yin_pulse_offset: float = 0.0

        # Yang (right/gold) parameters
        self.yang_size: int = 8  # Radius in pixels
        self.yang_color: Tuple[int, int, int] = (255, 220, 150)  # Warm gold
        self.yang_glow_size: int = 16  # Glow radius
        self.yang_flicker_speed: float = 6.0  # Flicker animation speed (faster than Yin)
        self.yang_flicker_offset: float = 1.57  # π/2 offset from Yin

        # Particle effects (optional)
        self.enable_particles: bool = True
        self.particles: list = []  # List of particle dicts

        # Audio (placeholder - would need sound system integration)
        self.enable_audio: bool = False  # Enable gentle hum/chime sounds

    def update(self, dt: float, player_x: float, player_y: float,
               player_width: int, player_height: int) -> None:
        """
        Update companion orb positions and animations.

        Args:
            dt: Delta time in seconds
            player_x: Player X position
            player_y: Player Y position
            player_width: Player width
            player_height: Player height
        """
        # Update orbit angle
        self.orbit_angle += self.orbit_speed * dt
        if self.orbit_angle > 2 * math.pi:
            self.orbit_angle -= 2 * math.pi

        # Update pulse/flicker animations
        self.yin_pulse_offset += self.yin_pulse_speed * dt
        self.yang_flicker_offset += self.yang_flicker_speed * dt

        # Update particles
        if self.enable_particles:
            self._update_particles(dt, player_x, player_y, player_width, player_height)

    def _update_particles(self, dt: float, player_x: float, player_y: float,
                         player_width: int, player_height: int) -> None:
        """
        Update particle effects for orbs.

        Args:
            dt: Delta time
            player_x: Player X position
            player_y: Player Y position
            player_width: Player width
            player_height: Player height
        """
        # Update existing particles
        for particle in self.particles[:]:
            particle['lifetime'] -= dt
            particle['y'] -= particle['speed'] * dt  # Float upward
            particle['alpha'] *= 0.95  # Fade out

            if particle['lifetime'] <= 0 or particle['alpha'] < 10:
                self.particles.remove(particle)

        # Spawn new particles (occasionally)
        if len(self.particles) < 20:  # Max 20 particles
            # Calculate orb positions
            player_center_x = player_x + player_width / 2
            player_center_y = player_y + player_height / 2

            # Spawn Yin particle (if active)
            if self.yin_active and (self.yin_pulse_offset % 0.5 < 0.1):
                yin_x, yin_y = self._get_yin_position(player_center_x, player_center_y)
                self._spawn_particle(yin_x, yin_y, (220, 220, 255))

            # Spawn Yang particle (if active)
            if self.yang_active and (self.yang_flicker_offset % 0.3 < 0.1):
                yang_x, yang_y = self._get_yang_position(player_center_x, player_center_y)
                self._spawn_particle(yang_x, yang_y, (255, 220, 150))

    def _spawn_particle(self, x: float, y: float, color: Tuple[int, int, int]) -> None:
        """
        Spawn a small particle at orb location.

        Args:
            x: Particle X position
            y: Particle Y position
            color: Particle color (RGB)
        """
        import random

        particle = {
            'x': x + random.uniform(-3, 3),
            'y': y + random.uniform(-3, 3),
            'color': color,
            'lifetime': random.uniform(0.5, 1.0),
            'speed': random.uniform(10, 20),  # Upward speed
            'alpha': 150
        }
        self.particles.append(particle)

    def _get_yin_position(self, player_center_x: float, player_center_y: float) -> Tuple[float, float]:
        """
        Get Yin orb position (left side of orbit).

        Args:
            player_center_x: Player center X
            player_center_y: Player center Y

        Returns:
            (x, y) tuple for Yin position
        """
        # Yin orbits on the left side (angle offset of π)
        angle = self.orbit_angle + math.pi
        offset_x = math.cos(angle) * self.orbit_radius
        offset_y = math.sin(angle) * self.orbit_radius

        return (player_center_x + offset_x, player_center_y + offset_y)

    def _get_yang_position(self, player_center_x: float, player_center_y: float) -> Tuple[float, float]:
        """
        Get Yang orb position (right side of orbit).

        Args:
            player_center_x: Player center X
            player_center_y: Player center Y

        Returns:
            (x, y) tuple for Yang position
        """
        # Yang orbits on the right side (no angle offset)
        angle = self.orbit_angle
        offset_x = math.cos(angle) * self.orbit_radius
        offset_y = math.sin(angle) * self.orbit_radius

        return (player_center_x + offset_x, player_center_y + offset_y)

    def render(self, screen: pygame.Surface, player_x: float, player_y: float,
               player_width: int, player_height: int, camera_x: float = 0.0, camera_y: float = 0.0) -> None:
        """
        Render companion orbs around player.

        Args:
            screen: Target surface to render to
            player_x: Player X position (world space)
            player_y: Player Y position (world space)
            player_width: Player width
            player_height: Player height
            camera_x: Camera X offset
            camera_y: Camera Y offset
        """
        # Calculate player center in world space
        player_center_x = player_x + player_width / 2
        player_center_y = player_y + player_height / 2

        # Render particles first (behind orbs)
        if self.enable_particles:
            self._render_particles(screen, camera_x, camera_y)

        # Render Yin (if active)
        if self.yin_active:
            yin_x, yin_y = self._get_yin_position(player_center_x, player_center_y)
            self._render_yin(screen, yin_x, yin_y, camera_x, camera_y)

        # Render Yang (if active)
        if self.yang_active:
            yang_x, yang_y = self._get_yang_position(player_center_x, player_center_y)
            self._render_yang(screen, yang_x, yang_y, camera_x, camera_y)

    def _render_yin(self, screen: pygame.Surface, world_x: float, world_y: float,
                    camera_x: float, camera_y: float) -> None:
        """
        Render Yin orb (white, steady glow).

        Args:
            screen: Target surface
            world_x: Yin X position in world space
            world_y: Yin Y position in world space
            camera_x: Camera X offset
            camera_y: Camera Y offset
        """
        # Convert to screen space
        screen_x = int(world_x - camera_x)
        screen_y = int(world_y - camera_y)

        # Pulse animation (gentle, slow)
        pulse = 0.85 + 0.15 * math.sin(self.yin_pulse_offset)

        # Render glow (outer layer)
        glow_surface = pygame.Surface((self.yin_glow_size * 2, self.yin_glow_size * 2), pygame.SRCALPHA)
        glow_alpha = int(80 * pulse)
        glow_color = (*self.yin_color, glow_alpha)

        for radius in range(self.yin_glow_size, self.yin_size, -2):
            alpha = int(glow_alpha * (1.0 - radius / self.yin_glow_size))
            color = (*self.yin_color, alpha)
            pygame.draw.circle(glow_surface, color, (self.yin_glow_size, self.yin_glow_size), radius)

        screen.blit(glow_surface, (screen_x - self.yin_glow_size, screen_y - self.yin_glow_size))

        # Render core (bright white center)
        core_color = (255, 255, 255)
        pygame.draw.circle(screen, core_color, (screen_x, screen_y), self.yin_size)

        # Render orb body (tinted)
        orb_color = tuple(int(c * pulse) for c in self.yin_color)
        pygame.draw.circle(screen, orb_color, (screen_x, screen_y), self.yin_size - 2)

    def _render_yang(self, screen: pygame.Surface, world_x: float, world_y: float,
                     camera_x: float, camera_y: float) -> None:
        """
        Render Yang orb (gold, flickering glow).

        Args:
            screen: Target surface
            world_x: Yang X position in world space
            world_y: Yang Y position in world space
            camera_x: Camera X offset
            camera_y: Camera Y offset
        """
        # Convert to screen space
        screen_x = int(world_x - camera_x)
        screen_y = int(world_y - camera_y)

        # Flicker animation (energetic, faster)
        flicker = 0.7 + 0.3 * abs(math.sin(self.yang_flicker_offset))

        # Render glow (outer layer)
        glow_surface = pygame.Surface((self.yang_glow_size * 2, self.yang_glow_size * 2), pygame.SRCALPHA)
        glow_alpha = int(100 * flicker)
        glow_color = (*self.yang_color, glow_alpha)

        for radius in range(self.yang_glow_size, self.yang_size, -2):
            alpha = int(glow_alpha * (1.0 - radius / self.yang_glow_size))
            color = (*self.yang_color, alpha)
            pygame.draw.circle(glow_surface, color, (self.yang_glow_size, self.yang_glow_size), radius)

        screen.blit(glow_surface, (screen_x - self.yang_glow_size, screen_y - self.yang_glow_size))

        # Render core (bright yellow-white center)
        core_color = (255, 240, 200)
        pygame.draw.circle(screen, core_color, (screen_x, screen_y), self.yang_size)

        # Render orb body (gold tinted)
        orb_color = tuple(int(c * flicker) for c in self.yang_color)
        pygame.draw.circle(screen, orb_color, (screen_x, screen_y), self.yang_size - 2)

    def _render_particles(self, screen: pygame.Surface, camera_x: float, camera_y: float) -> None:
        """
        Render particle effects.

        Args:
            screen: Target surface
            camera_x: Camera X offset
            camera_y: Camera Y offset
        """
        for particle in self.particles:
            screen_x = int(particle['x'] - camera_x)
            screen_y = int(particle['y'] - camera_y)

            # Draw small particle
            alpha = int(particle['alpha'])
            if alpha > 0:
                color = (*particle['color'], alpha)
                particle_surface = pygame.Surface((4, 4), pygame.SRCALPHA)
                pygame.draw.circle(particle_surface, color, (2, 2), 2)
                screen.blit(particle_surface, (screen_x - 2, screen_y - 2))

    def set_yin_active(self, active: bool) -> None:
        """
        Set Yin orb visibility.

        Args:
            active: Whether Yin should be visible
        """
        self.yin_active = active

    def set_yang_active(self, active: bool) -> None:
        """
        Set Yang orb visibility.

        Args:
            active: Whether Yang should be visible
        """
        self.yang_active = active

    def set_both_active(self, active: bool) -> None:
        """
        Set both orbs visibility (for story events).

        Args:
            active: Whether both orbs should be visible
        """
        self.yin_active = active
        self.yang_active = active

    def are_companions_present(self) -> bool:
        """
        Check if at least one companion is visible.

        Returns:
            True if Yin or Yang is active
        """
        return self.yin_active or self.yang_active

    def get_orbit_positions(self, player_x: float, player_y: float,
                           player_width: int, player_height: int) -> Tuple[Optional[Tuple[float, float]],
                                                                            Optional[Tuple[float, float]]]:
        """
        Get current orb positions in world space.

        Args:
            player_x: Player X position
            player_y: Player Y position
            player_width: Player width
            player_height: Player height

        Returns:
            Tuple of (yin_position, yang_position) where each is (x, y) or None if inactive
        """
        player_center_x = player_x + player_width / 2
        player_center_y = player_y + player_height / 2

        yin_pos = self._get_yin_position(player_center_x, player_center_y) if self.yin_active else None
        yang_pos = self._get_yang_position(player_center_x, player_center_y) if self.yang_active else None

        return (yin_pos, yang_pos)

    def reset_animation(self) -> None:
        """Reset animation state (for cutscenes or respawns)."""
        self.orbit_angle = 0.0
        self.yin_pulse_offset = 0.0
        self.yang_flicker_offset = 1.57
        self.particles.clear()

    def get_description(self) -> str:
        """
        Get description of companion state.

        Returns:
            Human-readable description
        """
        if self.yin_active and self.yang_active:
            return "Yin & Yang orbit peacefully"
        elif self.yin_active:
            return "Only Yin remains (steady white glow)"
        elif self.yang_active:
            return "Only Yang remains (flickering gold)"
        else:
            return "Companions absent (consumed)"
