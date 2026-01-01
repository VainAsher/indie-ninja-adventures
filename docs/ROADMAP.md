# Development Roadmap
**Vain Asher Gaming's: Indie Ninja Adventures**

This is a living document outlining the development roadmap for the project. Priorities and timelines may shift based on feedback and discoveries.

---

## Vision & Goals

### Core Vision
Create a fast-paced, skill-based 2D platformer with:
- Tight, responsive controls
- Deep movement mechanics
- Speedrun-friendly design
- Modular architecture for easy extensibility
- Multiplayer support (co-op and versus)

### Technical Goals
- Clean, modular codebase
- Full mod support via plugin system
- Deterministic physics for networking and replay
- Comprehensive documentation
- Professional code quality

### Design Pillars
1. **Precision**: Controls must feel pixel-perfect
2. **Flow**: Mechanics should chain together smoothly
3. **Depth**: Easy to learn, hard to master
4. **Accessibility**: Options for different skill levels
5. **Creativity**: Player expression through movement

---

## Current Status (v0.7.0)

### Completed (100%)

**Scope Freeze for next milestone (v0.6.1)**
- Focus game modes: **Campaign**, **Arcade**, **Sandbox**.
- Goal: stable vertical slice (movement/combat, pickups/hazards, exits/win flow, HUD/menus) before expanding missions/hub/trading/boss systems.
- Experimental/advanced systems remain off by default until the slice is green.

**Core Infrastructure**
- [x] Event bus system with priority handlers
- [x] Persistent logging with user-configurable location
- [x] Fixed 60Hz timestep clock (Glenn Fiedler pattern)
- [x] Serializable state management (JSON)
- [x] Component-based entity system
- [x] Mod/plugin architecture

**Collision & Physics**
- [x] Universal AABB collision system
- [x] Penetration resolution with normal vectors
- [x] Collision events for all interactions
- [x] Advanced queries (radius, raycast)
- [x] Physics system (gravity, velocity integration)
- [x] Fall speed capping
- [x] Overlap-based collision classification
- [x] Corner collision handling
- [x] Wall clipping prevention

**Player Mechanics**
- [x] Movement mechanic (ground/air physics)
- [x] Jump mechanic (ground, double, wall, coyote, buffer)
- [x] Dash mechanic (cooldown, wall cancel)
- [ ] Wall slide (implemented, currently disabled during wall rework; wall friction fallback active)
- [x] Crouch mechanic (stealth, ceiling detection)
- [x] Player orchestrator class
- [x] Input handling

**Testing & Documentation**
- [x] 14 comprehensive test suites
- [x] Integration tests
- [x] Edge case coverage
- [x] Complete API documentation
- [x] Architecture guide
- [x] Modding guide
- [x] Development docs (changelog, devlog, roadmap)

**Demo**
- [x] Playable demo game
- [x] All mechanics working together
- [x] Test level with platforms and walls
- [x] Multi-mode camera with letterboxing
- [x] Procedural world generation (16x16 zones, 160x160 rooms, seed-based)

---

## Phase 4.5: Movement Enhancement  COMPLETE

**Priority**: CRITICAL
**Target**: v0.3.2
**Status**: 100% Complete

### Goals
Eliminate movement jitter and enhance player movement feel by adopting smooth interpolation techniques from the dynamic dungeon platformer project.

### Analysis

The current movement system uses discrete acceleration steps (`vx += accel * direction`), which can cause jitter and less smooth movement. The dynamic dungeon platformer uses smooth interpolation (`vx += (target_vx - vx) * smooth_factor`), providing more responsive and fluid movement.

**Source Reference**: `dynamic_dungeon_platformer_project_zonegrid5_v1_2/main.py` lines 2120-2137

### Tasks

**Smooth Movement Interpolation** (4/4) 

- [x] Add MOVEMENT_ACCEL constant (2600.0) for high responsiveness
- [x] Replace discrete acceleration with smooth interpolation formula
- [x] Update ground and air movement to use new system
- [x] Verify smooth deceleration when releasing input

**Fast-Fall Mechanic** (3/3) 

- [x] Add FAST_FALL_MULT constant (1.7) to physics system
- [x] Implement gravity multiplier when holding down key while falling
- [x] Update physics system to apply fast-fall in appropriate states

