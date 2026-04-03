"""
GameSimulator — Pure simulation core (no rendering, audio, or UI).

The server creates a GameSimulator from pre-built game systems and drives it at
60 Hz.  demo_game.py can also create one for delegation (smoke-test parity with
solo play).

Architecture:
    GameSimulator.__init__(bus, game_clock, collision_system, players, ...)
        Takes pre-built systems.  The server creates them headlessly via
        create_core_systems() + create_physics_and_collision(); demo_game.py
        passes in its own already-initialised references.

    GameSimulator.step(inputs, dt)
        Advances one tick:
          1. Apply InputCommand to each player via CommandKeyView
          2. game_clock.tick() + bus.process() (fires TickEvent → player mechanics)
          3. Platform update (if handle_platforms=True)
          4. Enemy AI update (multi-player aware)
          5. Pickup update

    GameSimulator.get_snapshot(frame) -> WorldSnapshot
        Serialises current entity state to a WorldSnapshot for broadcast.

Phase 3 work order: G1 (this file), used by G5 (server loop) and G6 (client reconciliation).
"""

from __future__ import annotations

# ── Platform physics constants (mirrored from demo_game.py) ───────────────────
_FALLING_PLATFORM_TRIGGER_DELAY = 0.35
_FALLING_PLATFORM_RESPAWN_DELAY = 2.5
_FALLING_PLATFORM_DROP_DISTANCE = 32 * 12
_FALLING_PLATFORM_GRAVITY = 1800.0
_FALLING_PLATFORM_MAX_SPEED = 800.0
_PLATFORM_CARRY_TOLERANCE = 2


