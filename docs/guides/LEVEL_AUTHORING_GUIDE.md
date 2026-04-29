# Level Authoring Guide

This guide explains how to design Shadow Ascent world-generation content after the room-geometry, room-structure, template-variant, and template-validation slices.

Use this as the working reference for designing levels, room templates, procedural room rules, zone behavior, and release checks.

## Mental Model

The runtime builds playable space in layers:

1. **Progression graph**: chooses central hub, region hubs, dungeon beats, grants, requirements, and critical path.
2. **World graph**: chooses rooms, room types, seeds, and neighbor directions.
3. **Room selection**: chooses either an authored TMX template or procedural generation.
4. **Zone plan**: procedural rooms get a 16x16 grid of zone roles.
5. **Zone expansion**: each zone becomes an 8x8 tile patch.
6. **Geometry enforcement**: walls, floors, and door corridors are normalized.
7. **Postprocess**: entities, puzzle gates, pickups, NPCs, bosses, and portals are placed.

Authored TMX templates skip the procedural zone plan for their interior, but they still receive geometry enforcement. Procedural rooms use data-driven structure rules plus zone templates.

## Canonical Files

Runtime-authored templates live here:

```text
java/assets/rooms/templates/
```

The root template folder is an editor/client copy:

```text
assets/rooms/templates/
```

The Java path is the canonical server/runtime validation target. Keep root copies aligned only when you intentionally maintain both.

Core authoring data:

```text
data/room_geometry_rules.json
data/room_structure_rules.json
data/room_template_catalog.json
data/zone_template_catalog.json
data/entities/rooms/types/*.json
```

Core code paths:

```text
java/shadowascent/src/main/java/com/indieniinja/world/WorldGraph.java
java/shadowascent/src/main/java/com/indieniinja/world/ZonePlanner.java
java/shadowascent/src/main/java/com/indieniinja/world/RoomGenerator.java
java/shadowascent/src/main/java/com/indieniinja/world/TmxRoomLoader.java
java/shadowascent/src/main/java/com/indieniinja/world/RoomTemplateCatalog.java
java/shadowascent/src/main/java/com/indieniinja/world/ZonePatchTemplateLibrary.java
java/shadowascent/src/main/java/com/indieniinja/world/RoomGeometryRules.java
java/shadowascent/src/main/java/com/indieniinja/world/RoomStructureRules.java
java/shadowascent/src/main/java/com/indieniinja/world/progression/WorldProgressionGraph.java
java/shadowascent/src/main/java/com/indieniinja/world/progression/WorldProgressionGenerator.java
java/shadowascent/src/main/java/com/indieniinja/world/progression/ProgressionValidator.java
```

## Designing Progression Graph Content

Think about level structure first as macro beats:

```text
central hub -> region hubs -> dungeon entry -> trial/reward -> lock gate -> boss
```

The progression graph layer records:

- region requirements
- dungeon requirements
- rewards/grants
- optional branches
- critical-path order
- services such as save/shop

Every required ability or key-like grant must appear before any required node
that needs it. `ProgressionValidator` checks this by walking reachable nodes
from `central_hub` while accumulating grants. Generated graphs are deterministic
from the world seed and covered by seed-sweep tests.

Current boundary: this layer does not yet replace room templates, zone patches,
room structure rules, or the live server layout. Later slices will use this
progression graph to choose section templates and spatial layout.

## Room Types

Room type ids are lowercase strings such as:

```text
start
exit
shop
combat
platform
treasure
boss
trial
combat_standard
platform_ascent
shop_interior
treasure_maze
duality_test
```

A room type can be:

- **Authored**: load a TMX template first.
- **Procedural**: build from a zone plan and structure rules.
- **Hybrid by fallback**: try a TMX, then fall back to procedural if no valid template exists.

Use authored templates when the room needs exact composition, story staging, a boss arena, a shop interior, a skill test, or hand-authored traversal. Use procedural rooms when variety and replayability matter more than exact layout.

## Designing Authored TMX Rooms

Create or edit templates in Tiled using:

```text
128 x 128 tiles
16 x 16 pixel tiles
CSV encoding
terrain layer name
GIDs 0-8 only
```

Tile meanings:

| GID | Meaning |
| --- | ------- |
| `0` | AIR |
| `1` | SOLID |
| `2` | PLATFORM |
| `3` | ICE |
| `4` | WATER |
| `5` | LAVA |
| `6` | DOOR_LOCKED |
| `7` | GAS |
| `8` | CLIMBABLE |

Do not manually cut permanent door holes. Door openings are carved at runtime based on neighboring rooms. The template should describe the room's interior and shell; the runtime handles connected exits.

### Geometry Contract

The active geometry defaults are:

| Rule | Default |
| ---- | ------- |
| room size | `128 x 128` tiles |
| outer wall thickness | `1` tile |
| floor thickness | `2` tiles |
| door half span | `5` tiles |
| horizontal door depth | `4` tiles |
| vertical door depth | `2` tiles |

