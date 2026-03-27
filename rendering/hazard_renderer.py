"""
Hazard Renderer - Visual rendering for hazards

Renders spike hazards, void zones, and other environmental dangers.
"""

import math

import pygame

# Module-level surface cache: (width, height) -> SRCALPHA Surface.
# Avoids per-frame pygame.Surface(SRCALPHA) allocations inside the render loop.
_overlay_cache: dict[tuple[int, int], pygame.Surface] = {}


def render_hazard(surface: pygame.Surface, hazard, camera):
    """
    Render a single hazard with camera transform

    Args:
        surface: Surface to render on
        hazard: Hazard object to render
        camera: Camera system for coordinate transformation
    """
    if not hazard.active:
        return

    # Get render position
    render_x, render_y = hazard.get_render_position()

    # Create rect for camera transform
    hazard_rect = pygame.Rect(int(render_x), int(render_y), hazard.width, hazard.height)

    # Apply camera transform
    screen_rect = camera.apply(hazard_rect)

    # Viewport cull — skip hazards fully outside the render surface
    if not screen_rect.colliderect(surface.get_rect()):
        return

    # Draw based on hazard type
    if hazard.hazard_type == "spike":
        render_spike(surface, screen_rect, hazard)
    elif hazard.hazard_type == "void":
        render_void(surface, screen_rect, hazard)
    elif hazard.hazard_type == "poison":
        render_poison(surface, screen_rect, hazard)


def render_spike(surface: pygame.Surface, rect: pygame.Rect, hazard):
    """
    Render spike hazard (upward-pointing triangles)

    Visual style: Gray triangular spikes with dark outlines
    """
    # Number of spikes based on width (one every 8 pixels)
    num_spikes = max(1, rect.width // 8)
    spike_width = rect.width / num_spikes

    for i in range(num_spikes):
        # Calculate spike position
        left_x = rect.left + int(i * spike_width)
        right_x = rect.left + int((i + 1) * spike_width)
        base_y = rect.bottom
        tip_y = rect.top

        # Spike triangle points
        points = [
            (left_x, base_y),  # Bottom left
            (right_x, base_y),  # Bottom right
            ((left_x + right_x) // 2, tip_y),  # Top point
        ]

        # Draw spike outline (dark)
        pygame.draw.polygon(surface, hazard.outline_color, points)

        # Draw spike fill (lighter gray)
        inner_points = [
            (left_x + 2, base_y - 1),
            (right_x - 2, base_y - 1),
            ((left_x + right_x) // 2, tip_y + 2),
        ]
        if rect.width >= 16:  # Only draw inner if spike is large enough
            pygame.draw.polygon(surface, hazard.color, inner_points)

    # Add subtle shadow at base
    if rect.height >= 8:
        shadow_rect = pygame.Rect(rect.left, rect.bottom - 2, rect.width, 2)
        pygame.draw.rect(surface, (60, 60, 60), shadow_rect)


def render_void(surface: pygame.Surface, rect: pygame.Rect, hazard):
    """
    Render void/pit hazard (dark zone with shimmer effect)

    Visual style: Dark purple/black with subtle animated shimmer
    """
    # Base void color (very dark)
    pygame.draw.rect(surface, hazard.color, rect)

    # Animated shimmer effect (subtle pulsing)
    time_ms = pygame.time.get_ticks()
    shimmer = abs(math.sin(time_ms / 800.0)) * 30  # 0-30 brightness pulse

    # Add shimmer overlay
    shimmer_color = (
        int(hazard.color[0] + shimmer),
        int(hazard.color[1] + shimmer * 0.5),
        int(hazard.color[2] + shimmer * 1.5),
    )

    # Draw shimmer as translucent overlay (reuse cached surface — avoids per-frame alloc)
    key = (rect.width, rect.height)
    shimmer_surface = _overlay_cache.get(key)
    if shimmer_surface is None:
        shimmer_surface = pygame.Surface(key, pygame.SRCALPHA)
        _overlay_cache[key] = shimmer_surface
    shimmer_surface.fill(shimmer_color + (40,))  # Low alpha for subtlety
    surface.blit(shimmer_surface, rect.topleft)

    # Add warning border (pulsing red)
    border_pulse = abs(math.sin(time_ms / 400.0))
    border_color = (int(100 + 155 * border_pulse), 0, 0)  # Pulsing red
    pygame.draw.rect(surface, border_color, rect, 2)


def render_poison(surface: pygame.Surface, rect: pygame.Rect, hazard):
    """
    Render poison/gas hazard (health-sapping zone)

    Visual style: Green haze with subtle pulsing
    """
    time_ms = pygame.time.get_ticks()
    pulse = 0.5 + 0.5 * abs(math.sin(time_ms / 700.0))
    base_color = (40, 140, 70)
    overlay_color = (
        int(base_color[0] + 40 * pulse),
        int(base_color[1] + 60 * pulse),
        int(base_color[2] + 40 * pulse),
    )

    key = (rect.width, rect.height)
    haze = _overlay_cache.get(key)
    if haze is None:
        haze = pygame.Surface(key, pygame.SRCALPHA)
        _overlay_cache[key] = haze
    haze.fill(overlay_color + (90,))
    surface.blit(haze, rect.topleft)

    border_color = (30, 180, 90)
    pygame.draw.rect(surface, border_color, rect, 2)


def render_hazards(surface: pygame.Surface, hazards: list, camera):
    """
    Render all active hazards

    Args:
        surface: Surface to render on
        hazards: List of hazard objects
        camera: Camera system
    """
    for hazard in hazards:
        if hazard.active:
            render_hazard(surface, hazard, camera)
