---
doc_type: plan
status: implementing
owner: core-team
last_updated: 2026-04-27
version_anchor: v0.12.08
slices_done: S0, S1, S2, S3, S4
slices_remaining: S5, S6, S7, S8
---

# PLAN — Visual World System
## Autotile · Decoration · Parallax · Terrain Features · Hot-Reload

**Created:** 2026-04-28 | **Codebase version:** v0.12.08 | **Next release target:** v0.12.09

## Slice Status

| Slice | Status | Commit |
| --- | --- | --- |
| S0 — Visual Config + Hot-Reload | **DONE** | `1627d82` |
| S1 — Platform Cap/Join Variants | **DONE** | `3e8a8d0` |
| S2 — Biome Audit + Naming | **DONE** | `3e8a8d0` |
| S3 — Parallax Renderer | **DONE** | `78c4b57` |
| S4 — Decoration Layer | **DONE** | `1349736` |
| S5 — Biome → World Region Wiring | PENDING — classify protocol impact before coding | — |
| S6 — Zone Template Library | PENDING — replay=BREAKING, bundle with S7+S8 | — |
| S7 — Feature Placer | PENDING — replay=BREAKING | — |
| S8 — Terrain Smoothing | PENDING — replay=BREAKING | — |

**S5 stop condition:** `WorldGraph.biome` field persistence in PostgreSQL must be classified (additive schema change vs. ignored field) before S5 code is written.

---

## Goal

Transform world generation and rendering from a single structural tile grid with placeholder colouring into a layered visual system: biome-aware autotile terrain, platform cap/join variants, a visual decoration pass, a three-layer parallax background, richer zone-expansion templates, and biome-specific structural features — all hot-reloadable via DevConsole without a JAR restart.

---

## Player-Facing Impact

Rooms read as distinct places rather than differently-coloured versions of the same skeleton. Caves feel enclosed and dripping. Dungeons feel constructed and maze-like. Forests feel open and layered. Platform edges are readable at a glance. Depth is visible as the camera moves. Every structural change is seed-deterministic.

---

## Canonical Docs Consulted

- `docs/systems/WORLD_GEN.md`
- `docs/systems/RENDERING.md`
- `docs/dev/TILED_SETUP.md`
- `docs/workflow/TASK_INTAKE_AND_IMPLEMENTATION_BRIEF.md`
- `docs/workflow/READY_DONE_WORKFLOW.md`
- `docs/workflow/COMPATIBILITY_AND_MIGRATION_WORKFLOW.md`

---

## What Already Exists (do not re-implement)

| System | Status |
|---|---|
| Terrain autotiling | Done — `AutotileResolver` + `BlobTileSet` + `shadow_ascent_tiles.json` live in `ChunkRenderer.loadBlobTiles()` |
| Biome → blob_set wiring | Done — `BlobTileSet.biomeFromSeed()` + `loadBlobTiles(biomeIndex)` parameter |
| 5 named biomes | Done — `BIOME_EARTH/GRASS/SNOW/SAND/STONE` in `BlobTileSet`, blob_sets 0/2/4/6/8 |
| 7 unused blob_sets | Loaded but unreferenced — sets 1/3/5/7/9/10/11 available for expansion |
| DevConsole + `register()` | Done — `reload_content` and `reload_anims` establish the hot-reload pattern |
| `EntityPlanner` entity placement | Done — enemies, pickups, NPCs, boss, portals, platforms |
| Lantern vignette overlay | Done — `ChunkRenderer.renderVignette()` |

---

## New Render Pass Order

```
BEFORE                          AFTER
──────────────────────────      ──────────────────────────────────────
terrain tiles                   parallax layer 1 (far,  0.10x scroll)
entities                        parallax layer 2 (mid,  0.25x scroll)
HUD / vignette                  parallax layer 3 (near, 0.50x scroll)
                                decoration tiles (visual only, no collision)
                                terrain tiles
                                entities
                                HUD / vignette
```

---

## Compatibility Matrix

| Slice | Replay | Save | Protocol | Notes |
|---|---|---|---|---|
| S0 config + hot-reload | no | no | no | client-only |
| S1 platform caps | no | no | no | rendering only |
| S2 biome naming | no | no | no | naming only |
| S3 parallax renderer | no | no | no | client-only |
| S4 decoration layer | no | no | no | generated client-side from seed |
| S5 biome → region wiring | no | no | additive | biome field in room metadata |
| S6 zone templates | **BREAKING** | no | no | changes tile grid output |
| S7 feature placer | **BREAKING** | no | no | changes tile grid output |
| S8 terrain smoothing | **BREAKING** | no | no | changes tile grid output |

