# Graphics & Tile Rendering Reference

This document explains how the game's tile graphics are loaded, rendered, and how to provide your own artwork to replace or improve them.

---

## Table of Contents

1. [Overview](#1-overview)
2. [World Hierarchy — What Drives Which Tiles Appear](#2-world-hierarchy)
3. [Tile Types & IDs](#3-tile-types--ids)
4. [Biome Themes](#4-biome-themes)
5. [Asset Directory Structure — Where to Put Your Files](#5-asset-directory-structure)
6. [The Autotiling System](#6-the-autotiling-system)
7. [How TileLoader Works](#7-how-tileloader-works)
8. [Rendering Order (Draw Layers)](#8-rendering-order-draw-layers)
9. [Region → Biome Mapping](#9-region--biome-mapping)
10. [How to Add Your Own Tiles](#10-how-to-add-your-own-tiles)
11. [Fallback Colors (Diagnostic Reference)](#11-fallback-colors-diagnostic-reference)
12. [Key Files Quick Reference](#12-key-files-quick-reference)

---

## 1. Overview

- **Engine:** Pygame (Python), virtual game resolution **1280×720**
- **Tile display size:** all tiles are rendered at **32×32 pixels** in-game
- **Original tile spec:** 8×8 pixels (the design spec; the loader accepts any size and rescales)
- **Biome themes:** 7 (`dungeon`, `cave`, `building`, `forest`, `town`, `sewer`, `hollow`)
- **Active tile types:** only `solid` and `platform` are autotiled from PNG files; all other types (lava, water, moving/falling platforms) render as fallback colors until you add PNGs for them
- **Procedural generation:** the game builds worlds from seed values — tiles are not hand-placed but generated from a rules-based hierarchy described below

---

## 2. World Hierarchy

Understanding this chain explains *why* a particular tile appears at a particular screen position.

```
Hub / Mission Definition
  └─ World  (WorldGenerator, seed-based)
       └─ Biome(s)  (dungeon | cave | building | forest | town | sewer | hollow)
            └─ Room(s)  (each room = 128×128 tiles = 4 096×4 096 pixels)
                 └─ Zone Grid  (16×16 zones per room)
                      └─ Tiles  (each zone expands to 8×8 tiles)
```

### Hubs

Hubs are persistent social spaces (town-squares, mission boards). Each hub definition specifies a single `biome_theme` that is enforced for every tile in that hub.

- **Defined in:** `game/hub_manager.py` → `HubDefinition`
- **Types:** `HubType.CENTRAL` (main hub), `HubType.REGION` (per-biome hub)

### Worlds

A World is the full map for one run. It contains one or more `Biome` regions, each holding a set of rooms.

- **Defined in:** `systems/world_generation.py` → `World` dataclass
- **Generation:** seeded (`world.seed`) — same seed always produces the same layout
- **Shapes:** `SNAKE`, `BRANCHY`, `BLOB`, `SPIRAL`, `TREE`, `GRID`

### Missions

Missions drive world generation. A mission definition specifies the `region` (which maps to a biome theme), number of rooms, world shape, and objectives.

- **Defined in:** `data/missions.json`
- **Read by:** `game/mission_registry.py` → `MissionDefinition`

### Rooms

Each room occupies one cell in the world grid at position `(grid_x, grid_y)`. A room stores:

- `biome_theme` — which biome's tile assets to use
- `room_type` — affects the zone layout (`START`, `EXIT`, `SHOP`, `COMBAT`, `PLATFORM`, `TREASURE`, `BOSS`)
- `tilemap` — the generated 128×128 integer grid (see tile IDs below)

### Zones

Before tiles are generated, each room is planned as a 16×16 **zone grid**. Each zone cell is assigned a *role* that determines what tiles fill the corresponding 8×8 tile block.

| Zone Role | Constant | What Tiles It Produces |
|-----------|----------|------------------------|
| `fill` | `Z_FILL` | Full 8×8 block of `TILE_SOLID` |
| `walk` | `Z_WALK` | Floor tile at bottom of block |
| `platform` | `Z_PLAT` | `TILE_PLATFORM` row at mid-height |
| `door` | `Z_DOOR` | Passable gap (no solid tiles) |
| `void` | `Z_VOID` | Empty — `TILE_EMPTY` throughout |
| `chute` | `Z_CHUTE` | Empty vertical shaft (for down-doors) |
| `climb` | `Z_CLIMB` | Ascending staircase of platforms |
| `connector` | `Z_CONNECTOR` | Horizontal platform (hub rooms) |
| `save` | `Z_SAVE` | Floor with save-point anchor |
| `shop` | `Z_SHOP` | Floor with shop-NPC anchor |
| `loot` | `Z_LOOT` | Floor with treasure anchor |
| `decor` | `Z_DECOR` | Treated as walkable floor |

Zone planning is in `systems/zone_planning.py`. The expansion from zones to tile IDs is in `systems/room_generation.py`.

---

## 3. Tile Types & IDs

The tilemap stores integer IDs. These IDs are what the renderer reads to decide which PNG to load.

| ID | Constant | Name | Autotiled? | PNG Source |
|----|----------|------|-----------|------------|
| 0 | `TILE_EMPTY` | Empty | — | nothing rendered |
| 1 | `TILE_SOLID` | Solid / terrain | **Yes** | `assets/biomes/{biome}/tile_*.png` |
| 2 | `TILE_PLATFORM` | One-way platform | **Yes** | `assets/biomes/{biome}/tile_*.png` (first 25%) |
| 3 | `TILE_LAVA` | Lava | No | fallback color until PNG added |
| 4 | `TILE_WATER` | Water | No | fallback color until PNG added |
| 5 | `TILE_PLATFORM_FALLING` | Falling platform | No | fallback color until PNG added |
| 6 | `TILE_PLATFORM_MOVING` | Moving platform | No | fallback color until PNG added |

Only `TILE_SOLID` and `TILE_PLATFORM` currently read from PNG files. The others render as solid colored rectangles until you add support for them (see [Section 10](#10-how-to-add-your-own-tiles)).

---

## 4. Biome Themes

The game has 7 visual themes. Each maps to its own asset folder under `assets/biomes/`.

| Biome | Folder | Visual Intent |
|-------|--------|---------------|
| `dungeon` | `assets/biomes/dungeon/` | Stone corridors, gray |
| `cave` | `assets/biomes/cave/` | Earthy caverns, brown |
| `building` | `assets/biomes/building/` | Brick/stone structures, dark gray |
| `forest` | `assets/biomes/forest/` | Mossy ground, green stone |
| `town` | `assets/biomes/town/` | Cobblestone streets, warm |
| `sewer` | `assets/biomes/sewer/` | Mossy stone, damp |
| `hollow` | `assets/biomes/hollow/` | Deep purple-black rock, corrupted |

---

## 5. Asset Directory Structure

### The naming convention that matters

The tile loading system scans each biome folder for files matching the pattern **`tile_*.png`**. Only files with this prefix are loaded as playable tiles.

```
assets/biomes/
├── dungeon/
│   ├── tile_001.png          ← LOADED (solid variant)
│   ├── tile_002.png          ← LOADED (solid variant)
│   ├── tile_wall_v1.png      ← LOADED (solid variant)
│   └── ...                   ← any tile_*.png file is picked up
├── cave/
│   └── tile_*.png            ← same pattern
├── building/
├── forest/
├── town/
├── sewer/
└── hollow/
```

> **Important:** The files currently in the biome folders (`terrain.png`, `wall.png`, `platform.png`, etc.) do **not** match the `tile_*.png` pattern and are therefore **not loaded** by the current tile system. All in-game tiles currently render as fallback colored rectangles. Adding `tile_*.png` files is the primary way to bring real art into the game.

### How the system splits tiles between solid and platform

When a biome folder is scanned, the discovered files are sorted alphabetically and split as follows:

- **Solid tiles (`TILE_SOLID`):** all discovered `tile_*.png` files
- **Platform tiles (`TILE_PLATFORM`):** the first 25% of discovered `tile_*.png` files

So if you have `tile_001.png` through `tile_020.png`, tiles 001–005 appear on platforms and all 20 appear on solid terrain.

---

## 6. The Autotiling System

Autotiling selects *which* tile PNG to display at each position based on the neighboring tiles, so that walls have visible edges and corners instead of repeating the same interior tile everywhere.

### How the 9-shape detection works

For every `TILE_SOLID` or `TILE_PLATFORM` cell in the tilemap, the system checks the **4 cardinal neighbors** (up, down, left, right):

- If a neighbor has a **different tile ID** (or is out-of-bounds), that side is an **edge**
- The combination of which sides are edges determines one of 9 **shape keys**

```
Shape grid:

  top_left  | top_mid  | top_right
  ----------+----------+----------
  mid_left  | mid_mid  | mid_right
  ----------+----------+----------
  bottom_left | bottom_mid | bottom_right
```

Examples:
- A tile fully surrounded by the same tile type → `mid_mid`
- A tile at the top-left corner of a block → `top_left`
- A tile along the top edge, not at a corner → `top_mid`

### How variants are selected

Currently the system uses **all `tile_*.png` files** in the folder as variants for **every** shape (the shape key is determined but doesn't yet filter which PNG is chosen). The variant index is selected **deterministically** using position + world seed:

```python
hash = (x * 73856093) ^ (y * 19349663) ^ (seed * 83492791)
variant_index = abs(hash) % num_variants
```

This means:
- The same tile at the same world position always looks the same
- Different positions get different variants from your tile pool → natural texture variation
- Adding more `tile_*.png` files increases variety automatically

### Future: shape-specific PNGs

The system is designed to support shape-specific PNG assignment in `tile_config_autotile.py`. If you want tile 001 to only appear on `mid_mid` (interior) positions and tile 002 only on `top_left` corners, you can modify `get_autotile_variants()` in `assets/biomes/tile_config_autotile.py` to return different file lists per shape.

---

## 7. How TileLoader Works

Full pipeline from game request to screen pixel:

```
game loop calls:
  tile_loader.get_autotiled_tile(biome, tile_type, tilemap, x, y, tile_id, seed)
      │
      ├─ 1. autotile_key(tilemap, x, y, tile_id)
      │      checks 4 neighbors → returns shape ("top_left", "mid_mid", etc.)
      │
      ├─ 2. get_variant_count(biome, tile_type, shape)
      │      counts how many tile_*.png files exist for this biome
      │      if 0 → return fallback colored tile
      │
      ├─ 3. deterministic_variant_index(x, y, seed, num_variants)
      │      hash of position + seed → stable variant index
      │
      ├─ 4. cache check: (biome, tile_type, shape, variant_idx, "autotile")
      │      cache hit → return immediately
      │
      ├─ 5. get_autotile_path(biome, tile_type, shape, variant_idx)
      │      resolves to: assets/biomes/{biome}/tile_{name}.png
      │      if file missing → return fallback colored tile
      │
      ├─ 6. PIL Image.open(path)
      │      .resize((32, 32), Image.LANCZOS)   ← scales from any input size
      │      → convert to pygame Surface with alpha
      │
      └─ 7. cache store + return surface
```

**Key behaviors:**
- Input PNG can be **any size** — the loader always rescales to 32×32
- For crisp pixel art: provide **8×8** or **32×32** (integer scaling multiples)
- For smooth/hi-res art: provide **64×64** or larger — LANCZOS downscale smooths it
- Tiles are cached in memory for the session; the cache is keyed per biome+type+position+seed
- In headless/CI mode (no display), all tiles automatically return fallback colors

---

## 8. Rendering Order (Draw Layers)

The main render loop in `demo_game.py` draws in this order (back to front):

| Order | Content | Notes |
|-------|---------|-------|
| 1 | Background fill | `COLOR_BG = (10, 10, 20)` — dark navy |
| 2 | **TILE_SOLID** | Autotiled, per biome, with camera culling |
| 3 | **TILE_LAVA / TILE_WATER** | Liquid layer, no autotiling |
| 4 | **TILE_PLATFORM** | Static one-way platforms, autotiled |
| 5 | **TILE_PLATFORM_FALLING / MOVING** | Dynamic platforms |
| 6 | Particles | Behind player |
| 7 | Hazards | Spikes, traps |
| 8 | Pickups | Coins, health drops |
| 9 | Portals | Fast travel |
| 10 | Enemies | With attack telegraphs |
| 11 | Player | |
| 12 | HUD / UI | Health bar, inventory, menus |

### Camera culling

Only tiles within the camera viewport + a 10-tile (320 px) margin are rendered each frame. The full megamap (all rooms stitched together) exists in memory but off-screen tiles are skipped entirely.

---

## 9. Region → Biome Mapping

Missions in `data/missions.json` specify a `region` string. This maps to a biome theme when generating the world:

| Region (missions.json) | Biome Theme | Asset Folder |
|------------------------|-------------|--------------|
| `forest` | `dungeon` | `assets/biomes/dungeon/` |
| `town` | `building` | `assets/biomes/building/` |
| `caves` | `cave` | `assets/biomes/cave/` |
| `castle` | `building` | `assets/biomes/building/` |
| `sewer` | `dungeon` | `assets/biomes/dungeon/` |
| `hollow_depths` | `cave` | `assets/biomes/cave/` |

Hub worlds bypass this mapping — they use `HubDefinition.biome_theme` directly.

---

## 10. How to Add Your Own Tiles

### Quickstart — replace all solid tiles in a biome

1. Create your tile PNG(s) — any size, but **8×8** or **32×32** is recommended for pixel art
2. Name them with the `tile_` prefix: `tile_001.png`, `tile_stone_v1.png`, etc.
3. Drop them into the biome folder: `assets/biomes/{biome}/tile_*.png`
4. Launch the game — no code changes needed

The scanner auto-discovers all `tile_*.png` files on startup.

---

### Adding multiple variants for natural texture variation

Add more `tile_*.png` files to the folder. The system automatically uses the full pool as variants, selected deterministically by tile position. You can have as many variants as you want.

```
assets/biomes/dungeon/
├── tile_stone_v1.png    ← smooth stone
├── tile_stone_v2.png    ← cracked stone
├── tile_stone_v3.png    ← mossy stone
└── tile_stone_v4.png    ← chipped stone
```

All four variants will appear across the dungeon naturally.

---

### Controlling which tiles appear on platforms vs. solid terrain

The first 25% of your sorted `tile_*.png` files are used for platforms; all files are used for solid terrain. To control this:

- Put your platform-style tiles first alphabetically (e.g. `tile_a_platform.png`, `tile_b_platform.png`)
- Or edit `assets/biomes/tile_config.py` → `_build_biome_tiles()` to return specific lists for `"solid"` and `"platform"` keys

---

### Shape-specific autotile PNGs (for seamless edges)

To use different artwork for corners vs. interior vs. edges, edit `assets/biomes/tile_config_autotile.py` → `_build_autotile_config()`. Change the line:

```python
# Current: same tiles for all shapes
config[biome] = {
    "solid": dict.fromkeys(AUTOTILE_SHAPES, solid_tiles),
    ...
}
```

To return per-shape lists:

```python
config[biome] = {
    "solid": {
        "top_left":    ["tile_corner_tl.png"],
        "top_mid":     ["tile_edge_top.png"],
        "top_right":   ["tile_corner_tr.png"],
        "mid_left":    ["tile_edge_left.png"],
        "mid_mid":     ["tile_interior_v1.png", "tile_interior_v2.png"],
        "mid_right":   ["tile_edge_right.png"],
        "bottom_left": ["tile_corner_bl.png"],
        "bottom_mid":  ["tile_edge_bottom.png"],
        "bottom_right":["tile_corner_br.png"],
    },
    ...
}
```

---

### Adding lava, water, or dynamic platform graphics

These tile types currently have no PNG loading code — they use fallback colors only. To add PNG support, extend `TileLoader.get_autotiled_tile()` (or add a new method) in `rendering/tile_loader.py` to handle `tile_id == TILE_LAVA`, etc., and resolve the path from a new entry in `tile_config.py`.

---

### Tile size reference

| Input PNG size | Result | Notes |
|----------------|--------|-------|
| 8×8 | Upscaled 4× to 32×32 | Crisp pixel art (recommended for pixel style) |
| 32×32 | No scaling needed | 1:1 display |
| 64×64 | Downscaled 2× | Smooth, good for detailed art |
| 70×70 | Downscaled | Legacy size from original tileset extraction |
| 128×128 | Downscaled | Hi-res artwork, LANCZOS filtered |
| Any other | Rescaled | Always lands at 32×32 in-game |

---

## 11. Fallback Colors (Diagnostic Reference)

If you see flat-colored blocks instead of tile art, the PNG was not found. Use these colors to identify which biome/type is missing:

| Biome | Solid | Platform | Lava | Water |
|-------|-------|----------|------|-------|
| dungeon | (100,100,120) gray stone | (139,69,19) brown | (200,70,20) orange | (40,90,160) blue |
| cave | (101,67,33) brown earth | (121,87,53) light brown | (220,80,20) lava | (30,80,140) water |
| building | (64,64,64) dark gray | (160,120,80) light wood | (180,60,20) | (30,90,170) |
| forest | (34,85,34) forest green | (90,60,30) dark bark | (200,70,20) | (30,100,180) |
| town | (110,100,90) cobblestone | (140,110,70) plank | (200,70,20) | (40,90,160) |
| sewer | (50,65,50) mossy stone | (60,80,60) damp ledge | (180,60,20) | (30,110,60) murky green |
| hollow | (40,35,55) purple-black | (55,45,75) crystal | (160,40,120) magenta | (20,60,120) |

Fallback color logic is defined in `rendering/tile_loader.py` → `_get_fallback_tile()`.

---

## 12. Key Files Quick Reference

| File | Purpose |
|------|---------|
| [`assets/biomes/tile_config.py`](../assets/biomes/tile_config.py) | Scans `tile_*.png` files per biome; builds `BIOME_TILES` dict; `get_tile_path()` |
| [`assets/biomes/tile_config_autotile.py`](../assets/biomes/tile_config_autotile.py) | Builds autotile variant lists; `get_autotile_path()`, `deterministic_variant_index()` |
| [`rendering/tile_loader.py`](../rendering/tile_loader.py) | `TileLoader` class — loads, scales (PIL LANCZOS → 32×32), caches, returns surfaces |
| [`systems/autotiling.py`](../systems/autotiling.py) | `autotile_key()` — 4-neighbor detection → 9 shape keys |
| [`systems/room_generation.py`](../systems/room_generation.py) | Expands zone grid → 128×128 tilemap with `TILE_*` integer IDs |
| [`systems/zone_planning.py`](../systems/zone_planning.py) | `ZonePlanner` — assigns zone roles to 16×16 grid per room |
| [`systems/world_generation.py`](../systems/world_generation.py) | `World`, `Biome`, `RoomNode` dataclasses; `WorldGenerator` |
| [`systems/megamap.py`](../systems/megamap.py) | `build_megamap()` — stitches all room tilemaps into one unified grid |
| [`systems/tilemap_streaming.py`](../systems/tilemap_streaming.py) | LRU cache for tilemaps; lazy-loads rooms on demand (max 50 in memory) |
| [`config/physics_constants.py`](../config/physics_constants.py) | `TILE_SIZE=32`, `TILES_PER_ZONE=8`, `ROOM_WIDTH_TILES=128` |
| [`data/missions.json`](../data/missions.json) | Mission definitions with `region` → biome mapping, room counts, shapes |
| [`game/hub_manager.py`](../game/hub_manager.py) | `HubDefinition` with forced `biome_theme` per hub |
| [`demo_game.py`](../demo_game.py) | Main render loop — tile draw calls at lines 3312–3472 |
| [`assets/generate_placeholder_tiles.py`](../assets/generate_placeholder_tiles.py) | Script to regenerate the biome placeholder tiles |
