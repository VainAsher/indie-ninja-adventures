"""
Loot Notification System - Displays item pickups

Shows notifications when loot is dropped or collected.
Notifications appear in bottom-left corner and auto-dismiss.

Version: v0.6.0 (Phase 6)
"""

import time
from dataclasses import dataclass

import pygame

# ============================================================
# Loot Notification Data
# ============================================================


@dataclass
class LootNotification:
    """Individual loot notification"""

    item_id: str
    item_name: str
    quantity: int
    notification_type: str  # "item", "currency", "special"
    timestamp: float  # Time when notification was created
    duration: float = 3.0  # How long to display (seconds)
    fade_duration: float = 0.5  # Fade out duration (seconds)

    def is_expired(self, current_time: float) -> bool:
        """Check if notification should be removed"""
        return (current_time - self.timestamp) > self.duration

    def get_alpha(self, current_time: float) -> int:
        """Get alpha value for fade effect"""
        elapsed = current_time - self.timestamp

        # Fade in (first 0.2 seconds)
        if elapsed < 0.2:
            return int((elapsed / 0.2) * 255)

        # Fully visible
        if elapsed < (self.duration - self.fade_duration):
            return 255

        # Fade out
        fade_progress = (elapsed - (self.duration - self.fade_duration)) / self.fade_duration
        return int((1.0 - fade_progress) * 255)


# ============================================================
# Loot Notification Manager
# ============================================================


class LootNotificationManager:
    """
    Manages loot notifications.

    Features:
    - Auto-dismiss after duration
    - Stacked vertical display
    - Fade in/out effects
    - Different styles for items vs currency
    """

    def __init__(self, font_name: str = "consolas", font_size: int = 16):
        """
        Initialize loot notification manager.

        Args:
            font_name: Font name
            font_size: Font size
        """
        self.font = pygame.font.SysFont(font_name, font_size, bold=True)
        self.notifications: list[LootNotification] = []

        # Colors
        self.color_item = (150, 200, 255)  # Light blue
        self.color_currency = (255, 215, 0)  # Gold
        self.color_special = (255, 100, 255)  # Purple
        self.color_bg = (20, 20, 30)
        self.color_border = (80, 80, 100)

        # Display settings
        self.notification_height = 32
        self.notification_spacing = 8
        self.max_notifications = 5  # Maximum displayed at once

    def add_notification(
        self,
        item_id: str,
        item_name: str,
        quantity: int = 1,
        notification_type: str = "item",
        duration: float = 3.0,
    ):
        """
        Add a loot notification.

        Args:
            item_id: Item ID
            item_name: Display name
            quantity: Quantity picked up
            notification_type: "item", "currency", or "special"
            duration: Display duration in seconds
        """
        notification = LootNotification(
            item_id=item_id,
            item_name=item_name,
            quantity=quantity,
            notification_type=notification_type,
            timestamp=time.time(),
            duration=duration,
        )

        self.notifications.append(notification)

        # Limit to max notifications
        if len(self.notifications) > self.max_notifications:
            self.notifications = self.notifications[-self.max_notifications :]

    def add_item_pickup(self, item_id: str, item_name: str, quantity: int = 1):
        """Add item pickup notification"""
        self.add_notification(item_id, item_name, quantity, "item")

    def add_currency_pickup(self, amount: int, currency_name: str = "Gold"):
        """Add currency pickup notification"""
        self.add_notification("currency", currency_name, amount, "currency")

    def add_special_pickup(self, item_name: str):
        """Add special item pickup notification (keys, quest items)"""
        self.add_notification("special", item_name, 1, "special")

    def update(self, dt: float):
        """
        Update notifications (remove expired).

        Args:
            dt: Delta time (unused, uses wall clock time)
        """
        current_time = time.time()

        # Remove expired notifications
        self.notifications = [
            notif for notif in self.notifications if not notif.is_expired(current_time)
        ]

    def draw(self, surface: pygame.Surface):
        """
        Draw all notifications.

        Args:
            surface: Surface to draw on
        """
        if not self.notifications:
            return

        current_time = time.time()
        screen_h = surface.get_height()

        # Starting position (bottom-left corner)
        x = 20
        y = screen_h - 20

        # Draw notifications from bottom to top
        for notif in reversed(self.notifications):
            alpha = notif.get_alpha(current_time)
            if alpha > 0:
                self._draw_notification(surface, notif, x, y, alpha)
                y -= self.notification_height + self.notification_spacing

    def _draw_notification(
        self, surface: pygame.Surface, notification: LootNotification, x: int, y: int, alpha: int
    ):
        """Draw a single notification"""
        # Choose color based on type
        if notification.notification_type == "currency":
            text_color = self.color_currency
        elif notification.notification_type == "special":
            text_color = self.color_special
        else:
            text_color = self.color_item

        # Build notification text
        prefix = "[+]"
        if notification.quantity > 1:
            text = f"{prefix} {notification.item_name} x{notification.quantity}"
        else:
            text = f"{prefix} {notification.item_name}"

        # Render text
        text_surf = self.font.render(text, True, text_color)
        text_surf.set_alpha(alpha)

        # Calculate dimensions
        text_w = text_surf.get_width()
        text_h = text_surf.get_height()
        padding = 10
        bg_w = text_w + padding * 2
        bg_h = text_h + padding

        # Draw background
        bg_y = y - bg_h
        bg_surf = pygame.Surface((bg_w, bg_h))
        bg_surf.set_alpha(min(200, alpha))
        bg_surf.fill(self.color_bg)
        surface.blit(bg_surf, (x, bg_y))

        # Draw border
        border_rect = pygame.Rect(x, bg_y, bg_w, bg_h)
        border_surf = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (*text_color, alpha), border_rect, width=2, border_radius=6)
        surface.blit(border_surf, (x, bg_y))

        # Draw text
        surface.blit(text_surf, (x + padding, bg_y + padding // 2))

    def clear(self):
        """Clear all notifications"""
        self.notifications.clear()

    def get_notification_count(self) -> int:
        """Get number of active notifications"""
        return len(self.notifications)


# ============================================================
# Helper Functions
# ============================================================


def create_loot_manager() -> LootNotificationManager:
    """Create a loot notification manager"""
    return LootNotificationManager()