S6–S8 must be documented as replay-breaking at the version they ship. Bundle all three into one version bump to minimise the number of replay-break events.

---

## Slice Details

---

### S0 — Visual Config + DevConsole Hot-Reload

**Goal:** All tunable visual params live in JSON from day one. Three DevConsole commands give immediate in-session feedback without a JAR restart.

**New files:**
- `assets/visual/biomes.json` — biome id, blobSetIndex, parallaxSet ref, decoRuleSet ref, zone template weights (consumed by S6), feature list (consumed by S7)
- `assets/visual/parallax.json` — per-biome parallax layer definitions (scroll factors, texture paths, tint)
- `assets/visual/deco_rules.json` — per-biome decoration probability tables (ceiling/wall/floor edge probs, tile offset)

**New DevConsole commands (registered in `GameScreen`):**
```
reload_visual                re-reads all three JSONs, re-applies biome config to
                             current room tiles + logs summary of loaded entries

set_biome <name|index>       force-sets the current room's biome, rebuilds terrain
                             tiles via ChunkRenderer.loadBlobTiles(); resets deco
                             grid when S4 is live

regen_room [seed]            re-runs room visual generation with current biome params
                             (decoration grid when S4 live; scaffolded as no-op until then)
```

**Changes:**
- `GameScreen` — register three commands in `show()` referencing `blobTileSet`, `chunkRenderer`, and current room grid
- No new Java classes required for S0 — parse JSON directly with libGDX `JsonReader` in command handlers

**Risk:** none. Client-only. Commands are no-ops or log-only for features not yet built (S3/S4/S6).

**Tests:** `VisualConfigParseTest` — assert all three JSONs parse without exception, biome entries match `BlobTileSet` constants, required fields present.

---

### S1 — Platform Cap/Join Variants

**Goal:** Platform tiles show left-cap / middle / right-cap / isolated variants instead of always role=0.

**Changes:**
- `BlobTileSet` — add `getPlatformFrame(boolean leftNeighbour, boolean rightNeighbour)` overload; selects role variant based on horizontal adjacency
- `ChunkRenderer.loadBlobTiles()` — pass left/right tile values when tile is PLATFORM

**Risk:** none. Rendering only. Falls back to existing isolated variant if role absent.

**Tests:** `BlobTileSetPlatformCapTest` — assert correct variant for isolated / left-end / right-end / middle configurations across all 5 biomes.

---

### S2 — Biome Audit + Unused Blob_set Naming

**Goal:** Confirm biome index flows end-to-end. Name the 7 unused blob_sets for future use.

**Changes:**
- `BlobTileSet` — add constants for unused sets (e.g. `BIOME_EARTH_ALT`, `BIOME_GRASS_ALT`, `BIOME_STONE_ALT`, `BIOME_SPIRIT`, `BIOME_HUB`)
- `GameScreen` — confirm `biomeFromSeed()` is called consistently when loading room tiles

**Risk:** none. Naming only. No generation changes.

**Tests:** `BlobTileSetBiomeIndexTest` — assert all 12 blob_sets are reachable by index, fallback non-null for each.

---

### S3 — Parallax Renderer

**Goal:** Three-layer parallax background scrolls behind all gameplay content, per-biome content defined in `parallax.json`.

**New class:** `ParallaxRenderer.java` (rendering package)

```java
// Core API
void loadBiome(String parallaxSetId, FileHandle assetRoot)
void render(SpriteBatch batch, GameCamera camera)
void dispose()
```

Each layer: tiling `TextureRegion`, scroll multiplier, vertical anchor. On `render()`, each layer draws a tiling strip offset by `camera.x * scrollMultiplier`. Falls back to a coloured gradient placeholder strip when texture file absent.

**Changes:**
- `GameScreen` — add `ParallaxRenderer parallaxRenderer` field; load on room entry; render before terrain pass
- `parallax.json` consumed here

**Risk:** **Performance** — three additional `SpriteBatch` draw calls per frame at 60 Hz. Each layer is 2–3 tiling quads. Confirm frame time remains under ~12 ms after S3 lands (4 ms margin to 16 ms at 60 Hz). If not, redesign as a single pre-baked background texture per biome.

**Tests:** `ParallaxLayerScrollTest` — assert layer X offset = `camera.x * multiplier` for each layer at a set of camera positions.

---

### S4 — Decoration Layer

