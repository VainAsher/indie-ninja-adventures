"""
Collision System - Entity collision detection and resolution

Features:
- AABB collision detection
- Collision resolution (penetration correction)
- Collision events for all entities
- Separation of detection and response
- Works with entity system
"""

import logging

import pygame

from core.entity_system import Entity, EntityManager
from core.event_bus import CollisionEvent, EventBus, TickEvent
from core.state import PhysicsState


class CollisionSystem:
    """
    Handles collision detection and resolution for all entities

    Features:
    - Detects collisions between entities and tiles
    - Resolves penetration (moves entities out of collision)
    - Emits CollisionEvent for each collision
    - Updates collision flags (on_ground, on_wall, wall_dir)
    - Runs after movement in physics pipeline
    """

    def __init__(
        self,
        event_bus: EventBus,
        entity_manager: EntityManager,
        logger: logging.Logger | None = None,
    ):
        self.event_bus = event_bus
        self.entity_manager = entity_manager
        self.logger = logger
        self.profiler = None  # Set externally to enable per-section timing
        self.chunk_size = 320  # spatial hash chunk size in pixels
        self.tile_lookup: dict[tuple, list] = {}
        self.platform_lookup: dict[tuple, list] = {}

        # Level tiles (collision rects)
        self.tiles: list[pygame.Rect] = []
        self.platforms: list[pygame.Rect] = []  # One-way platforms (collision from top only)

        # Subscribe to tick events
        # Priority 55 runs BEFORE Player.on_tick (50) so collision state is current, not stale
        self.event_bus.subscribe(TickEvent, self.on_tick, priority=55)

        if self.logger:
            self.logger.info("CollisionSystem initialized")

    def set_tiles(self, tiles: list[pygame.Rect], platforms: list[pygame.Rect] | None = None):
        """
        Set tile collision rects for current level

        Args:
            tiles: List of pygame.Rect for solid tiles (full collision)
            platforms: List of pygame.Rect for platform tiles (one-way collision from top)
        """
        self.tiles = tiles
        self.platforms = platforms if platforms is not None else []
        # Build spatial hash for faster lookups
        self.tile_lookup.clear()
        self.platform_lookup.clear()
        for t in self.tiles:
            key = (t.x // self.chunk_size, t.y // self.chunk_size)
            self.tile_lookup.setdefault(key, []).append(t)
        for p in self.platforms:
            key = (p.x // self.chunk_size, p.y // self.chunk_size)
            self.platform_lookup.setdefault(key, []).append(p)
        if self.logger:
            self.logger.info(f"Loaded {len(tiles)} tile colliders, {len(self.platforms)} platforms")

    def update_platforms(self, platforms: list[pygame.Rect]):
        """
        Update platform colliders without rebuilding solid tile lookup.

        Args:
            platforms: List of pygame.Rect for platform tiles (one-way collision from top)
        """
        self.platforms = platforms
        self.platform_lookup.clear()
        for p in self.platforms:
            key = (p.x // self.chunk_size, p.y // self.chunk_size)
            self.platform_lookup.setdefault(key, []).append(p)

    def on_tick(self, event: TickEvent):
        """
        Process collisions every physics tick

        Called after entity movement but before mechanics respond.
        """
        if self.profiler:
            self.profiler.begin("collision")

        # Check collisions for all entities with physics
        for entity in self.entity_manager.entities.values():
            if entity.physics and entity.active:
                self.check_and_resolve(entity)

        if self.profiler:
            self.profiler.end("collision")

    def check_and_resolve(self, entity: Entity) -> list[CollisionEvent]:
        """
        Check collisions and resolve penetration for an entity

        Uses swept collision detection for high-speed movement to prevent tunneling.

        Args:
            entity: Entity to check collisions for

        Returns:
            List of collision events emitted
        """
        if not entity.physics:
            return []

        events = []

        # For high-speed movement, use swept collision detection
        # to prevent tunneling through tiles
        physics = entity.physics
        use_swept_vertical = abs(physics.vy) > 8.0
        use_swept_horizontal = abs(physics.vx) > 8.0

        if use_swept_vertical:
            events.extend(self._swept_vertical_collision(entity))
        else:
            # Normal collision for low speeds
            events.extend(self._check_vertical_collisions(entity))

        # Horizontal collisions - use swept for high speeds (dash = 16.0)
        if use_swept_horizontal:
            events.extend(self._swept_horizontal_collision(entity))
        else:
            events.extend(self._check_horizontal_collisions(entity))

        # If we're on a wall but lack support below, clear ground flag to avoid false grounded state.
        # Keep current vertical velocity to allow descent; do not zero vy here.
        if physics.on_wall and not self._has_support_below(physics):
            physics.on_ground = False

        # Predictive snap: if very close to support below after all resolution, snap down and ground
        if not physics.on_ground and physics.vy >= -0.1:
            self._snap_to_ground(physics)

        return events

    def _check_horizontal_collisions(self, entity: Entity) -> list[CollisionEvent]:
        """
        Check and resolve horizontal (X-axis) collisions

        Args:
            entity: Entity to check

        Returns:
            List of collision events
        """
        events = []
        physics = entity.physics
        entity_rect = physics.get_rect()
        candidate_tiles = self._get_candidate_tiles(entity_rect, self.tiles)

        # Reset wall flags
        physics.on_wall = False
        physics.wall_dir = 0

        for tile in candidate_tiles:
            if entity_rect.colliderect(tile):
                # Determine if this is a horizontal or vertical collision
                # Calculate overlaps in both directions
                overlap_x = min(entity_rect.right, tile.right) - max(entity_rect.left, tile.left)
                overlap_y = min(entity_rect.bottom, tile.bottom) - max(entity_rect.top, tile.top)

                # If overlap_x is much smaller than overlap_y, this is a horizontal collision (side hit)
                # If overlap_y is much smaller than overlap_x, this is a vertical collision (ground/ceiling)
                #
                # However, if the player is falling (vy > 0) and hitting a corner,
                # treat it as vertical to avoid jitter when landing on platform edges
                is_horizontal_collision = overlap_x < overlap_y

                # Special case for falling corner collisions:
                # If falling AND both overlaps are small AND close in value,
                # prefer vertical collision. This prevents jitter when landing on corners.
                # Adjusted thresholds for 32x32 tiles with 28x56 player (width x height)
                # Player width is 28px, so overlap_x should be small for corners
                # Player height is 56px, but we only check when BOTH overlaps are small
                # IMPORTANT: Only apply this when moving primarily downward (vy > vx)
                # to prevent wall climbing when walking into walls horizontally
                if (
                    physics.vy > 0
                    and abs(physics.vy)
                    > abs(physics.vx) * 1.5  # Must be falling faster than moving sideways
                    and overlap_x >= 4
                    and overlap_x <= 14  # Horizontal overlap (based on width)
                    and overlap_y >= 4
                    and overlap_y <= 14  # Vertical overlap must ALSO be small
                    and abs(overlap_x - overlap_y) <= 8
                ):  # And they must be close in value
                    is_horizontal_collision = False

                # Only process horizontal collision here
                # Also verify we're actually moving horizontally to prevent false positives
                if is_horizontal_collision and abs(physics.vx) > 0.1:
                    if physics.vx > 0:  # Moving right
                        # Push entity left
                        entity_rect.right = tile.left
                        physics.x = float(entity_rect.x)
                        physics.vx = min(physics.vx, 0.0)
                        physics.on_wall = True
                        physics.wall_dir = 1

                        # Emit collision event
                        event = CollisionEvent(
                            entity_id=entity.entity_id,
                            collision_type="wall_right",
                            normal=(-1, 0),
                            tile_rect=tile,
                        )
                        events.append(event)
                        self.event_bus.emit(event)

                        if self.logger:
                            self.logger.debug(
                                f"Entity {entity.entity_id} ({entity.entity_type.value}) "
                                f"hit wall on right"
                            )

                    elif physics.vx < 0:  # Moving left
                        # Push entity right
                        entity_rect.left = tile.right
                        physics.x = float(entity_rect.x)
                        physics.vx = max(physics.vx, 0.0)
                        physics.on_wall = True
                        physics.wall_dir = -1

                        # Emit collision event
                        event = CollisionEvent(
                            entity_id=entity.entity_id,
                            collision_type="wall_left",
                            normal=(1, 0),
                            tile_rect=tile,
                        )
                        events.append(event)
                        self.event_bus.emit(event)

                        if self.logger:
                            self.logger.debug(
                                f"Entity {entity.entity_id} ({entity.entity_type.value}) "
                                f"hit wall on left"
                            )

        return events

    def _has_support_below(self, physics: PhysicsState, tolerance: float = 2.0) -> bool:
        """
        Check if there is a solid/platform surface directly below within a small tolerance.
        """
        entity_rect = pygame.Rect(int(physics.x), int(physics.y), physics.width, physics.height)
        for tile in self._get_candidate_tiles(entity_rect, self.tiles):
            if entity_rect.right > tile.left and entity_rect.left < tile.right:
                gap = tile.top - entity_rect.bottom
                if 0 <= gap <= tolerance:
                    return True
        for platform in self._get_candidate_tiles(entity_rect, self.platforms, platforms=True):
            if entity_rect.right > platform.left and entity_rect.left < platform.right:
                gap = platform.top - entity_rect.bottom
                if 0 <= gap <= tolerance:
                    return True
        return False

    def _snap_to_ground(self, physics: PhysicsState, tolerance: float = 3.0) -> None:
        """
        Small predictive snap to ground/platform when very close, to prevent floating gaps.
        """
        entity_rect = pygame.Rect(int(physics.x), int(physics.y), physics.width, physics.height)
        required_overlap_x = max(6, int(physics.width * 0.5))

        for tile in self._get_candidate_tiles(entity_rect, self.tiles):
            if entity_rect.right > tile.left and entity_rect.left < tile.right:
                horizontal_overlap = min(entity_rect.right, tile.right) - max(
                    entity_rect.left, tile.left
                )
                if horizontal_overlap < required_overlap_x:
                    continue
                gap = tile.top - entity_rect.bottom
                if 0 <= gap <= tolerance:
                    entity_rect.bottom = tile.top
                    physics.y = float(entity_rect.y)
                    physics.vy = 0.0
                    physics.on_ground = True
                    return

        for platform in self._get_candidate_tiles(entity_rect, self.platforms, platforms=True):
            if entity_rect.right > platform.left and entity_rect.left < platform.right:
                horizontal_overlap = min(entity_rect.right, platform.right) - max(
                    entity_rect.left, platform.left
                )
                if horizontal_overlap < required_overlap_x:
                    continue
                gap = platform.top - entity_rect.bottom
                if 0 <= gap <= tolerance:
                    entity_rect.bottom = platform.top
                    physics.y = float(entity_rect.y)
                    physics.vy = 0.0
                    physics.on_ground = True
                    return

    def _check_vertical_collisions(self, entity: Entity) -> list[CollisionEvent]:
        """
        Check and resolve vertical (Y-axis) collisions

        Args:
            entity: Entity to check

        Returns:
            List of collision events
        """
        events = []
        physics = entity.physics
        # Use x before horizontal movement was applied this frame so that wall
        # tiles the player is pressing into are not misread as ceiling tiles.
        check_x = physics.x - physics.vx
        entity_rect = pygame.Rect(int(check_x), int(physics.y), physics.width, physics.height)
        candidate_tiles = self._get_candidate_tiles(entity_rect, self.tiles)

        # Reset ground flag, but remember previous state for stickiness
        old_on_ground = physics.on_ground
        physics.on_ground = False

        for tile in candidate_tiles:
            if entity_rect.colliderect(tile):
                # Calculate overlaps in both directions
                overlap_x = min(entity_rect.right, tile.right) - max(entity_rect.left, tile.left)
                overlap_y = min(entity_rect.bottom, tile.bottom) - max(entity_rect.top, tile.top)

                # Check if entity is on ground (landing from above)
                # Must have MORE vertical overlap than horizontal (landing on top, not side hit)
                # AND entity's feet must be near the tile's top
                feet_overlap = entity_rect.bottom - tile.top
                required_overlap_x = max(
                    6, int(physics.width * 0.5)
                )  # need meaningful horizontal coverage
                is_landing_on_top = (
                    feet_overlap > 0
                    and feet_overlap <= 22  # Feet within ~20px of tile top
                    and overlap_x
                    >= required_overlap_x  # Sufficient horizontal overlap to avoid wall-side misclassification
                    and physics.vy > -0.1  # Slight upward drift still counts if overlapping
                    and overlap_y < overlap_x  # More horizontal overlap = landing on top
                    and entity_rect.centery < tile.centery  # Entity above tile
                )

                if is_landing_on_top:
                    # Entity is above tile and overlapping
                    physics.on_ground = True

                    # Only resolve collision if there's significant penetration
                    # (more than 0.5 pixels to avoid micro-adjustments)
                    if feet_overlap > 0.5:
                        entity_rect.bottom = tile.top
                        physics.y = float(entity_rect.y)

                    # Zero velocity if falling
                    if physics.vy > 0:
                        physics.vy = 0.0

                    # Emit collision event (only on first landing)
                    if not old_on_ground and physics.vy >= 0:
                        event = CollisionEvent(
                            entity_id=entity.entity_id,
                            collision_type="ground",
                            normal=(0, -1),
                            tile_rect=tile,
                        )
                        events.append(event)
                        self.event_bus.emit(event)

                        if self.logger:
                            self.logger.debug(
                                f"Entity {entity.entity_id} ({entity.entity_type.value}) "
                                f"landed on ground"
                            )

                elif entity_rect.centery > tile.centery and physics.vy < 0:
                    # Entity hitting ceiling from below
                    entity_rect.top = tile.bottom
                    physics.y = float(entity_rect.y)
                    physics.vy = 0.0

                    # Emit collision event
                    event = CollisionEvent(
                        entity_id=entity.entity_id,
                        collision_type="ceiling",
                        normal=(0, 1),
                        tile_rect=tile,
                    )
                    events.append(event)
                    self.event_bus.emit(event)

                    if self.logger:
                        self.logger.debug(
                            f"Entity {entity.entity_id} ({entity.entity_type.value}) "
                            f"hit ceiling"
                        )

        # Check platform collisions (one-way, only from top)
        candidate_platforms = self._get_candidate_tiles(entity_rect, self.platforms, platforms=True)
        for platform in candidate_platforms:
            if entity_rect.colliderect(platform):
                # Platform collision only works when:
                # 1. Entity is falling (vy >= 0)
                # 2. Entity's bottom is within a few pixels of platform top
                # 3. Entity's center is above platform center (approaching from top)

                # Calculate how far entity's bottom extends past platform top
                overlap_y = entity_rect.bottom - platform.top

                # Check if entity is approaching from above and falling
                # Use feet position (bottom) instead of center for tall players (56px)
                # This ensures one-way platforms work correctly regardless of player height
                required_overlap_x = max(6, int(physics.width * 0.5))
                horizontal_overlap = min(entity_rect.right, platform.right) - max(
                    entity_rect.left, platform.left
                )
                if (
                    physics.vy > -0.1
                    and entity_rect.bottom
                    <= platform.bottom  # Feet must be at or above platform bottom
                    and overlap_y > 0
                    and overlap_y <= 14
                    and horizontal_overlap >= required_overlap_x
                ):

                    # Land on platform
                    physics.on_ground = True
                    entity_rect.bottom = platform.top
                    physics.y = float(entity_rect.y)

                    # Zero velocity
                    if physics.vy > 0:
                        physics.vy = 0.0

                    # Emit collision event (only on first landing)
                    if not old_on_ground:
                        event = CollisionEvent(
                            entity_id=entity.entity_id,
                            collision_type="platform",
                            normal=(0, -1),
                            tile_rect=platform,
                        )
                        events.append(event)
                        self.event_bus.emit(event)

                        if self.logger:
                            self.logger.debug(
                                f"Entity {entity.entity_id} ({entity.entity_type.value}) "
                                f"landed on platform"
                            )

        return events

    def _swept_vertical_collision(self, entity: Entity) -> list[CollisionEvent]:
        """
        Swept collision detection for high-speed vertical movement

        Prevents tunneling by checking collision along the movement path.
        This divides the movement into smaller steps to ensure no tiles are missed.

        NOTE: The physics system has ALREADY moved the entity. We need to check
        the path from the OLD position to the CURRENT position.

        Args:
            entity: Entity to check

        Returns:
            List of collision events
        """
        events = []
        physics = entity.physics

        # Save ground state before checking
        old_on_ground = physics.on_ground
        physics.on_ground = False

        # The entity has already been moved by physics.vy
        # We need to trace back and check the path
        end_y = physics.y
        start_y = end_y - physics.vy

        # Calculate number of steps based on velocity
        # Step size should be smaller than the smallest tile dimension
        step_size = 12.0  # pixels per step (slightly under half of 32px tile)
        total_distance = abs(physics.vy)
        num_steps = max(1, int(total_distance / step_size))

        collision_found = False
        collision_y = end_y  # Where collision occurred

        # Use x before horizontal movement was applied this frame so wall tiles
        # the player is pressing into are not misread as ceiling tiles.
        check_x = physics.x - physics.vx

        # Step through the movement path from start to end
        for step in range(num_steps + 1):
            if collision_found:
                break

            # Interpolate position along the path
            t = step / max(num_steps, 1)
            test_y = start_y + (end_y - start_y) * t
            entity_rect = pygame.Rect(int(check_x), int(test_y), physics.width, physics.height)

            # Check solid tile collisions at this step
            for tile in self._get_candidate_tiles(entity_rect, self.tiles):
                if entity_rect.colliderect(tile):
                    # Found a collision! Stop at this point in the path
                    collision_found = True
                    collision_y = test_y

                    if entity_rect.centery < tile.centery and physics.vy > 0:
                        # Entity hitting ground from above
                        physics.on_ground = True
                        # Position entity at collision point
                        entity_rect.y = int(collision_y)
                        entity_rect.bottom = tile.top
                        physics.y = float(entity_rect.y)
                        physics.vy = 0.0

                        # Emit collision event (only on first landing)
                        if not old_on_ground:
                            event = CollisionEvent(
                                entity_id=entity.entity_id,
                                collision_type="ground",
                                normal=(0, -1),
                                tile_rect=tile,
                            )
                            events.append(event)
                            self.event_bus.emit(event)

                    elif entity_rect.centery > tile.centery and physics.vy < 0:
                        # Entity hitting ceiling from below
                        entity_rect.y = int(collision_y)
                        entity_rect.top = tile.bottom
                        physics.y = float(entity_rect.y)
                        physics.vy = 0.0

                        # Emit collision event
                        event = CollisionEvent(
                            entity_id=entity.entity_id,
                            collision_type="ceiling",
                            normal=(0, 1),
                            tile_rect=tile,
                        )
                        events.append(event)
                        self.event_bus.emit(event)

                    break  # Stop checking tiles for this step

        # Check platform collisions (still use normal detection for platforms)
        entity_rect = physics.get_rect()
        for platform in self.platforms:
            if entity_rect.colliderect(platform):
                overlap_y = entity_rect.bottom - platform.top

                if (
                    physics.vy >= 0
                    and entity_rect.bottom <= platform.bottom  # Use feet position
                    and overlap_y > 0
                    and overlap_y <= 14
                ):  # Adjusted for taller player

                    physics.on_ground = True
                    entity_rect.bottom = platform.top
                    physics.y = float(entity_rect.y)
                    physics.vy = 0.0

                    if not old_on_ground:
                        event = CollisionEvent(
                            entity_id=entity.entity_id,
                            collision_type="platform",
                            normal=(0, -1),
                            tile_rect=platform,
                        )
                        events.append(event)
                        self.event_bus.emit(event)

        return events

    def _swept_horizontal_collision(self, entity: Entity) -> list[CollisionEvent]:
        """
        Swept collision detection for high-speed horizontal movement

        Prevents tunneling by checking collision along the movement path.
        This is crucial for dash movement (16.0 pixels/frame).

        Args:
            entity: Entity to check

        Returns:
            List of collision events
        """
        events = []
        physics = entity.physics

        # Reset wall state before checking
        physics.on_wall = False
        physics.wall_dir = 0

        # The entity has already been moved by physics.vx
        # We need to trace back and check the path
        end_x = physics.x
        start_x = end_x - physics.vx

        # Calculate number of steps based on velocity
        step_size = 12.0  # pixels per step (slightly under half of 32px tile)
        total_distance = abs(physics.vx)
        num_steps = max(1, int(total_distance / step_size))

        collision_found = False

        # Step through the movement path from start to end
        for step in range(num_steps + 1):
            if collision_found:
                break

            # Interpolate position along the path
            t = step / max(num_steps, 1)
            test_x = start_x + (end_x - start_x) * t
            entity_rect = pygame.Rect(int(test_x), int(physics.y), physics.width, physics.height)

            # Check solid tile collisions at this step
            for tile in self.tiles:
                if entity_rect.colliderect(tile):
                    # Found a collision! Stop at this point in the path
                    collision_found = True

                    # Resolve collision: move entity just outside the tile
                    if physics.vx > 0:
                        # Moving right - hit left side of tile
                        physics.x = tile.left - physics.width
                        physics.vx = 0
                        physics.on_wall = True
                        physics.wall_dir = 1

                        # Emit collision event
                        event = CollisionEvent(
                            entity_id=entity.entity_id,
                            collision_type="wall_right",
                            normal=(-1, 0),
                            tile_rect=tile,
                        )
                        events.append(event)
                        self.event_bus.emit(event)

                    else:
                        # Moving left - hit right side of tile
                        physics.x = tile.right
                        physics.vx = 0
                        physics.on_wall = True
                        physics.wall_dir = -1

                        # Emit collision event
                        event = CollisionEvent(
                            entity_id=entity.entity_id,
                            collision_type="wall_left",
                            normal=(1, 0),
                            tile_rect=tile,
                        )
                        events.append(event)
                        self.event_bus.emit(event)

                    break  # Stop checking tiles for this step

        return events

    def check_entity_collision(self, entity_a: Entity, entity_b: Entity) -> bool:
        """
        Check collision between two entities

        Args:
            entity_a: First entity
            entity_b: Second entity

        Returns:
            True if entities are colliding
        """
        if not entity_a.physics or not entity_b.physics:
            return False

        rect_a = entity_a.physics.get_rect()
        rect_b = entity_b.physics.get_rect()

        return rect_a.colliderect(rect_b)

    def get_entities_in_radius(
        self, center_x: float, center_y: float, radius: float
    ) -> list[Entity]:
        """
        Get all entities within radius of a point

        Useful for:
        - Explosion damage
        - Pickup collection
        - Area effects

        Args:
            center_x: Center X coordinate
            center_y: Center Y coordinate
            radius: Radius to check

        Returns:
            List of entities within radius
        """
        entities = []
        radius_squared = radius * radius

        for entity in self.entity_manager.entities.values():
            if not entity.physics or not entity.active:
                continue

            # Calculate distance (squared, no sqrt for performance)
            dx = entity.physics.x - center_x
            dy = entity.physics.y - center_y
            distance_squared = dx * dx + dy * dy

            if distance_squared <= radius_squared:
                entities.append(entity)

        return entities

    # ============================================================
    # Spatial Hash Helpers
    # ============================================================
    def _get_candidate_tiles(
        self, rect: pygame.Rect, tiles: list[pygame.Rect], platforms: bool = False
    ) -> list[pygame.Rect]:
        """
        Get nearby tiles using spatial hash to reduce collision checks.

        Args:
            rect: Entity rect
            tiles: Tile list (solids or platforms)
            platforms: Whether this is platform lookup

        Returns:
            List of tiles near the rect
        """
        if not self.tile_lookup and not self.platform_lookup:
            return tiles

        lookup = self.platform_lookup if platforms else self.tile_lookup
        margin = 64  # expand search area slightly
        min_chunk_x = (rect.left - margin) // self.chunk_size
        max_chunk_x = (rect.right + margin) // self.chunk_size
        min_chunk_y = (rect.top - margin) // self.chunk_size
        max_chunk_y = (rect.bottom + margin) // self.chunk_size

        candidates = []
        for cx in range(int(min_chunk_x), int(max_chunk_x) + 1):
            for cy in range(int(min_chunk_y), int(max_chunk_y) + 1):
                candidates.extend(lookup.get((cx, cy), []))
        return candidates if candidates else tiles

    def raycast(self, start_x: float, start_y: float, end_x: float, end_y: float) -> tuple | None:
        """
        Raycast from start to end point

        Useful for:
        - Line of sight checks
        - Projectile collision
        - Vision cones

        Args:
            start_x, start_y: Ray start point
            end_x, end_y: Ray end point

        Returns:
            (hit_x, hit_y, tile_rect) if hit, None otherwise
        """
        # Simple DDA raycast algorithm
        dx = end_x - start_x
        dy = end_y - start_y
        distance = max(abs(dx), abs(dy))

        if distance == 0:
            return None

        # Use step size for reasonable performance (check every ~8 pixels)
        step_size = 8.0
        steps = max(1, int(distance / step_size))

        x_inc = dx / steps
        y_inc = dy / steps

        x = start_x
        y = start_y

        # Create a small collision point
        point = pygame.Rect(0, 0, 1, 1)

        for i in range(steps + 1):
            # Update point position
            point.x = int(x)
            point.y = int(y)

            # Use spatial hash to get nearby tiles only
            chunk_x = int(x / self.chunk_size)
            chunk_y = int(y / self.chunk_size)

            # Check tiles in this chunk only (massive performance improvement)
            nearby_tiles = self.tile_lookup.get((chunk_x, chunk_y), [])

            for tile in nearby_tiles:
                if tile.colliderect(point):
                    return (x, y, tile)

            # Move to next point
            x += x_inc
            y += y_inc

        return None

    def get_collision_info(self, entity: Entity) -> dict:
        """
        Get collision information for entity

        Returns:
            Dictionary with collision flags
        """
        if not entity.physics:
            return {"on_ground": False, "on_wall": False, "wall_dir": 0, "on_ceiling": False}

        return {
            "on_ground": entity.physics.on_ground,
            "on_wall": entity.physics.on_wall,
            "wall_dir": entity.physics.wall_dir,
            "on_ceiling": False,  # TODO: Track ceiling flag if needed
        }
