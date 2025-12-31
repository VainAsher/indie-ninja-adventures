# Legacy Files

This folder contains the original monolithic implementation files that have been replaced by the new modular architecture.

## Files

- **main.py** - Original game loop (replaced by modular game loop)
- **player.py** - Monolithic 224-line Player class (replaced by `entities/player.py` + modular mechanics)
- **ui.py** - Original UI (can be integrated with new architecture)
- **camera.py** - Camera system (can be reused as-is)
- **level_gen.py** - Level generation (can be integrated as-is)

## Status

These files are **kept for reference only**. The new modular architecture in the parent directory is the active codebase.

### What Was Replaced

**player.py** → Multiple systems:
- `mechanics/movement.py` - Ground/air acceleration
- `mechanics/jump.py` - All jump types
- `mechanics/dash.py` - Dash with cooldown
- `mechanics/wall_slide.py` - Wall cling with stamina
- `mechanics/crouch.py` - Stealth movement
- `entities/player.py` - Orchestrator

**main.py** → Will be replaced by:
- `game/game_loop.py` - Event-driven game loop
- `systems/physics_system.py` - Physics coordination
- `systems/input_system.py` - Input processing
- `rendering/` - Rendering systems

### Files That Can Be Reused

**camera.py** - Camera math is simple and can be integrated directly:
```python
from legacy.camera import Camera  # Works as-is
```

**level_gen.py** - Level generation is already deterministic:
```python
from legacy.level_gen import generate_level  # Works as-is
```

**ui.py** - UI components can be adapted to new architecture

## Migration Complete

The modular architecture is now ready for:
- ✅ Development
- ✅ Testing
- ✅ Demo/showcase
- ✅ Integration with level_gen and camera
- ✅ Network implementation

The legacy files are no longer needed for active development but are preserved for reference.

## Deletion

These files can be deleted once you're confident the new architecture covers all functionality.

To delete:
```bash
rm -rf legacy/
```
