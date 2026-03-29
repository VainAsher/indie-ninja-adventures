"""
Remote player ghost renderer — multiplayer Phase N4.

Draws a blue semi-transparent ghost silhouette for each remote peer player,
with a directional indicator, health bar, and slot label above their head.

No sprite sheet access needed — purely pygame.draw primitives so this works
without the AnimationStateMachine wiring that the local player uses.
"""

from __future__ import annotations

import pygame

from entities.remote_player import REMOTE_H, REMOTE_W, RemotePlayer

# ── Colour palette ────────────────────────────────────────────────────────────
_BODY_ALIVE = (80, 160, 255, 140)       # blue ghost, alive
_BODY_DEAD = (120, 120, 120, 60)        # grey ghost, dead
_BODY_OUTLINE = (140, 200, 255, 200)    # lighter blue outline
_ARROW_COLOR = (255, 255, 180)          # pale yellow direction arrow
_HEALTH_BG = (60, 20, 20)
_HEALTH_FG = (80, 220, 80)
_HEALTH_LOW = (220, 60, 60)
_LABEL_FG = (200, 230, 255)
_LABEL_SHADOW = (10, 10, 30)

# Pixels of padding above the hitbox top edge before drawing the label+bar
_OVERHEAD_OFFSET = 4
_BAR_W = 36
_BAR_H = 5
_LABEL_FONT_SIZE = 13

_font_cache: dict[int, pygame.font.Font] = {}


def _get_font(size: int) -> pygame.font.Font:
    if size not in _font_cache:
        try:
            _font_cache[size] = pygame.font.SysFont("consolas", size, bold=True)
        except Exception:
            _font_cache[size] = pygame.font.Font(None, size)
    return _font_cache[size]


def draw(
    surface: pygame.Surface,
    remote: RemotePlayer,
    camera: object,
    now_ms: float,
) -> None:
    """
    Draw *remote* onto *surface* with a camera-adjusted position.

    *camera* must expose an `apply(rect)` method that converts a world-space
    pygame.Rect to a screen-space pygame.Rect (same interface as CameraSystem).
    *now_ms* is `pygame.time.get_ticks()` used for interpolation.
    """
    # Interpolated world position
    wx, wy = remote.interpolated_pos(now_ms)

    world_rect = pygame.Rect(int(wx), int(wy), REMOTE_W, REMOTE_H)
    screen_rect: pygame.Rect = camera.apply(world_rect)

    # ── Body silhouette (alpha surface) ─────────────────────────────────────
    body_surf = pygame.Surface((REMOTE_W, REMOTE_H), pygame.SRCALPHA)
    fill_color = _BODY_DEAD if remote.is_dead else _BODY_ALIVE
    pygame.draw.rect(body_surf, fill_color, (0, 0, REMOTE_W, REMOTE_H), border_radius=4)

    # Outline
    outline_color = (*_BODY_OUTLINE[:3], 80 if remote.is_dead else _BODY_OUTLINE[3])
    pygame.draw.rect(body_surf, outline_color, (0, 0, REMOTE_W, REMOTE_H), width=2, border_radius=4)

    # Directional arrow inside body (small triangle indicating facing)
    if not remote.is_dead:
        cx = REMOTE_W // 2
        cy = REMOTE_H // 2
        aw = 7
        ah = 5
        if remote.facing >= 0:  # facing right
            pts = [(cx + aw, cy), (cx - aw // 2, cy - ah), (cx - aw // 2, cy + ah)]
        else:  # facing left
            pts = [(cx - aw, cy), (cx + aw // 2, cy - ah), (cx + aw // 2, cy + ah)]
        pygame.draw.polygon(body_surf, _ARROW_COLOR, pts)

    surface.blit(body_surf, screen_rect.topleft)

    if remote.is_dead:
        return

    # ── Overhead UI ──────────────────────────────────────────────────────────
    overhead_y = screen_rect.top - _OVERHEAD_OFFSET

    # Health bar
    bar_x = screen_rect.centerx - _BAR_W // 2
    bar_y = overhead_y - _BAR_H - 14   # 14px above top for the label

    # Background
    pygame.draw.rect(surface, _HEALTH_BG, (bar_x, bar_y, _BAR_W, _BAR_H))

    # Fill (proportional to health)
    hp_ratio = max(0.0, min(1.0, remote.health / max(1, remote.max_health)))
    fill_w = int(_BAR_W * hp_ratio)
    bar_color = _HEALTH_FG if hp_ratio > 0.35 else _HEALTH_LOW
    if fill_w > 0:
        pygame.draw.rect(surface, bar_color, (bar_x, bar_y, fill_w, _BAR_H))

    # Bar border
    pygame.draw.rect(surface, _BODY_OUTLINE[:3], (bar_x, bar_y, _BAR_W, _BAR_H), width=1)

    # Slot label (e.g. "P2") above health bar
    font = _get_font(_LABEL_FONT_SIZE)
    label_surf = font.render(remote.display_name, True, _LABEL_FG)
    lw = label_surf.get_width()
    lx = screen_rect.centerx - lw // 2
    ly = bar_y - label_surf.get_height() - 1

    # Shadow pass
    shadow_surf = font.render(remote.display_name, True, _LABEL_SHADOW)
    surface.blit(shadow_surf, (lx + 1, ly + 1))
    surface.blit(label_surf, (lx, ly))


def draw_all(
    surface: pygame.Surface,
    remote_players: dict[int, RemotePlayer],
    camera: object,
    now_ms: float,
) -> None:
    """Convenience wrapper — draw every remote player in the dict."""
    for rp in remote_players.values():
        draw(surface, rp, camera, now_ms)