**Goal:** A second `byte[128][128]` decoration grid generated client-side from `roomSeed + biomeIndex`. Rendered as a visual-only pass immediately before terrain. No collision, no wire traffic.

**New class:** `DecorationGenerator.java` (world package)

```java
// Core API — deterministic from seed + biome
static byte[][] generate(byte[][] terrainGrid, long roomSeed, int biomeIndex,
                         DecoRuleSet rules)
```

**Generation rules (per biome, from `deco_rules.json`):**
- For each SOLID tile with AIR directly above: roll `ceilingProb` → place ceiling deco in air tile above (stalactite, drip, root hang, cobweb, etc.)
- For each SOLID tile with AIR to left or right: roll `wallProb` → place wall deco in adjacent air tile
- For each SOLID tile at ground surface: roll `floorEdgeProb` → place floor-edge deco (moss, rubble, root tangle)
- Never place decoration where `WorldGenerator.collectGroundPositions()` would return a spawn point

**Changes:**
- `ChunkRenderer` — add `TextureRegion[][] decoMap`; `loadDecoMap(byte[][] decoGrid, DecoRuleSet rules)`; second render pass before terrain
- `GameScreen` — call `DecorationGenerator.generate()` on room load; pass result to `ChunkRenderer.loadDecoMap()`
- `deco_rules.json` consumed here
- `regen_room` DevConsole command becomes functional

**Risk:** `decoGrid` must **never travel over the wire**. Generated client-side only. If a future multiplayer feature proposes syncing it, stop and classify as protocol change.

**Tests:** `DecorationGeneratorTest` — assert (a) deterministic from seed, (b) no deco on solid tile, (c) no deco at valid spawn position, (d) count within expected range per biome.

---

### S5 — Biome → World Region Wiring

**Goal:** `WorldGraph` room clusters carry a canonical biome. Dungeon rooms → STONE. Forest rooms → GRASS. Cave rooms → EARTH. Hub → HUB. Biome index flows to `ChunkRenderer` and `DecorationGenerator` at room load.

**Changes:**
- `WorldGraph` — add `biome` field to room metadata
- `GameScreen` — read room biome from `WorldRoomDescriptor`; pass to `loadBlobTiles()` and `DecorationGenerator.generate()`
- `biomes.json` consulted for biome→blobSetIndex mapping

**Risk:** If `biome` field in room metadata is persisted in PostgreSQL world graph JSONB, this is an **ADDITIVE** schema change. Classify before coding S5 if persistence is involved.

**Tests:** `WorldGraphBiomeAssignmentTest` — assert contiguous clusters share a biome; hub rooms always get hub biome; biome transitions at region boundaries only.

---

### S6 — Zone Template Library

**Goal:** Replace single fixed output per zone role with a pool of named 8×8 tile patterns. `expandZone()` picks one per zone using `roomSeed + zonePosition + biomeIndex`.

**New class:** `ZoneTemplateLibrary.java` (world package)

```java
static byte[][] pick(byte zoneRole, int biomeIndex, Random rng)
```

**Platform zone (PLAT) template pool:**
```
full_bar        — full width, middle row (current behaviour)
left_ledge      — short bar, left-aligned
right_ledge     — short bar, right-aligned
centre_island   — short bar, gap either side
step_left       — ascending 3 tiles from left
step_right      — ascending 3 tiles from right
split           — two short bars with gap between
double_ledge    — two bars at different heights
```

**Solid zone (FILL) template pool:**
```
full            — entire zone solid (current behaviour)
arch            — solid with arch carved out        [dungeon weight high]
pillar          — 2-wide column, rest air            [cave/dungeon]
overhang        — solid top half + lip               [cave]
tooth           — pointed bottom edge (stalactite)   [cave]
l_block         — L-shaped fill                      [any]
steps           — solid staircase shape              [dungeon]
hollow          — solid perimeter, air interior      [dungeon]
```

**Biome weights** defined in `biomes.json` under `zoneTemplateWeights`. `ZoneTemplateLibrary.pick()` uses a weighted random selection seeded deterministically.

**Changes:**
- `RoomGenerator.expandZone()` — delegate to `ZoneTemplateLibrary.pick()` for FILL and PLAT roles
- `biomes.json` `zoneTemplateWeights` block consumed here

**Risk:** replay=**BREAKING**. Any change to `expandZone()` changes tile grid output, changing collision surfaces, desyncing replays from ≤S5 versions. Document at version boundary.

**Tests:** `ZoneTemplateLibraryTest` — each role+biome combination returns valid pattern, no out-of-bounds tiles, connectivity check passes for all templates.

