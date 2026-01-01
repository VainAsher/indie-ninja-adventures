"""
Hub Visual Effects - Rendering effects for hub atmosphere

Provides visual effects for hub rendering based on story state:
- Brightness overlay (darkening effect)
- Portal glow intensity
- Constellation rendering (Yin/Yang stars)

Version: v0.7.0
"""

import math

import pygame


class HubEffectsRenderer:
    """
    Renders visual effects for the hub based on story state.

    Effects:
    - Brightness overlay (dark overlay that dims the scene)
    - Portal dimming and color shifts
    - Constellation rendering (postgame Yin/Yang stars)
    """

    def __init__(self, screen_width: int = 1280, screen_height: int = 720):
        """
        Initialize hub effects renderer.

        Args:
            screen_width: Screen width in pixels
            screen_height: Screen height in pixels
        """
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Create overlay surface for brightness effect
        self.overlay_surface = pygame.Surface((screen_width, screen_height))
        self.overlay_surface.fill((0, 0, 0))  # Black overlay

        # Constellation state (for postgame)
        self.constellation_visible = False
        self.constellation_twinkle_offset = 0.0

    def render_brightness_overlay(self, screen: pygame.Surface, brightness: float) -> None:
        """
        Render dark overlay based on brightness value.

        Args:
            screen: Target surface to render to
            brightness: Brightness value (0.0 = completely dark, 1.0 = fully bright)
        """
        # Calculate overlay alpha (inverse of brightness)
        # brightness 1.0 -> alpha 0 (no overlay)
        # brightness 0.0 -> alpha 255 (maximum darkness)
        overlay_alpha = int((1.0 - brightness) * 255)

        if overlay_alpha > 0:
            self.overlay_surface.set_alpha(overlay_alpha)
            screen.blit(self.overlay_surface, (0, 0))

    def get_portal_glow_intensity(self, atmosphere: str) -> float:
        """
        Get portal glow intensity based on atmosphere.

        Args:
            atmosphere: Current hub atmosphere

        Returns:
            Glow intensity multiplier (0.0 - 1.0)
        """
        intensity_map = {
            "vibrant": 1.0,
            "dimming": 0.7,
            "dark": 0.3,
            "recovering": 0.5,
            "restored": 0.95,
            "bittersweet": 1.0,
        }

        return intensity_map.get(atmosphere, 1.0)

    def get_portal_color_shift(self, atmosphere: str) -> tuple[float, float, float]:
        """
        Get portal color shift multiplier based on atmosphere.

        Args:
            atmosphere: Current hub atmosphere

        Returns:
            RGB color multiplier tuple (0.0 - 1.0 per channel)
        """
        color_shift_map = {
            "vibrant": (1.0, 1.0, 1.0),
            "dimming": (0.9, 0.9, 1.0),
            "dark": (0.7, 0.7, 0.9),
            "recovering": (0.8, 0.9, 1.0),
            "restored": (1.0, 1.0, 1.0),
            "bittersweet": (1.0, 0.95, 0.9),
        }

        return color_shift_map.get(atmosphere, (1.0, 1.0, 1.0))

    def update_constellation(self, dt: float) -> None:
        """
        Update constellation twinkle animation.

        Args:
            dt: Delta time in seconds
        """
        if self.constellation_visible:
            self.constellation_twinkle_offset += dt * 2.0  # Twinkle speed

    def render_constellation(
        self, screen: pygame.Surface, camera_x: float = 0.0, camera_y: float = 0.0
    ) -> None:
        """
        Render Yin & Yang constellation (postgame).

        Args:
            screen: Target surface
            camera_x: Camera X offset
            camera_y: Camera Y offset
        """
        if not self.constellation_visible:
            return

        # Constellation position (top center of screen, world space)
        constellation_x = 640 + camera_x
        constellation_y = 100 + camera_y

        # Yin & Yang constellation pattern (8 stars total)
        # Yin (left): 4 white stars in crescent
        # Yang (right): 4 gold stars in crescent

        yin_positions = [(-30, -10), (-25, 5), (-20, 20), (-15, 10)]

        yang_positions = [(30, -10), (25, 5), (20, 20), (15, 10)]

        # Render Yin stars (white)
        for i, (offset_x, offset_y) in enumerate(yin_positions):
            star_x = constellation_x + offset_x
            star_y = constellation_y + offset_y

            # Twinkle effect (vary alpha)
            twinkle_phase = self.constellation_twinkle_offset + i * 0.5
            alpha = 0.7 + 0.3 * math.sin(twinkle_phase)

            # Star color (white with slight blue tint)
            color = (int(220 * alpha), int(220 * alpha), int(255 * alpha))

            # Draw star (small circle with glow)
            self._draw_star(screen, star_x, star_y, color, alpha)

        # Render Yang stars (gold)
        for i, (offset_x, offset_y) in enumerate(yang_positions):
            star_x = constellation_x + offset_x
            star_y = constellation_y + offset_y

            # Twinkle effect (offset from Yin)
            twinkle_phase = self.constellation_twinkle_offset + i * 0.5 + 1.0
            alpha = 0.7 + 0.3 * math.sin(twinkle_phase)

            # Star color (gold)
            color = (int(255 * alpha), int(220 * alpha), int(150 * alpha))

            # Draw star
            self._draw_star(screen, star_x, star_y, color, alpha)

    def _draw_star(
        self, screen: pygame.Surface, x: float, y: float, color: tuple[int, int, int], alpha: float
    ) -> None:
        """
        Draw a single star with glow effect.

        Args:
            screen: Target surface
            x: Star X position
            y: Star Y position
            color: RGB color tuple
            alpha: Star alpha/brightness
        """
        # Star core (bright pixel)
        pygame.draw.circle(screen, color, (int(x), int(y)), 2)

        # Glow effect (larger transparent circle)
        glow_surface = pygame.Surface((12, 12), pygame.SRCALPHA)
        glow_color = (*color, int(100 * alpha))
        pygame.draw.circle(glow_surface, glow_color, (6, 6), 6)

        screen.blit(glow_surface, (int(x) - 6, int(y) - 6))

    def set_constellation_visible(self, visible: bool) -> None:
        """
        Set constellation visibility (for postgame).

        Args:
            visible: Whether constellation should be visible
        """
        self.constellation_visible = visible

    def apply_portal_effects(
        self, portal_surface: pygame.Surface, atmosphere: str
    ) -> pygame.Surface:
        """
        Apply atmosphere-based effects to portal rendering.

        Args:
            portal_surface: Portal sprite surface
            atmosphere: Current hub atmosphere

        Returns:
            Modified portal surface with effects applied
        """
        # Get glow intensity and color shift
        glow_intensity = self.get_portal_glow_intensity(atmosphere)
        color_shift = self.get_portal_color_shift(atmosphere)

        # Apply color shift
        modified_surface = portal_surface.copy()

        # Simple color multiplication (tinting)
        # This is a basic approach - more advanced would use pixel-level manipulation
        if color_shift != (1.0, 1.0, 1.0):
            # Create color overlay
            overlay = pygame.Surface(modified_surface.get_size(), pygame.SRCALPHA)
            overlay_color = (
                int(255 * color_shift[0]),
                int(255 * color_shift[1]),
                int(255 * color_shift[2]),
                int(100 * (1.0 - glow_intensity)),  # More overlay when dimmed
            )
            overlay.fill(overlay_color)
            modified_surface.blit(overlay, (0, 0), special_flags=pygame.BLEND_MULT)

        # Apply glow intensity (alpha modulation)
        if glow_intensity < 1.0:
            modified_surface.set_alpha(int(255 * glow_intensity))

        return modified_surface

    def get_vignette_intensity(self, atmosphere: str) -> float:
        """
        Get vignette intensity (darkening around edges).

        Args:
            atmosphere: Current hub atmosphere

        Returns:
            Vignette intensity (0.0 - 1.0)
        """
        vignette_map = {
            "vibrant": 0.0,
            "dimming": 0.1,
            "dark": 0.3,
            "recovering": 0.15,
            "restored": 0.0,
            "bittersweet": 0.05,
        }

        return vignette_map.get(atmosphere, 0.0)

    def render_vignette(self, screen: pygame.Surface, atmosphere: str) -> None:
        """
        Render vignette effect (optional, for enhanced atmosphere).

        Args:
            screen: Target surface
            atmosphere: Current hub atmosphere
        """
        intensity = self.get_vignette_intensity(atmosphere)

        if intensity <= 0.0:
            return

        # Create radial gradient vignette
        vignette_surface = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)

        center_x = self.screen_width // 2
        center_y = self.screen_height // 2
        max_radius = int(math.sqrt(center_x**2 + center_y**2))

        # Draw concentric circles with increasing opacity
        for radius in range(max_radius, 0, -20):
            # Calculate alpha based on distance from center
            distance_ratio = radius / max_radius
            alpha = int(intensity * 200 * (1.0 - distance_ratio))

            if alpha > 0:
                color = (0, 0, 0, alpha)
                pygame.draw.circle(vignette_surface, color, (center_x, center_y), radius)

        screen.blit(vignette_surface, (0, 0))