**Testing** (4/4) 

- [x] Update `tests/unit/test_physics_system.py` for fast-fall
- [x] Update `tests/integration/test_player_integration.py` for smooth movement
- [x] Create edge case tests for movement transitions
- [x] Verify no jitter during continuous movement

**Documentation** (3/3) 

- [x] Update `docs/SYSTEM_OVERVIEW.md` with new movement API
- [x] Update `docs/CHANGELOG.md` [Unreleased] section
- [x] Update `docs/DEVLOG.md` with implementation notes

### Acceptance Criteria

- No visible jitter during horizontal movement
- Smooth acceleration and deceleration feel
- Fast-fall improves landing precision and air control
- All movement tests pass
- Movement feels more responsive than before

### Technical Details

**Current Implementation** (`mechanics/movement.py`):

```python
vx += accel * direction  # Discrete steps
```

**New Implementation**:

```python
target_vx = direction * MAX_RUN_SPEED * speed_multiplier
smooth_factor = min(1.0, MOVEMENT_ACCEL * dt / max(MAX_RUN_SPEED, 1.0))
state.physics.vx += (target_vx - state.physics.vx) * smooth_factor
```

**Benefits**:

- Eliminates jitter from discrete acceleration
- More responsive feel due to high acceleration constant
- Better player control and precision
- Matches feel of polished commercial platformers

---

## Phase 4.75: Camera System & Collision Polish  COMPLETE

**Priority**: CRITICAL
**Target**: v0.4.0
**Status**: 100% Complete (2025-12-12)

### Goals

Implement robust camera system and eliminate all collision edge cases to ensure perfect player physics.

### Completed Tasks

**Camera System** (6/6) 
- [x] Multi-mode camera (WORLD_CLAMP, ROOM_CLAMP, FREE, LOCKED)
- [x] Smooth following with deadzone and lerp
- [x] Responsive letterboxing for any window size
- [x] Virtual resolution (1280x720) scaled to display
- [x] Bounds clamping for world and room modes
- [x] In-game mode cycling with 'C' key

**Collision Fixes** (5/5) 
- [x] Platform collision with feet-based detection
- [x] Wall climbing bug fix (corner and ground detection)
- [x] Vertical tunneling prevention (physics tuning)
- [x] Player size adjustment (2856, 2:1 ratio)
- [x] Tile scaling to 32px (industry standard)

### Acceptance Criteria

All criteria met:
-  Camera smoothly follows player in all modes
-  Letterboxing maintains aspect ratio at any window size
-  No wall climbing when walking into walls
-  Platform collision works with tall player
-  No tunneling through tiles when falling
-  Player has proper platformer proportions (2:1)

---

## Phase B: Procedural World Generation  COMPLETE

**Priority**: HIGH
**Target**: v0.4.0
**Status**: 100% Complete (2025-12-11)

### Goals

Create a hierarchical procedural world generation system for metroidvania-style interconnected dungeons, caves, buildings, and levels. Use zone-based planning for intelligent room layout and feature placement.

### Analysis

The dynamic dungeon platformer uses a sophisticated hierarchical generation system:

```
World (seed-based, metroidvania structure)
   Biomes (dungeon, cave, building themes)
       Rooms (connected graph with types)
          Zone Grid (16x16 planning grid per room)
               Tilemap (generated from zone roles)
```

**Source Reference**: `dynamic_dungeon_platformer_project_zonegrid5_v1_2/main.py` lines 282-463

This allows for:
- Deterministic generation from seeds
- Interconnected world structure (metroidvania)
- Different biome generation patterns (dungeon mazes, cave networks, building rooms)
- Intelligent feature placement (spawn, exit, shop, treasure, combat areas)
- Guaranteed connectivity via BFS pathfinding validation

### Tasks

**Core World Generation** (6/6) 

- [x] Create `systems/world_generation.py` - WorldGenerator class
- [x] Implement seed-based world creation
- [x] Add biome system (dungeon, cave, building themes)
- [x] Create room graph with connectivity validation (BFS)
- [x] Implement room type system (start, exit, shop, combat, platform, treasure, boss)
- [x] Add door connection system with port positioning

**Zone Planning System** (5/5) 

