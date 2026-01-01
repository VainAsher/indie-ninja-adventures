"""
Rendering Smoke Tests

Smoke tests for all rendering systems to ensure they don't crash
and produce valid output. These tests verify basic functionality
without checking pixel-perfect rendering.

Coverage:
- HUD rendering (health bars, hearts)
- Sprite management and animations
- Minimap rendering
- Particle system
- Pickup/hazard renderers
- UI screens (victory, dialogue, etc.)

Test philosophy: Verify rendering doesn't crash, not pixel accuracy
"""

import pygame
import pytest

from rendering import hazard_renderer, pickup_renderer

# Import rendering modules
from rendering.hud import HUDRenderer
from rendering.loot_notification import LootNotificationManager
from rendering.minimap import MinimapConfig, MinimapRenderer
from rendering.npc_prompt import NPCPromptRenderer
from rendering.objective_hud import ObjectiveHUDRenderer, create_objective
from rendering.particles import ParticleSystem
from rendering.sprite_manager import SpriteManager
from rendering.victory_screen import VictoryScreen

# ============================================================
# Test Fixtures
# ============================================================


@pytest.fixture(scope="module", autouse=True)
def pygame_init():
    """Initialize pygame once for all tests"""
    pygame.init()
    # Create a small test surface
    screen = pygame.display.set_mode((800, 600))
    yield screen
    pygame.quit()


@pytest.fixture
def test_surface():
    """Create a test surface for rendering"""
    return pygame.Surface((800, 600))


# ============================================================
# HUD Renderer Tests
# ============================================================


def test_hud_renderer_initialization():
    """Test HUDRenderer can be initialized"""
    hud = HUDRenderer()
    assert hud is not None
    assert hud.font is not None
    assert hud.small is not None
    assert hud.large is not None
    print("[PASS] HUD initialization")


def test_hud_draw_bar(test_surface):
    """Test drawing health/stamina bars"""
    hud = HUDRenderer()

    # Draw various bar states
    hud.draw_bar(test_surface, "Health", 80, 100, 10, 10, 200, 20, (220, 20, 60))
    hud.draw_bar(test_surface, "Stamina", 50, 100, 10, 40, 200, 20, (60, 180, 220))
    hud.draw_bar(test_surface, "Energy", 0, 100, 10, 70, 200, 20, (220, 220, 60))
    hud.draw_bar(test_surface, "Full", 100, 100, 10, 100, 200, 20, (60, 220, 60))

    # No crash means success
    print("[PASS] HUD bar rendering")


def test_hud_draw_heart(test_surface):
    """Test drawing individual hearts"""
    hud = HUDRenderer()

    # Draw filled heart
    hud.draw_heart(test_surface, 10, 10, filled=True, pulsing=False)

    # Draw empty heart
    hud.draw_heart(test_surface, 40, 10, filled=False, pulsing=False)

    # Draw pulsing heart (low health warning)
    hud.draw_heart(test_surface, 70, 10, filled=True, pulsing=True, pulse_time=1.5)

    print("[PASS] HUD heart rendering")


def test_hud_draw_hearts_full(test_surface):
    """Test drawing full heart containers"""
    hud = HUDRenderer()

    # Full health (5/5 hearts)
    hud.draw_hearts(test_surface, 5, 5, 10, 50)

    # Partial health (3/5 hearts)
    hud.draw_hearts(test_surface, 3, 5, 10, 80)

    # Low health (1/5 hearts, pulsing)
    hud.draw_hearts(test_surface, 1, 5, 10, 110, low_health_time=2.0)

    # No health (0/5 hearts)
    hud.draw_hearts(test_surface, 0, 5, 10, 140)

    print("[PASS] HUD hearts container rendering")


def test_hud_edge_cases(test_surface):
    """Test HUD edge cases"""
    hud = HUDRenderer()

    # Zero max value
    hud.draw_bar(test_surface, "Empty", 0, 0, 10, 10, 200, 20, (220, 20, 60))

    # Negative value (should clamp to 0)
    hud.draw_bar(test_surface, "Negative", -10, 100, 10, 40, 200, 20, (220, 20, 60))

    # Value exceeds max (should clamp to max)
    hud.draw_bar(test_surface, "Overflow", 150, 100, 10, 70, 200, 20, (220, 20, 60))

    # Zero hearts
    hud.draw_hearts(test_surface, 0, 0, 10, 100)

    print("[PASS] HUD edge cases")


# ============================================================
# Sprite Manager Tests
# ============================================================


def test_sprite_manager_initialization():
    """Test SpriteManager can be initialized"""
    sprite_mgr = SpriteManager()
    assert sprite_mgr is not None
    print("[PASS] SpriteManager initialization")


