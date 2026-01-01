"""
Pickup Renderer - Visual rendering for pickups

Renders coins, health, and collectibles with animations.
"""

import math

import pygame


def render_pickup(surface: pygame.Surface, pickup, camera):
    """
    Render a single pickup with bobbing and rotation animations.

    Args:
        surface: Surface to render on
        pickup: Pickup object to render
        camera: Camera system for coordinate transformation
    """
    if not pickup.alive:
        return

    # Get render position (with bobbing)
    render_x, render_y = pickup.get_render_position()

    # Create rect for camera transform
    pickup_rect = pygame.Rect(int(render_x), int(render_y), pickup.width, pickup.height)

    # Apply camera transform
    screen_rect = camera.apply(pickup_rect)

    # Draw based on pickup type
    if pickup.pickup_type == "coin":
        render_coin(surface, screen_rect, pickup)
    elif pickup.pickup_type == "health":
        render_health(surface, screen_rect, pickup)
    elif pickup.pickup_type == "collectible":
        render_collectible(surface, screen_rect, pickup)


def render_coin(surface: pygame.Surface, rect: pygame.Rect, pickup):
    """Render a coin pickup (golden circle)"""
    center = rect.center

    # Pulsing effect
    pulse = abs(math.sin(pygame.time.get_ticks() / 300.0))
    radius = int(rect.width / 2 * (0.8 + 0.2 * pulse))

    # Outer glow
    pygame.draw.circle(surface, (255, 235, 100), center, radius + 2)

    # Main coin
    pygame.draw.circle(surface, pickup.color, center, radius)

    # Inner highlight
    highlight_offset = int(radius * 0.3)
    highlight_pos = (center[0] - highlight_offset, center[1] - highlight_offset)
    highlight_radius = int(radius * 0.4)
    pygame.draw.circle(surface, (255, 255, 200), highlight_pos, highlight_radius)


def render_health(surface: pygame.Surface, rect: pygame.Rect, pickup):
    """Render a health pickup (red heart)"""
    center = rect.center
    size = rect.width

    # Pulsing effect
    pulse = abs(math.sin(pygame.time.get_ticks() / 400.0))
    scale = 0.9 + 0.1 * pulse

    # Simple heart shape using two circles and a triangle
    heart_size = int(size * scale)

    # Top two circles
    left_circle = (center[0] - heart_size // 4, center[1] - heart_size // 4)
    right_circle = (center[0] + heart_size // 4, center[1] - heart_size // 4)
    circle_radius = heart_size // 3

    pygame.draw.circle(surface, pickup.color, left_circle, circle_radius)
    pygame.draw.circle(surface, pickup.color, right_circle, circle_radius)

    # Bottom triangle (pointing down)
    bottom_point = (center[0], center[1] + heart_size // 2)
    left_point = (center[0] - heart_size // 2, center[1] - heart_size // 6)
    right_point = (center[0] + heart_size // 2, center[1] - heart_size // 6)

    pygame.draw.polygon(surface, pickup.color, [bottom_point, left_point, right_point])

    # Highlight
    highlight_pos = (center[0] - heart_size // 6, center[1] - heart_size // 6)
    pygame.draw.circle(surface, (255, 150, 150), highlight_pos, circle_radius // 3)


def render_collectible(surface: pygame.Surface, rect: pygame.Rect, pickup):
    """Render a special collectible (cyan star)"""
    center = rect.center
    size = rect.width

    # Rotation effect
    rotation = pickup.rotation

    # Star points
    points = []
    for i in range(8):
        angle = rotation + (i * math.pi / 4)
        radius = size / 2 if i % 2 == 0 else size / 4
        x = center[0] + int(radius * math.cos(angle))
        y = center[1] + int(radius * math.sin(angle))
        points.append((x, y))

    # Outer glow
    glow_points = []
    for i in range(8):
        angle = rotation + (i * math.pi / 4)
        radius = (size / 2 + 2) if i % 2 == 0 else (size / 4 + 2)
        x = center[0] + int(radius * math.cos(angle))
        y = center[1] + int(radius * math.sin(angle))
        glow_points.append((x, y))

    pygame.draw.polygon(surface, (100, 255, 255), glow_points)

    # Main star
    pygame.draw.polygon(surface, pickup.color, points)

    # Center highlight
    pygame.draw.circle(surface, (200, 255, 255), center, size // 6)


def render_pickups(surface: pygame.Surface, pickups: list, camera):
    """
    Render all alive pickups.

    Args:
        surface: Surface to render on
        pickups: List of pickup objects
        camera: Camera system
    """
    for pickup in pickups:
        if pickup.alive:
            render_pickup(surface, pickup, camera)
