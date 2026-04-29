---
doc_type: technical
audience: developer
last_updated: 2026-04-28
---
# Tiled Map Editor — Room Template Setup

Room templates let designers override procedural generation for specific room types. Template rooms are authored in [Tiled](https://www.mapeditor.org/) and loaded at runtime by `TmxRoomLoader`.

---

## Quick Start

1. Install Tiled 1.10+ from [mapeditor.org](https://www.mapeditor.org/).
2. Open any template from `java/assets/rooms/templates/` (the runtime path — see Asset Layout below).
3. Edit using the `shadow_ascent_tiles` tileset (tile IDs below).
4. Save as CSV-encoded TMX (default in Tiled).
5. Run validation: `python tools/validate_room_templates.py --dir java/assets/rooms/templates`.

---

## Asset Layout

Two asset roots exist in this repo:

| Root           | Purpose                                                 | Loaded by                                  |
| -------------- | ------------------------------------------------------- | ------------------------------------------ |
| `assets/`      | Bundled into the client fat JAR — textures, audio, data | `Gdx.files.internal` (classpath)           |
| `java/assets/` | Filesystem access from the `java/` working directory    | `TmxRoomLoader` via `Files.newInputStream` |

**Room templates live in `java/assets/rooms/templates/`.** The server and tests resolve `assets/rooms/templates` relative to the `java/` working directory, giving `java/assets/rooms/templates/`.

The validation script default path is `assets/rooms/templates`; always override it:

```bash
python tools/validate_room_templates.py --dir java/assets/rooms/templates
```

---

## Tileset Reference

The tileset is `java/assets/tileset/shadow_ascent_tiles.png` — 568 tiles arranged in 8 columns × 71 rows (16×16 px each). The autotile blob-set atlas occupies the full sheet; template authors use only GIDs 0–8 (the first 9 logical engine slots) when painting terrain.

| Tile # | GID | Engine constant | Collision behaviour                     |
| ------ | --- | --------------- | --------------------------------------- |
| 1      | 0   | AIR             | No collision — open space               |
| 2      | 1   | SOLID           | Full block — stops all movement         |
| 3      | 2   | PLATFORM        | One-way — blocks downward movement only |
| 4      | 3   | ICE             | Solid + near-zero friction              |
| 5      | 4   | WATER           | Passable liquid — reduces speed         |
| 6      | 5   | LAVA            | Solid + 1 HP damage per tick            |
| 7      | 6   | DOOR_LOCKED     | Solid until puzzle solved               |
| 8      | 7   | GAS             | Passable + light drag                   |
| 9      | 8   | CLIMBABLE       | Solid + wall-climb surface              |

**GID** is the raw tile ID stored in the `.tmx` file; it equals the engine byte value.

---

## Map Settings

When creating a new template in Tiled:

| Setting           | Required value |
| ----------------- | -------------- |
| Map width         | 128 tiles      |
| Map height        | 128 tiles      |
| Tile width        | 16 px          |
| Tile height       | 16 px          |
| Tile layer format | CSV            |

---

## Template Files

Templates live in `java/assets/rooms/templates/`. The filename (without `.tmx`) is the **room type id** that matches `RoomTypeDefinition.id()` in the JSON definitions.

All entries with `requiresTemplate: true` in their JSON definition will load their `.tmx` before falling back to procedural generation.

| File                  | Room type       | Used when                 |
| --------------------- | --------------- | ------------------------- |
| `boss.tmx`            | boss            | Boss encounter room       |
| `shop.tmx`            | shop            | Merchant room             |
| `start.tmx`           | start           | Player spawn room         |
| `exit.tmx`            | exit            | Level exit room           |
| `combat_standard.tmx` | combat_standard | Formatted combat chamber  |
| `platform_ascent.tmx` | platform_ascent | Vertical platform climb   |
| `shop_interior.tmx`   | shop_interior   | Shop with interior layout |
| `treasure_maze.tmx`   | treasure_maze   | Maze with loot at the end |
| `duality_test.tmx`    | duality_test    | Yin/Yang stance test room |

---

## Template Variants

Authored room types can have multiple deterministic variants. The runtime checks `data/room_template_catalog.json` first:

```json
{
  "roomTypes": {
    "start": [
      { "file": "start.tmx", "weight": 1 },
      { "file": "start_alt.tmx", "weight": 2 }
    ]
  }
}
```

The room seed chooses one existing entry by weight. If the catalog is absent, has no entry for the room type, or points only at missing files, the loader falls back to filename conventions in `java/assets/rooms/templates/`:

- `<room_type>.tmx`
- `<room_type>_*.tmx`
- `<room_type>-*.tmx`

Convention variants are sorted by filename and selected deterministically from the room seed. The chosen TMX still receives runtime geometry enforcement for walls, floors, and door corridors.

---

## How Templates Are Loaded

`RoomGenerator.generate()` checks `RoomTypeDefinition.requiresTemplate()` first:

1. If `requiresTemplate: true`, calls `TmxRoomLoader.loadTemplate(def.id(), roomSeed)`.
2. If a catalog or convention variant exists: loads it, carves door openings, returns the grid.
3. If the file is absent: falls back to procedural generation silently.

This means templates can be removed without breaking the game — it just reverts to procedural.

---

## Layer Conventions

Templates must have at least one layer. The layer named **terrain** is loaded (case-insensitive). If no layer is named "terrain", the first layer is used.

Keep it to one layer. Additional layers (decorations, metadata) are ignored by the loader.

---

## Door Openings

Do **not** manually carve door openings in the template. The engine calls `carveDoors()` at load time based on which neighbouring rooms are connected. Template walls on connected edges will be cleared automatically.

This means templates define the interior geometry; the engine handles connectivity.

---

## Procedural Structure Rules

TMX templates are full-room overrides. Procedural rooms use `data/room_structure_rules.json` instead:

- `fillMin` / `fillMax` control how many obstacle or hazard zones are placed.
- hazard chance fields control lava, ice, and water role selection.
- DECOR chance fields control how unresolved zones become fill, platforms, walkable space, or void.
- `perimeterDepth` controls zone-level wall thickness around procedural rooms.
- `centerClearRadiusZones` keeps central arena space open for rooms such as `boss`.

These rules affect generated rooms only. If a `.tmx` exists for a room type, its authored interior wins, then runtime geometry enforcement still normalizes walls, floors, and door corridors.

---

## Zone Patch Templates

Procedural rooms can also use authored 8x8 Tiled patches during zone expansion.
These are smaller than room templates and live in:

```text
java/assets/rooms/zone_templates/
```

Use the same terrain GIDs as room templates, but make the map exactly `8 x 8`
tiles. Add weighted entries in `data/zone_template_catalog.json`.

`fallbackWeight` controls how often the existing built-in procedural pool remains
eligible. For example, `fallbackWeight: 6` plus two authored templates with
weight `1` means the legacy pool is selected six weighted rolls out of eight,
and the authored patches are selected two weighted rolls out of eight.

Validate patches and catalog entries with:

```bash
python tools/validate_zone_templates.py --dir java/assets/rooms/zone_templates --catalog data/zone_template_catalog.json
```

---

## Validation

Run before committing any template change:

```bash
python tools/validate_room_templates.py --dir java/assets/rooms/templates
```

This checks:

- Valid XML
- Correct 128×128 dimensions
- CSV encoding
- Tile values in range 0–8
- At least one non-AIR tile

Exit code 0 = all valid. Exit code 1 = one or more errors.

For structural checks, run strict geometry validation:

```bash
python tools/validate_room_templates.py --dir java/assets/rooms/templates --strict-geometry
```

When changing `data/room_template_catalog.json`, validate the catalog against the canonical Java template set:

```bash
python tools/validate_room_templates.py --dir java/assets/rooms/templates --strict-geometry --catalog data/room_template_catalog.json
```

The root `assets/rooms/templates/` directory can be strict-geometry checked when editing those copies, but it does not contain every catalog template. Use the Java directory for catalog validation.

Strict geometry uses `data/room_geometry_rules.json` by default. It checks the same core assumptions the Java runtime now enforces around room shell safety:

- wall thickness on room edges
- floor thickness on bottom rows
- standard door-corridor exceptions at each edge midpoint
- at least one standable tile with AIR above it

If strict geometry fails, the room can still pass basic TMX compatibility, but the authored shape is outside the current runtime geometry contract. Fix the TMX when the gap is unintentional; otherwise update the geometry rules only when the new structure is a deliberate design change.

---

## Adding a New Template

1. Create a new `.tmx` file in `java/assets/rooms/templates/` named `<room_type_id>.tmx`.
2. Create a matching `data/entities/rooms/types/<id>.json` with `requiresTemplate: true`.
3. Run `python tools/validate_room_templates.py --dir java/assets/rooms/templates` — confirm zero errors.
4. Commit both the `.tmx` and the `.json`.