---

### S7 — Feature Placer

**Goal:** Named multi-zone structural features placed after zone expansion, before blob variation. 1–3 features per room, biome-specific, validated against door path connectivity.

**New class:** `FeaturePlacer.java` (world package)

```java
static void place(byte[][] grid, byte[][] zones, int biomeIndex,
                  long roomSeed, Collection<String> neighborDirs)
```

**Cave features:** stalactite column, underground pool, cave bridge
**Dungeon features:** stone pillar pair, raised dais, arch gate
**Forest features:** tree trunk, root tangle, branch cluster
**Hub features:** decorative pillar pair, water feature, gate arch

Each feature is a named tile stamp. Placement validates via `ZonePlanner.checkConnectivity()` — reverts if doors are blocked.

**Changes:**
- `RoomGenerator.generate()` — call `FeaturePlacer.place()` after `expandZone()` loop, before `addBlobVariation()`
- `biomes.json` `features` array consumed here

**Risk:** replay=**BREAKING**. Bundle with S6 into same version bump.

**Tests:** `FeaturePlacerTest` — features don't block door paths, count within range, features don't overlap each other, connectivity maintained.

---

### S8 — Terrain Smoothing (cave biomes only)

**Goal:** Single cellular automata pass over FILL zones in cave/earth biomes. Removes isolated single-tile pillars and jagged grid-aligned edges for more organic surfaces.

**Rules:**
- SOLID tile with fewer than 3 SOLID neighbours → AIR (remove isolated tile)
- AIR tile surrounded by 5+ SOLID neighbours → SOLID (fill small pockets)
- Applied only to EARTH and EARTH_ALT biomes

**Changes:**
- `RoomGenerator` — add static `smoothCaveTerrain(byte[][] grid, int biomeIndex)` method; call after `FeaturePlacer.place()`, before `tagClimbableSurfaces()`

**Risk:** replay=**BREAKING**. Bundle with S6/S7 into same version bump. Dungeon/forest/hub biomes unaffected — sharp edges are correct for those.

**Tests:** `TerrainSmoothingTest` — isolated solid tiles removed, small air pockets filled, boundary tiles never modified, dungeon biome grid unchanged.

---

## Combined Test List

| Test class | Slice | What it covers |
|---|---|---|
| `VisualConfigParseTest` | S0 | All three JSONs parse, required fields present |
| `BlobTileSetPlatformCapTest` | S1 | Cap/join/isolated selection across 5 biomes |
| `BlobTileSetBiomeIndexTest` | S2 | All 12 blob_sets reachable, fallback non-null |
| `ParallaxLayerScrollTest` | S3 | Layer offset = camera.x × multiplier |
| `DecorationGeneratorTest` | S4 | Deterministic, no solid overlap, no spawn overlap, count range |
| `WorldGraphBiomeAssignmentTest` | S5 | Region→biome consistency |
| `ZoneTemplateLibraryTest` | S6 | Valid patterns, connectivity safe |
| `FeaturePlacerTest` | S7 | No door block, count range, no overlap |
| `TerrainSmoothingTest` | S8 | Isolated tiles removed, boundaries safe |

---

## Docs to Update on Completion

| Doc | Trigger |
|---|---|
| `docs/systems/WORLD_GEN.md` | S6/S7/S8 — add decoration layer, feature placer, smoothing to runtime flow |
| `docs/systems/RENDERING.md` | S3/S4 — add parallax + decoration to render pass order |
| `docs/dev/TILED_SETUP.md` | S4 — note decoration tiles are generated, not Tiled-authored |
| `docs/CHANGELOG.md` | S3 or S4 — first player-visible change entry |
| `docs/CURRENT_STATE.md` | Each slice on ship — compatibility flags |

---

## Rollback Plan

S0–S4: client JAR revert only. No server changes, no schema migrations.

S5: if biome field is persisted in PostgreSQL, a schema version bump is required. Rollback = schema downgrade or field ignore. Classify before writing S5 code.

S6–S8: client + server JAR revert. Replays from the version these ship in are incompatible with prior versions — document at version boundary. No save or protocol rollback needed.

---

## Escalation Conditions

- S5 biome field persisted in DB → stop, classify schema change before coding
- S3 parallax pushes frame time above ~12 ms → redesign as pre-baked background texture
- S4 `decoGrid` proposed as a wire field → stop, classify as protocol change
- Any S6–S8 change found to affect zone connectivity gate logic → stop, rerun connectivity audit before shipping