That means authored templates should have:

- solid top wall outside the top door corridor
- solid left and right walls outside side door corridors
- solid bottom two rows outside the down door corridor
- at least one standable tile with AIR above it

Strict validation checks this contract:

```bash
python tools/validate_room_templates.py --dir java/assets/rooms/templates --strict-geometry
```

## Template Variants

Template variants are selected by room seed. Add explicit weighted variants in:

```text
data/room_template_catalog.json
```

Example:

```json
{
  "roomTypes": {
    "combat_standard": [
      { "file": "combat_standard.tmx", "weight": 2 },
      { "file": "combat_standard_cross.tmx", "weight": 1 },
      { "file": "combat_standard_tower.tmx", "weight": 1 }
    ]
  }
}
```

Weights are relative. A weight of `2` is twice as likely as a weight of `1`, but selection remains deterministic for a given room seed.

If no catalog entry exists, the loader can discover:

```text
<room_type>.tmx
<room_type>_*.tmx
<room_type>-*.tmx
```

Prefer explicit catalog entries for shipped content. They are easier to review and validate.

Catalog validation:

```bash
python tools/validate_room_templates.py --dir java/assets/rooms/templates --strict-geometry --catalog data/room_template_catalog.json
```

## Procedural Rooms And Zones

Procedural rooms start as a 16x16 zone grid. Each zone is later expanded into an 8x8 tile patch, creating the final 128x128 room.

Zone roles include:

| Role | Use |
| ---- | --- |
| `WALK` | open navigable space |
| `FILL` | solid obstacle zone |
| `PLAT` | one-way platform zone |
| `DOOR` | graph connection opening |
| `VOID` | empty pit or air volume |
| `SAVE` | save point feature |
| `SHOP` | shop NPC feature |
| `LOOT` | treasure feature |
| `CHUTE` | vertical drop path |
| `CLIMB` | vertical ascent path |
| `CONN` | hub connector |
| `LAVA` | damaging solid hazard |
| `ICE` | low-friction solid hazard |
| `WATER` | slowing passable hazard |

The important distinction:

- `ZonePlanner` decides broad room shape and zone roles.
- `ZoneTemplateLibrary` decides the 8x8 tile pattern for each fill/platform zone.
- `ZonePatchTemplateLibrary` can mix Tiled-authored 8x8 patches into that pool.
- `RoomGenerator` expands zones into tiles and applies geometry.

## Designing Tiled Zone Patch Templates

Zone patch templates are small Tiled maps used by procedural rooms. They are not
full rooms. A patch is stamped into one 8x8 zone after `ZonePlanner` has already
chosen a zone role.

Canonical runtime patches live here:

```text
java/assets/rooms/zone_templates/
```

The root editor copy is:

```text
assets/rooms/zone_templates/
```

Patch TMX requirements:

```text
8 x 8 tiles
16 x 16 pixel tiles
CSV encoding
terrain layer name
GIDs 0-8 only
```

Add patch entries in:

```text
data/zone_template_catalog.json
```

Example:

```json
{
  "roles": {
    "fill": {
      "fallbackWeight": 6,
      "templates": [
        { "file": "fill/solid_block.tmx", "weight": 1 },
        { "file": "fill/hollow_shell.tmx", "weight": 1 }
      ]
    },
    "plat": {
      "fallbackWeight": 6,
      "templates": [
        { "file": "plat/center_bar.tmx", "weight": 1 }
      ]
    }
  }
}
```

`fallbackWeight` is the chance budget reserved for the built-in procedural pool.
With `fallbackWeight: 6` and two authored templates at weight `1`, the legacy pool
is selected 6 out of 8 weighted rolls and authored patches are selected 2 out of
8. Use `fallbackWeight: 0` only when you intentionally want a role to be fully
authored by the catalog.

Optional `biomeIndexes` can restrict a patch to specific biome indexes:

```json
{ "file": "fill/crystal_pillar.tmx", "weight": 1, "biomeIndexes": [7] }
```

Validate patches and catalog entries with:

```bash
python tools/validate_zone_templates.py --dir java/assets/rooms/zone_templates --catalog data/zone_template_catalog.json
```

Changing patch files, weights, or fallback weights is replay-breaking for
procedural rooms because the same seed can stamp different 8x8 geometry.

## Inspecting Generated Maps

Use the world-generation snapshot command before and after template or rule
changes when you need a deterministic diffable export:

```bash
cd java
./gradlew.bat :shadowascent:worldgenSnapshot -Pseed=12345 -Prooms=20 -Pshape=BLOB "-Pout=build/worldgen-snapshots/seed-12345.json" --no-daemon
```

The snapshot records generator schema version, seed streams, room graph data,
neighbor directions, biome indexes, and per-room tile checksums. Use it as the
baseline artifact for future room/zone authoring changes until the visual map
viewer slice lands.

## Room Structure Rules

Procedural room behavior is controlled by:

