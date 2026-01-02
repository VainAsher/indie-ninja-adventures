"""
Physics Constants - Single Source of Truth

All physics-related constants for Vain Asher Gaming's: Indie Ninja Adventures.
Centralized to ensure consistency across PhysicsSystem and all mechanics.

IMPORTANT: Do NOT duplicate these constants elsewhere. Import from this file.
"""

# ============================================================================
# GRAVITY & FALLING
# ============================================================================

# Base gravity acceleration (pixels per tick per tick)
# Increased from 0.4 to 0.6 for snappier, less floaty jump feel
GRAVITY = 0.6

# Gravity multipliers for different fall states
FALL_GRAVITY_MULT = 2.0  # Falling is faster than rising (increased from 1.5 for snappier descent)
FAST_FALL_MULT = 2.0  # Holding down while falling
JUMP_CUT_MULT = 3.0  # When jump button released mid-jump

# Apex hang time - reduces gravity when near peak of jump for satisfying floaty moment
APEX_HANG_THRESHOLD = 1.0  # When |vy| < this value, apply apex hang
APEX_HANG_MULT = 0.6  # Gravity multiplier at apex (60% gravity for brief hang)

# Maximum fall speed (terminal velocity)
MAX_FALL_SPEED = 12.0

# ============================================================================
# MOVEMENT
# ============================================================================

# Ground movement
MAX_RUN_SPEED = 8.0  # Maximum horizontal speed
MOVEMENT_ACCEL = 1200.0  # Movement acceleration (reduced from 2600 for more weight/momentum feel)
# smooth_factor = accel * dt / speed = 1200 * 0.0167 / 8 = 0.25 per tick
# This gives responsive but weighted acceleration (reaches 75% speed in ~5 ticks)
GROUND_FRICTION = 0.8  # Deceleration multiplier

# Air movement
AIR_ACCEL_MULT = 0.65  # Air control (65% of ground accel)
AIR_FRICTION = 0.95  # Less friction in air

# ============================================================================
# JUMPING
# ============================================================================

# Jump power values
JUMP_POWER = 14.5  # Ground jump initial velocity
DOUBLE_JUMP_POWER = 14.5  # Double jump (same as ground)
WALL_JUMP_POWER_X = 8.5  # Horizontal component of wall jump
WALL_JUMP_POWER_Y = 14.5  # Vertical component of wall jump

# Jump timing
COYOTE_TIME = 0.12  # Seconds after leaving ground can still jump
JUMP_BUFFER_TIME = 0.14  # Seconds jump input is remembered

# Jump modifiers
CROUCH_JUMP_MULT = 0.7  # Crouch reduces jump height to 70%

# ============================================================================
# DASH
# ============================================================================

DASH_SPEED = 16.0  # Dash horizontal speed
DASH_DURATION = 0.16  # Dash lasts 160ms
DASH_COOLDOWN = 0.45  # 450ms between dashes

# ============================================================================
# CROUCH
# ============================================================================

CROUCH_SPEED_MULT = 0.6  # Movement speed while crouching (60%)
CROUCH_ACCEL_MULT = 0.8  # Acceleration while crouching (80%)
CROUCH_HEIGHT_RATIO = 0.5  # Collision box height (50% of normal)

# ============================================================================
# WALL SLIDE
# ============================================================================

WALL_SLIDE_SPEED = 3.0  # Slide down speed (capped)
WALL_SLIDE_FRICTION = 0.7  # Velocity damping near walls
WALL_FRICTION_CLAMP = 5.0  # Max fall speed near walls

# Wall slide stamina
MAX_WALL_STAMINA = 3.0  # Max seconds of wall cling
STAMINA_REGEN_RATE = 2.0  # Seconds to regen from 0 to max
EXHAUST_THRESHOLD = 0.1  # Below this, can't wall slide
EXHAUST_PENALTY = 0.5  # Stamina lost on detach

# ============================================================================
# COLLISION
# ============================================================================

# Swept collision threshold
SWEPT_COLLISION_THRESHOLD = 8.0  # Activate swept collision above this speed

# Platform collision
PLATFORM_GRACE_PIXELS = 4  # Pixels below platform where collision still works

# Corner collision thresholds (for smoothing)
CORNER_MIN_OVERLAP = 4  # Minimum overlap to trigger corner smoothing
CORNER_MAX_OVERLAP = 14  # Maximum overlap for corner smoothing

# ============================================================================
# PLAYER DIMENSIONS
# ============================================================================

PLAYER_WIDTH = 28  # Player collision box width (pixels)
PLAYER_HEIGHT = 56  # Player collision box height (pixels)
PLAYER_CROUCH_HEIGHT = 28  # Player height while crouching

# ============================================================================
# WORLD / TILES
# ============================================================================

TILE_SIZE = 32  # Tile size in pixels
TILES_PER_ZONE = 8  # Each zone = 8×8 tiles (smaller rooms to reduce load)
ROOM_WIDTH_TILES = 128  # Room width in tiles (16 zones × 8)
ROOM_HEIGHT_TILES = 128  # Room height in tiles

# ============================================================================
# GAME CLOCK
# ============================================================================

TARGET_FPS = 60  # Physics tick rate
FIXED_DT = 1.0 / 60.0  # Fixed timestep (16.67ms)
MAX_FRAME_TIME = 0.25  # Spiral of death prevention

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def pixels_to_tiles(pixels: float) -> int:
    """Convert pixel coordinate to tile coordinate."""
    return int(pixels // TILE_SIZE)


def tiles_to_pixels(tiles: int) -> float:
    """Convert tile coordinate to pixel coordinate (center)."""
    return tiles * TILE_SIZE + TILE_SIZE / 2


def zones_to_tiles(zone_coord: int) -> int:
    """Convert zone coordinate to tile coordinate."""
    return zone_coord * TILES_PER_ZONE


def tiles_to_zones(tile_coord: int) -> int:
    """Convert tile coordinate to zone coordinate."""
    return tile_coord // TILES_PER_ZONE
