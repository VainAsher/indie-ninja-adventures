"""
Remote player sprite renderer — multiplayer Phase N4 (colored sprites).

Draws remote peer players using the same spritesheets as the local player,
color-tinted by slot number:
  slot 0 — base ninja  (no tint)
  slot 1 — red         (220, 80, 80)
  slot 2 — green       (80, 200, 80)
  slot 3 — purple      (180, 80, 220)

Falls back to a ghost silhouette if the animation SM has no frame to offer
(e.g. during the first frame before any state update arrives).
"""

from __future__ import annotations

import pygame

from entities.remote_player import REMOTE_H, REMOTE_W, RemotePlayer

# ── Slot tint colours ─────────────────────────────────────────────────────────
# None = no tint (slot 0, default ninja). Others multiply RGB channels via
# BLEND_RGB_MULT so white pixels take the tint and black pixels stay black.
_SLOT_TINT: dict[int, tuple[int, int, int] | None] = {
    0: None,
    1: (220, 80,  80),   # red
    2: (80,  200, 80),   # green
    3: (180, 80,  220),  # purple
}

# ── Ghost fallback colours (RGBA) ─────────────────────────────────────────────
_GHOST_ALIVE: dict[int, tuple[int, int, int, int]] = {
    0: (80,  160, 255, 140),
    1: (220, 80,  80,  140),
    2: (80,  200, 80,  140),
    3: (180, 80,  220, 140),
}
_GHOST_DEAD = (120, 120, 120, 60)

# ── Overhead UI ───────────────────────────────────────────────────────────────
_HEALTH_BG  = (60,  20,  20)
_HEALTH_FG  = (80,  220, 80)
_HEALTH_LOW = (220, 60,  60)
_BAR_BORDER = (140, 200, 255)
_LABEL_FG   = (200, 230, 255)
_LABEL_SHADOW = (10, 10, 30)

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


def _tint_surface(
    surf: pygame.Surface,
    tint: tuple[int, int, int],
) -> pygame.Surface:
    """Return a copy of *surf* with RGB channels multiplied by *tint*."""
    tinted = surf.copy()
    tinted.fill(tint, special_flags=pygame.BLEND_RGB_MULT)
    return tinted


def _draw_ghost(
    surface: pygame.Surface,
    remote: RemotePlayer,
    screen_rect: pygame.Rect,
) -> None:
    """Semi-transparent silhouette — used when no sprite frame is available."""
    ghost = pygame.Surface((screen_rect.width, screen_rect.height), pygame.SRCALPHA)
    fill = _GHOST_DEAD if remote.is_dead else _GHOST_ALIVE.get(remote.slot, _GHOST_ALIVE[0])
    pygame.draw.rect(ghost, fill, ghost.get_rect(), border_radius=4)
    surface.blit(ghost, screen_rect.topleft)


def draw(
    surface: pygame.Surface,
    remote: RemotePlayer,
    camera: object,
    now_ms: float,
) -> None:
    """
    Draw *remote* onto *surface* at the camera-adjusted position.

    Uses the remote player's AnimationStateMachine (``remote.anim_sm``) to pick
    the correct sprite frame, then applies a slot-based colour tint.
    Falls back to a ghost silhouette if ``anim_sm`` is None or returns no frame.
    """
    wx, wy = remote.interpolated_pos(now_ms)
    world_rect = pygame.Rect(int(wx), int(wy), REMOTE_W, REMOTE_H)
    screen_rect: pygame.Rect = camera.apply(world_rect)

    # ── Sprite (or ghost fallback) ────────────────────────────────────────────
    drawn_sprite = False
    if remote.anim_sm is not None:
        raw_surf: pygame.Surface | None = remote.anim_sm.get_frame(remote.facing)
        if raw_surf is not None:
            w, h = screen_rect.size
            if w > 0 and h > 0:
                scaled = pygame.transform.scale(raw_surf, (w, h))
                tint = _SLOT_TINT.get(remote.slot)
                if tint is not None:
                    scaled = _tint_surface(scaled, tint)
                surface.blit(scaled, screen_rect.topleft)
                drawn_sprite = True

    if not drawn_sprite:
        _draw_ghost(surface, remote, screen_rect)

    if remote.is_dead:
        return

    # ── Overhead UI ───────────────────────────────────────────────────────────
    overhead_y = screen_rect.top - _OVERHEAD_OFFSET
    bar_x = screen_rect.centerx - _BAR_W // 2
    bar_y = overhead_y - _BAR_H - 14  # 14 px gap for the label

    pygame.draw.rect(surface, _HEALTH_BG, (bar_x, bar_y, _BAR_W, _BAR_H))
    hp_ratio = max(0.0, min(1.0, remote.health / max(1, remote.max_health)))
    fill_w = int(_BAR_W * hp_ratio)
    bar_color = _HEALTH_FG if hp_ratio > 0.35 else _HEALTH_LOW
    if fill_w > 0:
        pygame.draw.rect(surface, bar_color, (bar_x, bar_y, fill_w, _BAR_H))
    pygame.draw.rect(surface, _BAR_BORDER, (bar_x, bar_y, _BAR_W, _BAR_H), width=1)

    font = _get_font(_LABEL_FONT_SIZE)
    label_surf = font.render(remote.display_name, True, _LABEL_FG)
    lw = label_surf.get_width()
    lx = screen_rect.centerx - lw // 2
    ly = bar_y - label_surf.get_height() - 1
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