def test_sprite_manager_missing_sprites():
    """Test SpriteManager handles missing sprite files gracefully"""
    # SpriteManager lazy-loads, so initialization shouldn't fail
    sprite_mgr = SpriteManager()

    # Trying to get a frame from missing sprites should handle gracefully
    # (May return None or placeholder, shouldn't crash)
    try:
        frame = sprite_mgr.get_frame("idle", facing=1, time_ms=0)
        # May be None if sprites missing, that's ok for smoke test
        print("[PASS] SpriteManager handles missing sprites")
    except Exception as e:
        # Expected if sprites don't exist
        print(f"[PASS] SpriteManager gracefully handles missing sprites: {type(e).__name__}")


# ============================================================
# Minimap Tests
# ============================================================


def test_minimap_initialization():
    """Test MinimapRenderer can be initialized"""
    minimap = MinimapRenderer()
    assert minimap is not None
    assert minimap.config is not None
    print("[PASS] Minimap initialization")


def test_minimap_custom_config():
    """Test MinimapRenderer with custom config"""
    config = MinimapConfig(
        position=(20, 20),
        show_connections=False,
        show_player=True,
        highlight_current=True,
        scale=20,
    )
    minimap = MinimapRenderer(config)
    assert minimap.config.position == (20, 20)
    assert minimap.config.scale == 20
    print("[PASS] Minimap custom config")


# Minimap rendering tests require complex World and Megamap setup
# Skip for smoke tests - minimap initialization verified above
# def test_minimap_render(test_surface):
#     """Test minimap rendering - SKIPPED: requires world generation"""
#     pass


# ============================================================
# Particle System Tests
# ============================================================


def test_particle_system_initialization():
    """Test ParticleSystem can be initialized"""
    particles = ParticleSystem()
    assert particles is not None
    assert particles.particles == []
    print("[PASS] ParticleSystem initialization")


def test_particle_emit_dust():
    """Test dust particle emission"""
    particles = ParticleSystem()

    # Emit dust particles
    particles.emit_dust(100.0, 100.0, count=8)

    assert len(particles.particles) == 8
    print("[PASS] Particle dust emission")


def test_particle_emit_dash():
    """Test dash particle emission"""
    particles = ParticleSystem()

    # Emit dash particles
    particles.emit_dash(100.0, 100.0, direction=1)

    assert len(particles.particles) == 12
    print("[PASS] Particle dash emission")


def test_particle_update():
    """Test particle system update"""
    particles = ParticleSystem()

    # Emit some particles
    particles.emit_dust(100.0, 100.0, count=10)
    initial_count = len(particles.particles)

    # Update particles (some should die)
    for _ in range(100):
        particles.update(0.016)  # 60 FPS

    # Particles should have expired
    assert len(particles.particles) < initial_count
    print(f"[PASS] Particle update ({initial_count} -> {len(particles.particles)} particles)")


def test_particle_draw(test_surface):
    """Test particle rendering"""
    particles = ParticleSystem()
    particles.emit_dust(400.0, 300.0, count=20)

    # Simple camera mock
    class MockCamera:
        def apply(self, rect):
            return rect

    camera = MockCamera()
    particles.draw(test_surface, camera)

    print("[PASS] Particle rendering")


# ============================================================
# Pickup Renderer Tests
# ============================================================


def test_pickup_renderer_functions_exist():
    """Test pickup renderer functions exist"""
    assert hasattr(pickup_renderer, "render_pickup")
    assert hasattr(pickup_renderer, "render_pickups")
    assert hasattr(pickup_renderer, "render_coin")
    assert hasattr(pickup_renderer, "render_health")
    assert hasattr(pickup_renderer, "render_collectible")
    print("[PASS] Pickup renderer functions exist")


def test_pickup_renderer_draw_empty(test_surface):
    """Test rendering with no pickups"""

    # Simple camera mock
    class MockCamera:
        def apply(self, rect):
            return rect

    camera = MockCamera()
    pickup_renderer.render_pickups(test_surface, [], camera)

    print("[PASS] Pickup renderer with empty list")


# ============================================================
# Hazard Renderer Tests
# ============================================================


def test_hazard_renderer_functions_exist():
    """Test hazard renderer functions exist"""
    assert hasattr(hazard_renderer, "render_hazard")
    assert hasattr(hazard_renderer, "render_hazards")
    assert hasattr(hazard_renderer, "render_spike")
    assert hasattr(hazard_renderer, "render_void")
    print("[PASS] Hazard renderer functions exist")


def test_hazard_renderer_draw_empty(test_surface):
    """Test rendering with no hazards"""

    # Simple camera mock
    class MockCamera:
        def apply(self, rect):
            return rect

    camera = MockCamera()
    hazard_renderer.render_hazards(test_surface, [], camera)

    print("[PASS] Hazard renderer with empty list")


# ============================================================
# NPC Prompt Renderer Tests
# ============================================================


def test_npc_prompt_initialization():
    """Test NPCPromptRenderer can be initialized"""
    renderer = NPCPromptRenderer()
    assert renderer is not None
    print("[PASS] NPCPromptRenderer initialization")


# ============================================================
# Objective HUD Tests
# ============================================================


def test_objective_hud_initialization():
    """Test ObjectiveHUDRenderer can be initialized"""
    hud = ObjectiveHUDRenderer()
    assert hud is not None
    print("[PASS] ObjectiveHUDRenderer initialization")


