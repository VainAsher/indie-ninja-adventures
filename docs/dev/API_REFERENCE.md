# API Reference

Auto-generate the full HTML API reference with `pdoc`:

```bash
pip install pdoc
pdoc game/ systems/ network/ core/ entities/ mechanics/ -o docs/dev/api/
```

Open `docs/dev/api/index.html` in a browser.

---

## Why pdoc

- Zero configuration — uses existing docstrings
- Generates clean HTML from Python type hints
- No sphinx setup overhead
- Output is gitignored (regenerate on demand)

---

## Generating in CI (On Demand)

The workflow `.github/workflows/generate_api_docs.yml` generates and uploads the HTML as an
artifact when triggered manually (`workflow_dispatch`). It does not auto-deploy.

To trigger: **Actions → Generate API Docs → Run workflow**

---

## Key Modules

These modules have the most public surface area and are documented with docstrings:

| Module | Description |
|--------|-------------|
| `core/event_bus.py` | Pub/sub event system |
| `core/entity_system.py` | ECS base classes |
| `core/state.py` | Serialisable game state |
| `network/client.py` | NetworkClient — game loop interface |
| `network/snapshots.py` | WorldSnapshot, PlayerState serialisation |
| `network/commands.py` | InputCommand |
| `network/input_pipeline.py` | Record/replay pipeline |
| `systems/collision_system.py` | AABB collision |
| `systems/world_generation.py` | Procedural world gen |
| `systems/save_system.py` | Save/load with integrity |
| `game/campaign_manager.py` | Campaign progression |
| `game/game_simulator.py` | Server-side simulation |
| `entities/player.py` | Player orchestrator |

---

## Docstring Convention

Use Google-style docstrings:

```python
def resolve(self, entity: Entity, tilemap: Tilemap, dt: float) -> CollisionResult:
    """Resolve AABB collisions for entity against tilemap.

    Args:
        entity: The entity to resolve collisions for.
        tilemap: The tilemap to check against.
        dt: Delta time in seconds (fixed at 1/60).

    Returns:
        CollisionResult with on_ground, hit_wall, hit_ceiling flags.
    """
```