- [x] Create `systems/zone_planning.py` - ZonePlanner class
- [x] Implement 16x16 zone grid per room
- [x] Add zone role assignment (WALK, FILL, PLAT, DOOR, SAVE, SHOP, LOOT)
- [x] Create shape pattern library for different biomes
- [x] Validate zone connectivity (ensure reachable zones)

**Room Generation** (5/5) 

- [x] Create `systems/room_generation.py` - RoomGenerator class
- [x] Generate tilemap from zone roles
- [x] Implement door carving with port system
- [x] Add platform/obstacle placement
- [x] Resolve anchor points (spawn, shop, loot, etc.)

**Placeholder Tile Assets** (3/3) 

- [x] Create sprite generator for 8x8 colored tile pieces
- [x] Generate basic tileset (terrain, wall, platform, feature)
- [x] Organize in `assets/biomes/` structure

**Demo Integration** (4/4) 

- [x] Add `--procedural` command-line flag to demo
- [x] Implement in-game toggle (P key) for world type switching
- [x] Add proper reload handling for world type changes
- [x] Maintain both static and procedural demo modes

**Testing** (3/4) - Quick tests created, comprehensive unit tests pending

- [x] Created `test_world_gen.py` (quick validation)
- [x] Created `test_zone_planning.py` (quick validation)
- [x] Created `test_full_generation.py` (complete pipeline test)
- [ ] Comprehensive unit tests with full coverage (deferred to future phase)

**Documentation** (4/4) 

- [x] Create `docs/WORLD_GENERATION.md` with complete API
- [x] Update `docs/SYSTEM_OVERVIEW.md` with world generation
- [x] Update `docs/CHANGELOG.md` [Unreleased] section
- [x] Update `docs/DEVLOG.md` with design decisions

### Acceptance Criteria

- Generates playable metroidvania worlds from seeds
- All rooms reachable from start room (validated connectivity)
- Different biomes use appropriate generation patterns
- Door connections work correctly between rooms
- Room types distribute properly (one start, one exit, etc.)
- `--procedural` flag switches between static and generated worlds
- In-game toggle (P key) switches world types with proper reload
- Performance: <200ms world generation for 20-30 rooms
- Deterministic: same seed always generates same world

### Technical Details

**Hierarchical Structure**:

```python
World:
  - seed: int
  - biomes: List[Biome]

Biome:
  - theme: str  # "dungeon", "cave", "building"
  - rooms: List[RoomNode]
  - connections: Dict[RoomNode, List[RoomNode]]

RoomNode:
  - position: Tuple[int, int]
  - room_type: str  # "start", "exit", "shop", "combat", etc.
  - zone_grid: List[List[ZoneRole]]  # 16x16 grid
  - tilemap: List[List[TileType]]
  - anchors: Dict[str, Tuple[int, int]]  # spawn, shop, loot, etc.

ZoneRole:
  - WALK: walkable floor
  - FILL: solid terrain
  - PLAT: platform
  - DOOR: door connection
  - SAVE: save point
  - SHOP: shop location
  - LOOT: treasure location
```

**Generation Flow**:

```python
# 1. World Generation
world = WorldGenerator.generate(seed=12345, num_biomes=3)

# 2. Biome Generation
for biome in world.biomes:
    rooms = generate_room_graph(biome.theme, num_rooms=10)
    validate_connectivity(rooms)  # BFS ensures all reachable

# 3. Zone Planning
for room in biome.rooms:
    zone_grid = ZonePlanner.plan(room.room_type, biome.theme)
    validate_zone_connectivity(zone_grid)

# 4. Tilemap Generation
for room in biome.rooms:
    tilemap = RoomGenerator.generate(room.zone_grid)
    carve_doors(tilemap, room.connections)
```

**Benefits**:

- Infinite replayability with seed-based generation
- Metroidvania-style exploration (interconnected world)
- Varied biome aesthetics and generation patterns
- Intelligent feature placement (shops, treasures, combat areas)
- Guaranteed playability (connectivity validation)
- Performance optimized (generation happens once at world creation)

---

## Phase 5: Rendering & Visual Polish (Planned)

**Priority**: High
**Target**: v0.4.0
**Status**: 0% Complete

### Goals
Transform the demo from rectangles to a polished visual experience.

### Tasks