```text
data/room_structure_rules.json
```

Fields:

| Field | Meaning |
| ----- | ------- |
| `fillMin` / `fillMax` | how many obstacle or hazard zones are placed |
| `lavaChance` | chance a placed obstacle becomes lava |
| `iceChance` | chance a placed obstacle becomes ice |
| `waterChance` | chance a placed obstacle becomes water |
| `decorFillChance` | chance unresolved DECOR becomes solid terrain |
| `decorPlatformChance` | chance unresolved DECOR becomes platform terrain |
| `decorWalkChance` | chance unresolved DECOR becomes walkable space |
| `perimeterDepth` | how many zone rings become perimeter walls |
| `centerClearRadiusZones` | radius around center forced to WALK after finalization |

Design examples:

- **Open boss arena**: lower `fillMin/fillMax`, lower `decorFillChance`, set `centerClearRadiusZones` to `1` or `2`.
- **Maze treasure room**: raise `fillMin/fillMax`, raise `decorFillChance`, lower platform chance.
- **Platform room**: raise `decorPlatformChance`, keep fill moderate, use some ice/water if the biome supports it.
- **Trial room**: lower random fill but raise platform chance to preserve skill-route readability.

Changing structure rules is replay-breaking because the same world seed can produce different zone plans.

## Geometry Rules

Shared wall, floor, and door behavior is controlled by:

```text
data/room_geometry_rules.json
```

Use this only for deliberate global geometry contract changes. Template authors should normally adapt TMX files to the rules, not change the rules for a single room.

Changing geometry rules is replay-breaking because it changes deterministic tile output.

## Designing A New Authored Room

1. Pick a room type id, for example `combat_standard_cross`.
2. Add or update `data/entities/rooms/types/<id>.json` if the room type is content-driven.
3. Create `java/assets/rooms/templates/<id>.tmx` in Tiled.
4. Use the terrain layer and GIDs 0-8.
5. Build the shell to match the geometry contract.
6. Add the file to `data/room_template_catalog.json` if it should be selected as a variant.
7. Run:

```bash
python tools/validate_room_templates.py --dir java/assets/rooms/templates --strict-geometry --catalog data/room_template_catalog.json
```

8. Run relevant Java tests if generation behavior changed:

```bash
cd java
./gradlew.bat :shadowascent:test --tests com.indieniinja.world.RoomGeometryRulesTest --no-daemon
./gradlew.bat :server:test --tests com.indieniinja.server.WorldGraphGenerationTest --no-daemon
```

## Designing A New Procedural Room Feel

1. Choose the room type id.
2. Add a room spec in `data/room_structure_rules.json`.
3. Decide the intended read:
   - arena
   - maze
   - vertical platforming
   - shop/rest
   - trial
   - connector/hub
4. Tune fill and DECOR probabilities.
5. Tune `perimeterDepth` and `centerClearRadiusZones`.
6. Generate several seeds and inspect output in-game.
7. Add a targeted test if you introduce a new structural invariant.

Good procedural room specs state intent through numbers. Avoid making every room dense, hazardous, or platform-heavy; preserve contrast between room types.

## Common Patterns

### Start Room

- Keep center readable and safe.
- Keep spawn space clear.
- Use low fill and low hazard pressure.
- Use authored template if spawn staging matters.

### Shop Room

- Keep NPC access obvious.
- Avoid pits and hazards near the shop zone.
- Use authored template for reliable staging.

### Combat Room

- Use mixed `FILL` and `PLAT` zones.
- Keep at least one clean loop or lane.
- Hazards should pressure movement without blocking all routes.

### Platform Room

- Favor `PLAT`, `CLIMB`, and vertical spacing.
- Avoid overfilling the center.
- Keep door-to-door routes readable.

### Treasure Room

- Maze-like fill is appropriate.
- Use controlled dead ends.
- Keep the reward path connected and legible.

### Boss Room

- Preserve arena center with `centerClearRadiusZones`.
- Keep entrances readable.
- Use hazards sparingly unless the boss behavior is designed around them.

## Release Checklist

Run these before tagging a generation/content release:

```bash
python tools/test_validate_room_templates.py
python tools/validate_room_templates.py --dir java/assets/rooms/templates --strict-geometry --catalog data/room_template_catalog.json
python tools/validate_room_templates.py --dir assets/rooms/templates --strict-geometry
cd java
./gradlew.bat :shadowascent:test --tests com.indieniinja.world.RoomGeometryRulesTest --no-daemon
./gradlew.bat :shadowascent:test --tests com.indieniinja.world.RoomStructureRulesTest --no-daemon
./gradlew.bat :shadowascent:test --tests com.indieniinja.world.RoomTemplateCatalogTest --no-daemon
./gradlew.bat :server:test --tests com.indieniinja.server.WorldGraphGenerationTest --no-daemon
```

Then from the repo root:

```bash
git diff --check
```

If all pass, commit, tag, and push.