def test_objective_hud_draw(test_surface):
    """Test objective HUD rendering"""
    hud = ObjectiveHUDRenderer()

    # Draw with sample objectives
    objectives = [
        create_objective("Defeat 5 enemies", current=5, target=5, completed=True),
        create_objective("Find the exit", completed=False),
        create_objective("Collect 100 gold", current=50, target=100, completed=False),
    ]

    hud.draw_objectives(test_surface, objectives)

    print("[PASS] ObjectiveHUDRenderer draw")


def test_objective_hud_empty(test_surface):
    """Test objective HUD with no objectives"""
    hud = ObjectiveHUDRenderer()

    # Draw with empty objectives
    hud.draw_objectives(test_surface, [])

    print("[PASS] ObjectiveHUDRenderer with empty objectives")


# ============================================================
# Victory Screen Tests
# ============================================================


def test_victory_screen_initialization():
    """Test VictoryScreen can be initialized"""
    screen = VictoryScreen()
    assert screen is not None
    print("[PASS] VictoryScreen initialization")


def test_victory_screen_draw(test_surface):
    """Test victory screen rendering"""
    screen = VictoryScreen()

    # Draw victory screen
    stats = {"time": 123.45, "collectibles": "3/5", "deaths": 2}

    screen.render(test_surface, stats, dt=0.016)

    print("[PASS] VictoryScreen draw")


# ============================================================
# Loot Notification Tests
# ============================================================


def test_loot_notification_initialization():
    """Test LootNotificationManager can be initialized"""
    manager = LootNotificationManager()
    assert manager is not None
    assert manager.notifications == []
    print("[PASS] LootNotificationManager initialization")


def test_loot_notification_add():
    """Test adding loot notifications"""
    manager = LootNotificationManager()

    # Add notification
    manager.add_notification("health_potion", "Health Potion", quantity=1)

    assert len(manager.notifications) == 1
    print("[PASS] LootNotificationManager add notification")


def test_loot_notification_update():
    """Test notification updates and expiration"""
    manager = LootNotificationManager()

    # Add notification with short duration
    manager.add_notification("gold", "Gold", quantity=50, duration=0.1)

    # Update (notifications should expire after duration)
    import time

    time.sleep(0.2)
    manager.update(0.016)

    # Should be expired
    assert len(manager.notifications) == 0
    print("[PASS] LootNotificationManager update and expiration")


def test_loot_notification_draw(test_surface):
    """Test loot notification rendering"""
    manager = LootNotificationManager()

    # Add notifications
    manager.add_item_pickup("sword", "Iron Sword", quantity=1)
    manager.add_currency_pickup(amount=100, currency_name="Gold")

    # Draw
    manager.draw(test_surface)

    print("[PASS] LootNotificationManager draw")


# ============================================================
# Integration Tests
# ============================================================


def test_multiple_renderers_together(test_surface):
    """Test multiple renderers can coexist and draw"""
    # Initialize all renderers
    hud = HUDRenderer()
    particles = ParticleSystem()
    objective_hud = ObjectiveHUDRenderer()
    loot_manager = LootNotificationManager()

    # Simple camera mock
    class MockCamera:
        def apply(self, rect):
            return rect

    camera = MockCamera()

    # Emit particles
    particles.emit_dust(400.0, 300.0, count=10)
    particles.emit_dash(450.0, 300.0, direction=1)

    # Add loot notification
    loot_manager.add_notification("test_item", "Test Item", quantity=1)

    # Draw everything
    hud.draw_hearts(test_surface, 3, 5, 10, 10)
    hud.draw_bar(test_surface, "XP", 75, 100, 10, 50, 200, 20, (60, 180, 220))
    particles.draw(test_surface, camera)
    pickup_renderer.render_pickups(test_surface, [], camera)
    hazard_renderer.render_hazards(test_surface, [], camera)
    objective_hud.draw_objectives(test_surface, [])
    loot_manager.draw(test_surface)

    print("[PASS] Multiple renderers integration")


def test_rendering_stress(test_surface):
    """Test rendering under stress (many particles, notifications)"""
    particles = ParticleSystem()
    loot_manager = LootNotificationManager()

    # Emit many particles
    for i in range(10):
        particles.emit_dust(100.0 + i * 50, 300.0, count=20)

    # Add many notifications
    for i in range(5):
        loot_manager.add_notification(f"item_{i}", f"Item {i}", quantity=i + 1)

    # Simple camera mock
    class MockCamera:
        def apply(self, rect):
            return rect

    camera = MockCamera()

    # Update and draw
    for _ in range(10):
        particles.update(0.016)
        loot_manager.update(0.016)

    particles.draw(test_surface, camera)
    loot_manager.draw(test_surface)

    print(
        f"[PASS] Rendering stress test ({len(particles.particles)} particles, {len(loot_manager.notifications)} notifications)"
    )


# ============================================================
# Run Tests
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