**Sprite System** (3/6)
- [x] Sprite loader and manager (placeholder-generated sprites)
- [ ] Sprite sheet support
- [x] Sprite flipping (left/right facing)
- [ ] Layered rendering (background, player, foreground)
- [ ] Debug visualization toggle
- [ ] Sprite offset/anchor points

**Animation System** (2/5)
- [x] Frame-based animation (time-based cycling)
- [x] Animation state machine (state selector in render pipeline)
- [ ] Transition blending
- [ ] Animation events (footstep, landing, etc.)
- [ ] Sprite sheet animation support

**Camera System** (Complete in v0.7.0)
- [x] Multi-mode camera (world clamp, room clamp, free, locked)
- [x] Smooth follow with lerp and deadzone
- [x] Letterboxing and bounds clamping
- [ ] Look-ahead based on velocity (nice to have)
- [ ] Shake/zoom support (future polish)

**Particle System** (3/5)
- [x] Particle emitter base class (lightweight)
- [x] Dust particles (landing)
- [x] Trail particles (dash)
- [ ] Impact particles (wall hit)
- [ ] Configurable particle properties

**Visual Effects** (0/4)
- [ ] Screen shake system
- [ ] Flash/hit effects
- [ ] Death animation
- [ ] Respawn effect

**UI/HUD** (3/6)
- [x] Health display
- [x] Stamina bar (legacy wall slide HUD — mechanic disabled)
- [x] Dash cooldown indicator
- [ ] Debug overlay (FPS, position, velocity)
- [ ] HUD positioning system
- [ ] UI scaling support

### Acceptance Criteria
- Player has animated sprites for all states (idle, run, jump, fall, crouch, dash); wall slide animation deferred until mechanic returns
- Camera smoothly follows player with proper boundaries
- Particle effects enhance visual feedback
- HUD displays all relevant information clearly
- Performance remains at 60 FPS

---

## Phase 6: Gameplay Systems (Planned)

**Priority**: High
**Target**: v0.5.0
**Status**: 0% Complete

### Goals
Add core gameplay elements to make it a complete game.

### Tasks

**Level Integration** (0/5)
- [ ] Integrate legacy level generation
- [ ] Tilemap loading (JSON/TMX)
- [ ] Multiple level support
- [ ] Level transitions
- [ ] Spawn points

**Pickup System** (0/6)
- [ ] PickupComponent enhancement
- [ ] Coin/collectible system
- [ ] Health pickups
- [ ] Power-up system
- [ ] Collectible tracking
- [ ] Pickup animations

**Hazard System** (0/5)
- [ ] Spike hazards
- [ ] Pit/void detection
- [ ] Moving platforms
- [ ] Crushers
- [ ] Hazard damage system

**Enemy System** (0/7)
- [ ] Basic enemy AI (patrol, chase)
- [ ] Enemy types (ground, flying)
- [ ] Enemy attacks
- [ ] Enemy health
- [ ] Enemy spawning
- [ ] Enemy death/respawn
- [ ] Boss framework

**Goal/Exit System** (0/4)
- [ ] Level exit detection
- [ ] Win condition
- [ ] Level completion tracking
- [ ] Exit animation

**Progression** (0/5)
- [ ] Level unlocking
- [ ] Save/load system
- [ ] Checkpoint system
- [ ] Lives system
- [ ] Game over handling

### Acceptance Criteria
- Players can complete levels by reaching exits
- Enemies provide challenge and variety
- Pickups encourage exploration
- Hazards require skill to navigate
- Progress is saved between sessions

---

## Phase 7: Polish & Juice (Planned)

**Priority**: Medium
**Target**: v0.6.0
**Status**: 0% Complete

### Goals
Make the game feel amazing to play.

### Tasks

**Sound System** (0/7)
- [ ] Audio engine integration
- [ ] Sound effect manager
- [ ] Music system
- [ ] Volume controls
- [ ] Sound effect variations
- [ ] Audio mixing
- [ ] Audio event hooks

**Polish Effects** (0/8)
- [ ] Improved screen shake
- [ ] Slow-motion effects
- [ ] Freeze frames
- [ ] Color flashing
- [ ] Background parallax
- [ ] Weather effects (rain, snow)
- [ ] Dynamic lighting
- [ ] Shadow system