class GameSimulator:
    """
    Self-contained simulation engine.

    Holds references to all simulation systems and advances them each tick.
    Must not import or call pygame.display, pygame.mixer, or any UI / menu code.
    pygame.Rect and pygame.init (headless) are acceptable.
    """

    def __init__(
        self,
        bus,
        game_clock,
        collision_system,
        players: dict[int, object],
        enemy_manager,
        pickup_manager,
        hazard_manager,
        dynamic_platforms: list[dict],
        static_platforms: list,
        megamap=None,
        seed: int = 0,
        handle_platforms: bool = True,
        combat_mechanics: "dict[int, object] | None" = None,
    ):
        """
        Args:
            bus: EventBus — already wired with player mechanics subscribed.
            game_clock: GameClock — firing TickEvent each tick.
            collision_system: CollisionSystem — spatial hash for tile/platform lookup.
            players: Mapping from slot index (0 = host) to Player instance.
            enemy_manager: EnemyManager with enemies already spawned.
            pickup_manager: PickupManager with pickups already spawned.
            hazard_manager: HazardManager.
            dynamic_platforms: List of platform dicts (shared objects — mutations
                               here are visible to demo_game.py render code).
            static_platforms: List of pygame.Rect for static platforms.
            megamap: Generated world map (needed for environment checks).
            seed: Current world seed — embedded in every WorldSnapshot.
            handle_platforms: If True, step() updates platforms directly
                              (server mode).  If False, platforms are assumed to
                              be updated by an external TickEvent subscriber
                              (demo_game.py mode).
            combat_mechanics: Optional mapping of slot → CombatMechanic for
                              server-side authoritative combat (Phase 3b).
                              When provided, step() calls check_enemy_collisions
                              for each alive player slot and applies damage.
        """
        self.bus = bus
        self.game_clock = game_clock
        self.collision_system = collision_system
        self.players: dict[int, object] = players
        self.enemy_manager = enemy_manager
        self.pickup_manager = pickup_manager
        self.hazard_manager = hazard_manager
        self.dynamic_platforms = dynamic_platforms
        self.static_platforms = static_platforms
        self.megamap = megamap
        self.seed = seed
        self.handle_platforms = handle_platforms
        self.combat_mechanics: dict[int, object] = combat_mechanics or {}

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def step(self, inputs: dict[int, object], dt: float) -> None:
        """
        Advance the simulation by one tick.

        Args:
            inputs: Mapping from slot index to InputCommand.  Slots absent from
                    the dict are not updated (player holds last known command).
            dt: Delta time in seconds (typically 1/60).
        """
        from network.input_pipeline import CommandKeyView

        # 1. Feed each player's InputCommand through the key-like adapter so
        #    mechanics can read it via their normal process_input() path.
        for slot, cmd in inputs.items():
            player = self.players.get(slot)
            if player is not None:
                player.process_input(CommandKeyView(cmd))

        # 2. Advance the game clock (fires TickEvent) and flush the bus.
        #    Player movement / jump / dash / crouch mechanics update here.
        self.game_clock.tick()
        self.bus.process()

        # 3. Platform updates (server mode only — demo_game.py uses TickEvent).
        if self.handle_platforms and self.dynamic_platforms:
            self._step_platforms(dt)

        # 4. Build (x, y, w, h) tuples for all alive players — used for
        #    enemy targeting and arrow collision.
        player_tuples: list[tuple[float, float, int, int]] = []
        for slot in sorted(self.players):
            p = self.players[slot]
            phys = p.state.physics
            if p.state.health_state.current_hp > 0:
                player_tuples.append((phys.x, phys.y, phys.width, phys.height))

        if not player_tuples:
            return  # every player is dead; skip AI and pickup steps

        # 5. Update enemy AI + physics (multi-player aware).
        _world_h = float(self.megamap.height_tiles * 32) if self.megamap else 0.0
        first = player_tuples[0]
        self.enemy_manager.update(
            dt=dt,
            player_x=first[0],
            player_y=first[1],
            player_width=first[2],
            player_height=first[3],
            collision_system=self.collision_system,
            world_h=_world_h,
            players=player_tuples,
        )

        # 6. Server-side player-enemy combat (Phase 3b).
        #    Only active when combat_mechanics were supplied (server mode).
        #    Runs after enemy AI so enemy positions / attack sub-states are
        #    already updated for this tick before damage is evaluated.
        for slot in sorted(self.players):
            mechanic = self.combat_mechanics.get(slot)
            if mechanic is None:
                continue
            p = self.players[slot]
            if p.state.health_state.current_hp <= 0:
                continue  # dead players skip combat
            damage = mechanic.check_enemy_collisions(
                p.state, self.enemy_manager, dt
            )
            if damage > 0:
                p.state.health_state.take_damage(damage, defense=0)

        # 7. Advance pickup animations.
        self.pickup_manager.update(dt)

        # 8. Authoritative pickup collection (server mode).
        #    check_collections() marks pickups as alive=False when a player
        #    overlaps them, ensuring WorldSnapshot reflects the true state.
        for slot in sorted(self.players):
            p = self.players[slot]
            phys = p.state.physics
            if p.state.health_state.current_hp > 0:
                self.pickup_manager.check_collections(
                    phys.x, phys.y, phys.width, phys.height
                )

    def get_snapshot(self, frame: int) -> object:
        """
        Build and return a WorldSnapshot from the current simulation state.

        Args:
            frame: Monotonic frame counter (supplied by the server loop).

        Returns:
            WorldSnapshot instance ready for serialisation and broadcast.
        """
        from entities.player_render_state import compute_anim_state
        from network.snapshots import (
            EnemyState,
            PickupState,
            PlatformState,
            PlayerState,
            WorldSnapshot,
        )

        # ── Players ──────────────────────────────────────────────────────────
        player_states: list[PlayerState] = []
        for slot in sorted(self.players):
            p = self.players[slot]
            phys = p.state.physics
            facing = int(p.state.facing)
            if facing == 0:
                facing = 1
            player_states.append(
                PlayerState(
                    player_id=str(p.player_id),
                    slot=slot,
                    pos=(phys.x, phys.y),
                    vel=(phys.vx, phys.vy),
                    health=int(p.state.health_state.current_hp),
                    facing=facing,
                    is_dead=p.state.health_state.current_hp <= 0,
                    anim_state=compute_anim_state(p),
                )
            )

        # ── Enemies ──────────────────────────────────────────────────────────
        enemy_states: list[EnemyState] = []
        for eid, enemy in self.enemy_manager.enemies.items():
            enemy_states.append(
                EnemyState(
                    enemy_id=eid,
                    x=enemy.physics.x,
                    y=enemy.physics.y,
                    vx=enemy.physics.vx,
                    vy=enemy.physics.vy,
                    hp=int(enemy.health_state.current_hp),
                    ai_state=enemy.ai_state.value,
                    facing_right=bool(enemy.facing_right),
                )
            )

        # ── Pickups ──────────────────────────────────────────────────────────
        pickup_states: list[PickupState] = []
        for pickup in self.pickup_manager.get_alive_pickups():
            pickup_states.append(
                PickupState(
                    pickup_id=pickup.pickup_id,
                    x=pickup.x,
                    y=pickup.y,
                    pickup_type=pickup.pickup_type,
                    alive=pickup.alive,
                )
            )

        # ── Platforms (falling only for Phase 3a) ────────────────────────────
        platform_states: list[PlatformState] = []
        for plat in self.dynamic_platforms:
            if plat.get("type") == "falling":
                plat_id = plat.get(
                    "id",
                    f"plat_{int(plat['origin_x'])}_{int(plat['origin_y'])}",
                )
                platform_states.append(
                    PlatformState(
                        platform_id=plat_id,
                        state=plat.get("state", "idle"),
                        pos_y=plat.get("pos_y", float(plat["origin_y"])),
                        timer=plat.get("timer", 0.0),
                        vy=plat.get("vy", 0.0),
                    )
                )

        return WorldSnapshot(
            frame=frame,
            seed=self.seed,
            players=player_states,
            enemies=enemy_states,
            pickups=pickup_states,
            platform_states=platform_states,
            metadata={},
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Platform helpers (replicated from demo_game.py closures)
    # ─────────────────────────────────────────────────────────────────────────

    def _step_platforms(self, dt: float) -> None:
        """Update all dynamic platform states and refresh collision map."""
        # Gather PhysicsState of alive players for "entity on platform" checks.
        physics_list = [
            p.state.physics
            for p in self.players.values()
            if p.state.health_state.current_hp > 0
        ]

        for platform in self.dynamic_platforms:
            if platform.get("type") == "moving":
                self._update_moving_platform(platform, dt, physics_list)
            else:
                self._update_falling_platform(platform, dt, physics_list)

        # Rebuild the active collider list and push it to the collision system.
        platform_colliders = self.static_platforms + [
            p["rect"] for p in self.dynamic_platforms if p["active"]
        ]
        self.collision_system.update_platforms(platform_colliders)

    @staticmethod
    def _entity_on_platform(physics, platform_rect, tolerance: int = _PLATFORM_CARRY_TOLERANCE) -> bool:
        """Return True if the entity's physics state is resting on platform_rect."""
        if not physics or not physics.on_ground:
            return False
        import pygame
        rect = pygame.Rect(int(physics.x), int(physics.y), physics.width, physics.height)
        if rect.right <= platform_rect.left or rect.left >= platform_rect.right:
            return False
        gap = platform_rect.top - rect.bottom
        return -1 <= gap <= tolerance

    @classmethod
    def _carry_entities(cls, physics_list: list, old_rect, dx: float, dy: float = 0.0) -> None:
        """Translate all entities that were resting on old_rect by (dx, dy)."""
        if dx == 0.0 and dy == 0.0:
            return
        for physics in physics_list:
            if cls._entity_on_platform(physics, old_rect):
                physics.x += dx
                physics.y += dy

    def _update_falling_platform(self, platform: dict, dt: float, physics_list: list) -> None:
        """State-machine update for a single falling platform."""
        rect = platform["rect"]
        supported = any(
            self._entity_on_platform(phys, rect) for phys in physics_list
        )
        state = platform["state"]

        if state == "idle":
            platform["active"] = True
            platform["visible"] = True
            if supported:
                platform["state"] = "triggered"
                platform["timer"] = 0.0

        elif state == "triggered":
            platform["active"] = True
            platform["visible"] = True
            if not supported:
                platform["state"] = "idle"
                platform["timer"] = 0.0
            else:
                platform["timer"] += dt
                if platform["timer"] >= _FALLING_PLATFORM_TRIGGER_DELAY:
                    platform["state"] = "falling"
                    platform["timer"] = 0.0
                    platform["vy"] = 0.0
                    platform["active"] = False

        elif state == "falling":
            platform["active"] = False
            platform["visible"] = True
            platform["vy"] = min(
                platform["vy"] + _FALLING_PLATFORM_GRAVITY * dt,
                _FALLING_PLATFORM_MAX_SPEED,
            )
            platform["pos_y"] += platform["vy"] * dt
            rect.y = int(round(platform["pos_y"]))
            if platform["pos_y"] - platform["origin_y"] >= _FALLING_PLATFORM_DROP_DISTANCE:
                platform["state"] = "respawn"
                platform["timer"] = 0.0
                platform["visible"] = False
                platform["pos_y"] = float(platform["origin_y"])
                rect.y = int(round(platform["pos_y"]))

        elif state == "respawn":
            platform["active"] = False
            platform["visible"] = False
            platform["timer"] += dt
            if platform["timer"] >= _FALLING_PLATFORM_RESPAWN_DELAY:
                platform["state"] = "idle"
                platform["timer"] = 0.0
                platform["vy"] = 0.0
                platform["active"] = True
                platform["visible"] = True

    def _update_moving_platform(self, platform: dict, dt: float, physics_list: list) -> None:
        """Advance a moving platform and carry any standing entities."""
        import pygame
        rect = platform["rect"]
        if platform["speed"] <= 0 or platform["min_x"] == platform["max_x"]:
            return
        old_rect = rect.copy()
        step = platform["speed"] * dt * platform["dir"]
        platform["pos_x"] += step
        if platform["pos_x"] < platform["min_x"]:
            platform["pos_x"] = platform["min_x"]
            platform["dir"] = 1
        elif platform["pos_x"] > platform["max_x"]:
            platform["pos_x"] = platform["max_x"]
            platform["dir"] = -1
        rect.x = int(round(platform["pos_x"]))
        dx = float(rect.x - old_rect.x)
        if dx != 0.0:
            self._carry_entities(physics_list, old_rect, dx, 0.0)
