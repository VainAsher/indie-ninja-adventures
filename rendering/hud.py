"""
HUD helpers for Phase 5 testing and game integration.

Enhanced with heart-based health display (Phase 6).
"""

import math

import pygame


class HUDRenderer:
    def __init__(self, font_name="consolas", font_size=16):
        self.font = pygame.font.SysFont(font_name, font_size)
        self.small = pygame.font.SysFont(font_name, 14)
        self.large = pygame.font.SysFont(font_name, 20, bold=True)

        # Health display settings
        self.use_hearts = True  # Toggle between hearts and bar
        self.heart_size = 20
        self.heart_spacing = 4

    def draw_bar(
        self, surface, label, value, max_value, x, y, width, height, color, bg_color=(40, 40, 50)
    ):
        pygame.draw.rect(surface, bg_color, pygame.Rect(x, y, width, height), border_radius=4)
        if max_value > 0:
            fill_w = int(width * max(0.0, min(1.0, value / max_value)))
            pygame.draw.rect(surface, color, pygame.Rect(x, y, fill_w, height), border_radius=4)
        text = self.small.render(
            (
                f"{label}: {value:.1f}/{max_value:.1f}"
                if isinstance(value, float)
                else f"{label}: {value}/{max_value}"
            ),
            True,
            (230, 230, 240),
        )
        surface.blit(text, (x + 6, y - 16))

    def draw_heart(self, surface, x, y, filled=True, pulsing=False, pulse_time=0.0):
        """
        Draw a single heart (Zelda-style).

        Args:
            surface: Surface to draw on
            x, y: Position (top-left)
            filled: True for full heart, False for empty
            pulsing: True to pulse (low health warning)
            pulse_time: Current time for pulse animation
        """
        size = self.heart_size

        # Pulse effect for low health
        if pulsing:
            pulse = math.sin(pulse_time * 8) * 0.15 + 1.0
            size = int(size * pulse)

        # Heart colors
        if filled:
            color = (220, 20, 60)  # Crimson red
            inner_color = (255, 60, 100)  # Lighter red
        else:
            color = (80, 80, 90)  # Dark gray
            inner_color = (60, 60, 70)  # Darker gray

        # Draw heart shape using circles and triangle
        # Top two circles
        half_size = size // 2
        quarter_size = size // 4

        # Left circle
        pygame.draw.circle(surface, color, (x + quarter_size, y + quarter_size), quarter_size)
        # Right circle
        pygame.draw.circle(
            surface, color, (x + half_size + quarter_size, y + quarter_size), quarter_size
        )

        # Bottom triangle
        points = [
            (x, y + quarter_size),  # Left
            (x + size, y + quarter_size),  # Right
            (x + half_size, y + size),  # Bottom point
        ]
        pygame.draw.polygon(surface, color, points)

        # Inner highlight (if filled)
        if filled:
            small_quarter = quarter_size // 2
            # Left inner circle
            pygame.draw.circle(
                surface,
                inner_color,
                (x + quarter_size - small_quarter // 2, y + quarter_size - small_quarter // 2),
                small_quarter,
            )

    def draw_hearts(self, surface, current_hp, max_hp, x, y, low_health_time=0.0):
        """
        Draw heart containers (Zelda-style health display).

        Args:
            surface: Surface to draw on
            current_hp: Current health points
            max_hp: Maximum health points
            x, y: Starting position
            low_health_time: Time for pulsing animation (when HP <= 1)
        """
        # Draw hearts from left to right
        for i in range(max_hp):
            heart_x = x + i * (self.heart_size + self.heart_spacing)
            filled = i < current_hp
            pulsing = current_hp <= 1 and filled

            self.draw_heart(surface, heart_x, y, filled, pulsing, low_health_time)

    def draw_hud(
        self,
        surface,
        player_state,
        camera_mode,
        mode_label,
        seed_label,
        fps,
        coins=0,
        collectibles="0/0",
    ):
        y = 10
        x = 12

        def draw_text(text, y_pos, color=(230, 230, 255)):
            surf = self.font.render(text, True, color)
            surface.blit(surf, (x, y_pos))
            return y_pos + 20

        y = draw_text(f"Mode: {mode_label}", y)
        if seed_label:
            y = draw_text(seed_label, y)
        y = draw_text(f"FPS: {fps:.0f}", y)
        y = draw_text(f"Camera: {camera_mode}", y)
        y = draw_text(f"Pos: ({player_state.physics.x:.0f}, {player_state.physics.y:.0f})", y)
        y = draw_text(f"Vel: ({player_state.physics.vx:.1f}, {player_state.physics.vy:.1f})", y)

        # Pickups display
        y += 6
        y = draw_text(f"Coins: {coins}", y, color=(255, 215, 0))  # Gold
        y = draw_text(f"Collectibles: {collectibles}", y, color=(0, 255, 255))  # Cyan

        y += 6
        # Health display - hearts or bar
        if self.use_hearts:
            import time

            self.draw_hearts(
                surface,
                player_state.health_state.current_hp,
                player_state.health_state.max_hp,
                x,
                y,
                time.time(),
            )
            y += 30
        else:
            self.draw_bar(
                surface,
                "Health",
                player_state.health_state.current_hp,
                player_state.health_state.max_hp,
                x,
                y,
                180,
                12,
                (120, 220, 120),
            )
            y += 24
        stamina = getattr(player_state, "stamina", 0.0)
        stamina_max = getattr(player_state, "stamina_max", 3.0)
        self.draw_bar(surface, "Stamina", stamina, stamina_max, x, y, 180, 12, (120, 180, 255))
        y += 24
        mana = getattr(player_state, "mana", 0.0)
        mana_max = getattr(player_state, "mana_max", 0.0)
        if mana_max > 0:
            self.draw_bar(
                surface,
                "Mana",
                mana,
                mana_max,
                x,
                y,
                180,
                12,
                (100, 180, 255),
                bg_color=(30, 40, 60),
            )
            y += 24
        dash_cd = getattr(player_state, "dash_cooldown", 0.0)
        dash_max = getattr(player_state, "dash_cooldown_max", 0.45)
        remaining = min(dash_max, dash_cd) if dash_cd > 0 else 0.0
        self.draw_bar(
            surface,
            "Dash CD",
            dash_max - remaining,
            dash_max,
            x,
            y,
            180,
            12,
            (255, 140, 255),
            bg_color=(60, 40, 70),
        )
        y += 24
        # Teleport / Ninjutsu cooldowns and shuriken ammo
        tp_cd = getattr(player_state, "teleport_cooldown", 0.0)
        tp_max = 3.0
        self.draw_bar(
            surface,
            "Teleport CD",
            tp_max - min(tp_max, tp_cd),
            tp_max,
            x,
            y,
            180,
            12,
            (140, 220, 255),
            bg_color=(40, 50, 70),
        )
        y += 24
        ninjutsu_cd = 0.0
        ninjutsu_dict = getattr(player_state, "ninjutsu_cooldowns", {})
        if isinstance(ninjutsu_dict, dict):
            ninjutsu_cd = ninjutsu_dict.get("purify", 0.0)
        self.draw_bar(
            surface,
            "Ninjutsu CD",
            max(0.0, 12.0 - min(12.0, ninjutsu_cd)),
            12.0,
            x,
            y,
            180,
            12,
            (255, 200, 120),
            bg_color=(50, 40, 30),
        )
        y += 24
        ammo_text = self.small.render(
            f"Shuriken: {getattr(player_state, 'shuriken_ammo', 0)}/{getattr(player_state, 'shuriken_max', 0)}",
            True,
            (230, 230, 240),
        )
        surface.blit(ammo_text, (x, y))
        y += 24
        y = draw_text(f"Ground: {player_state.physics.on_ground}", y)
        y = draw_text(
            f"Wall: {player_state.physics.on_wall} dir={player_state.physics.wall_dir}", y
        )
        y = draw_text(f"Facing: {'R' if player_state.facing >= 0 else 'L'}", y)

    def draw_compass_indicators(
        self,
        surface,
        player_pos: tuple[float, float],
        nearest_coin_pos: tuple[float, float] | None,
        exit_pos: tuple[float, float] | None,
        current_room_type: str | None = None,
        portal_targets: list[tuple[str, tuple[float, float], tuple[int, int, int]]] | None = None,
    ):
        """
        Draw compass-style indicators for nearest coin and exit direction.

        Args:
            surface: Surface to draw on
            player_pos: (x, y) player center position
            nearest_coin_pos: (x, y) nearest coin position (or None)
            exit_pos: (x, y) exit position (or None)
            current_room_type: Current room type for display
        """
        screen_w = surface.get_width()
        screen_h = surface.get_height()

        portal_targets = portal_targets or []

        # Draw indicators in top-right corner
        indicator_x = screen_w - 240
        indicator_y = 20

        # Background panel
        indicator_lines = 0
        if current_room_type:
            indicator_lines += 1
        if nearest_coin_pos:
            indicator_lines += 1
        if exit_pos:
            indicator_lines += 1
        indicator_lines += len(portal_targets)

        panel_w = 220
        panel_h = max(80, 50 + indicator_lines * 24)
        pygame.draw.rect(
            surface,
            (20, 20, 30, 200),
            pygame.Rect(indicator_x - 10, indicator_y - 10, panel_w, panel_h),
            border_radius=8,
        )
        pygame.draw.rect(
            surface,
            (80, 80, 100),
            pygame.Rect(indicator_x - 10, indicator_y - 10, panel_w, panel_h),
            width=2,
            border_radius=8,
        )

        # Title
        title_surf = self.small.render("Navigation", True, (200, 200, 220))
        surface.blit(title_surf, (indicator_x, indicator_y))
        indicator_y += 22

        # Current room type (if available)
        if current_room_type:
            room_color = self._get_room_type_color(current_room_type)
            room_surf = self.small.render(f"Room: {current_room_type.title()}", True, room_color)
            surface.blit(room_surf, (indicator_x, indicator_y))
            indicator_y += 20

        # Nearest coin indicator
        if nearest_coin_pos:
            self._draw_direction_indicator(
                surface,
                player_pos,
                nearest_coin_pos,
                indicator_x,
                indicator_y,
                "Coin",
                (255, 215, 0),
            )
            indicator_y += 24

        # Exit indicator
        if exit_pos:
            self._draw_direction_indicator(
                surface, player_pos, exit_pos, indicator_x, indicator_y, "Exit", (80, 255, 80)
            )
            indicator_y += 24

        # Hub portal indicators
        for label, target_pos, color in portal_targets:
            self._draw_direction_indicator(
                surface, player_pos, target_pos, indicator_x, indicator_y, label, color
            )
            indicator_y += 24

    def _draw_direction_indicator(
        self,
        surface,
        player_pos: tuple[float, float],
        target_pos: tuple[float, float],
        x: int,
        y: int,
        label: str,
        color: tuple[int, int, int],
    ):
        """Draw a single direction indicator with arrow and distance"""
        px, py = player_pos
        tx, ty = target_pos

        # Calculate direction
        dx = tx - px
        dy = ty - py
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < 1:
            return

        # Normalize direction
        dx /= distance
        dy /= distance

        # Draw arrow
        arrow_x = x + 12
        arrow_y = y + 8
        arrow_len = 10

        # Arrow endpoint
        end_x = arrow_x + dx * arrow_len
        end_y = arrow_y + dy * arrow_len

        # Draw arrow line
        pygame.draw.line(surface, color, (arrow_x, arrow_y), (end_x, end_y), 2)

        # Draw arrowhead
        angle = math.atan2(dy, dx)
        head_size = 4
        left_angle = angle + math.pi * 0.75
        right_angle = angle - math.pi * 0.75

        left_x = end_x + math.cos(left_angle) * head_size
        left_y = end_y + math.sin(left_angle) * head_size
        right_x = end_x + math.cos(right_angle) * head_size
        right_y = end_y + math.sin(right_angle) * head_size

        pygame.draw.polygon(surface, color, [(end_x, end_y), (left_x, left_y), (right_x, right_y)])

        # Draw label and distance
        distance_pixels = int(distance)
        distance_tiles = distance_pixels // 32

        if distance_tiles < 10:
            dist_str = f"{distance_tiles}t"
        elif distance_tiles < 100:
            dist_str = f"{distance_tiles}t"
        else:
            dist_str = f"{distance_tiles // 10 * 10}t"

        text_surf = self.small.render(f"{label}: {dist_str}", True, color)
        surface.blit(text_surf, (x + 30, y))

    def _get_room_type_color(self, room_type: str) -> tuple[int, int, int]:
        """Get color for room type"""
        colors = {
            "start": (120, 255, 120),
            "exit": (80, 255, 80),
            "shop": (255, 215, 0),
            "treasure": (255, 215, 0),
            "combat": (255, 100, 100),
            "boss": (255, 50, 50),
            "platform": (150, 150, 255),
        }
        return colors.get(room_type, (200, 200, 220))