**Input Enhancement** (0/5)
- [ ] Input buffering refinement
- [ ] Control remapping
- [ ] Gamepad support
- [ ] Input recording/playback
- [ ] Control sensitivity settings

**Menus & UI** (0/7)
- [ ] Main menu
- [ ] Pause menu
- [ ] Settings menu
- [ ] Level select
- [ ] Credits screen
- [ ] Transition animations
- [ ] UI sound effects

**Statistics** (0/5)
- [ ] Time tracking
- [ ] Death counter
- [ ] Jump counter
- [ ] Best times
- [ ] Statistics display

### Acceptance Criteria
- Game feels polished and juicy
- Menus are intuitive and attractive
- Sound effects enhance gameplay
- Statistics encourage replayability
- Input feels perfect

---

## Phase 8: Advanced Features (Future)

**Priority**: Medium
**Target**: v0.7.0+
**Status**: 0% Complete

### Speedrunning (0/6)
- [ ] Timer system
- [ ] Leaderboards
- [ ] Ghost replay recording
- [ ] Ghost replay playback
- [ ] Speedrun categories
- [ ] Splits/segment timing

### Modding Support (0/6)
- [ ] Mod loader UI
- [ ] Mod browser
- [ ] Workshop integration
- [ ] Custom level loading
- [ ] Custom mechanic loading
- [ ] Mod documentation

### Level Editor (0/8)
- [ ] In-game editor
- [ ] Tile placement
- [ ] Entity placement
- [ ] Testing mode
- [ ] Export/import levels
- [ ] Sharing system
- [ ] Community levels
- [ ] Featured levels

### Accessibility (0/6)
- [ ] Colorblind modes
- [ ] Assist mode (easier gameplay)
- [ ] Control customization
- [ ] Text size options
- [ ] High contrast mode
- [ ] Screen reader support

### Daily Challenges (0/5)
- [ ] Procedural challenge generation
- [ ] Daily seed system
- [ ] Challenge leaderboard
- [ ] Challenge completion tracking
- [ ] Reward system

---

## Phase 9: Multiplayer (Long Term)

**Priority**: Low (Future)
**Target**: v1.0.0+
**Status**: 0% Complete

### Goals
Add co-op and versus multiplayer modes.

### Tasks

**Network Architecture** (0/8)
- [ ] Client/server separation
- [ ] State synchronization
- [ ] Client prediction
- [ ] Server reconciliation
- [ ] Lag compensation
- [ ] Network event system
- [ ] Connection handling
- [ ] Matchmaking

**Co-op Mode** (0/6)
- [ ] 2-4 player support
- [ ] Camera following multiple players
- [ ] Co-op specific levels
- [ ] Team health/lives
- [ ] Co-op mechanics (boost, throw)
- [ ] Local/online play

**Versus Mode** (0/5)
- [ ] Race mode
- [ ] Tag mode
- [ ] Battle mode
- [ ] Versus levels
- [ ] Scoring system

**Social Features** (0/5)
- [ ] Friends list
- [ ] Invites
- [ ] Spectator mode
- [ ] Chat system
- [ ] Emotes

### Acceptance Criteria
- Stable multiplayer with minimal lag
- Co-op mode is fun with friends
- Versus modes are competitive
- Netcode handles poor connections gracefully
- Server architecture is scalable

---

## Milestone Timeline

### Near Term (1-2 Weeks)
- **v0.4.0**: Complete Phase 5 (Rendering & Visual Polish)
  - Sprites, animations, camera, particles, HUD
  - Estimated: 20-30 hours

### Short Term (1 Month)
- **v0.5.0**: Complete Phase 6 (Gameplay Systems)
  - Levels, pickups, hazards, enemies, progression
  - Estimated: 30-40 hours

### Medium Term (2-3 Months)
- **v0.6.0**: Complete Phase 7 (Polish & Juice)
  - Sound, menus, statistics, polish effects
  - Estimated: 20-30 hours

### Long Term (3-6 Months)
- **v0.7.0**: Complete Phase 8 (Advanced Features)
  - Speedrunning, modding, level editor, accessibility
  - Estimated: 40-60 hours

### Future (6+ Months)
- **v1.0.0**: Complete Phase 9 (Multiplayer)
  - Network architecture, co-op, versus, social features
  - Estimated: 60-100 hours

---

## Feature Backlog

### High Priority
- Ledge grab mechanic
- Ground pound ability
- Air dash
- Slide mechanic (after dash)
- Momentum conservation between mechanics

### Medium Priority
- Grappling hook system
- Time slow power-up
- Teleport ability
- Wall run mechanic
- Double dash upgrade

### Low Priority
- Swimming mechanics
- Vehicle sections
- Puzzle elements
- Dialogue system
- Cutscene system

### Nice to Have
- Photo mode
- Custom skins
- Achievements
- Twitch integration
- Randomizer mode

---

## Technical Roadmap

### Headless & Networking Foundations
- [x] Headless mode toggle for CI (SDL dummy video, no window creation)
- [x] Input command pattern + snapshot serializer for authoritative sim
- [x] Deterministic replay/record harness for regression testing
- [ ] Structured logging (session/seed/build tags) for auditing
- [ ] Minimal client/server loop (authoritative server, input buffer on client)

### Performance
- [ ] Spatial partitioning (grid/quadtree) for collision
- [ ] Object pooling for entities
- [ ] Batch rendering optimizations
- [ ] Profiling and optimization pass
- [ ] Memory usage optimization

### Code Quality
- [ ] Type hint coverage to 100%
- [ ] Docstring coverage to 100%
- [ ] Linting with ruff/black
- [ ] CI/CD pipeline
- [ ] Automated testing

### Documentation
- [x] Changelog
- [x] Devlog
- [x] Roadmap
- [ ] API reference generation
- [ ] Video tutorials
- [ ] Modding examples

### Tooling
- [ ] Build system
- [ ] Asset pipeline
- [ ] Debugging tools
- [ ] Performance profiler
- [ ] Network debugger

---

## Success Metrics

### Technical Metrics
- **FPS**: Maintain 60 FPS in all scenarios
- **Load Time**: < 3 seconds for level load
- **Memory**: < 500MB RAM usage
- **Network Latency**: < 100ms for multiplayer
- **Test Coverage**: > 80% code coverage

### Gameplay Metrics
- **First Death**: Average time to first death > 30s (tutorial quality)
- **Completion Rate**: > 50% of players complete first level
- **Retention**: > 30% return after first session
- **Session Length**: Average 15-30 minutes per session
- **Skill Curve**: Clear progression from easy to hard

### Quality Metrics
- **Bug Rate**: < 1 critical bug per 100 hours of playtime
- **Crash Rate**: < 0.1% of sessions
- **User Satisfaction**: > 80% positive feedback
- **Performance**: 60 FPS on 5+ year old hardware
- **Accessibility**: Playable by colorblind users

---

## Risk Assessment

### High Risk
- **Network Complexity**: Multiplayer is hard, may delay v1.0.0
- **Scope Creep**: Feature backlog is large, need to prioritize
- **Performance**: May need optimization before adding more features

### Medium Risk
- **Asset Creation**: Art/sound assets may require external help
- **Balancing**: Difficulty curve needs extensive playtesting
- **Platform Support**: May need platform-specific work (Windows, Mac, Linux)

### Low Risk
- **Core Mechanics**: Solid foundation already in place
- **Architecture**: Modular design enables parallel development
- **Documentation**: Strong docs reduce onboarding friction

---

## Dependencies & Blockers

### Current Blockers
- None (all core systems complete)

### External Dependencies
- Art assets (sprites, tilesets)
- Sound effects and music
- Playtesting feedback
- Community input on features

### Technical Dependencies
- Pygame for rendering
- Python 3.11+ runtime
- JSON for data storage
- (Future) Network library for multiplayer

---

## Community & Collaboration

### Contribution Opportunities
- Art assets (sprites, tilesets, backgrounds)
- Sound effects and music
- Level design
- Playtesting and feedback
- Bug reports
- Documentation improvements
- Mod creation

### Feedback Channels
- GitHub issues for bugs
- Discord for discussions
- Playtesting sessions
- Community surveys

---

**Last Updated**: 2025-12-12
**Current Version**: 0.7.0
**Next Milestone**: v0.4.0 (Rendering & Visual Polish)
**Project**: Vain Asher Gaming's: Indie Ninja Adventures
**Status**: Core, collision, camera, and procedural world generation complete; moving to rendering/UI polish
