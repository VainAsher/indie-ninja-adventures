---
doc_type: dev_analysis
status: living
owner: core-team
last_updated: 2026-05-02
version_anchor: v0.13.28
source: https://github.com/runevision/LayerProcGen
---

# LayerProcGen: Concepts and Applicability to Shadow Ascent

A technical analysis of the LayerProcGen framework (C#, Unity) and where its
principles can concretely improve Shadow Ascent's Java worldgen pipeline.

---

## What LayerProcGen Is

LayerProcGen is not a generation algorithm. It is a **streaming dependency
executor** for spatial data. It solves one specific problem very well: how to
generate an infinite world in chunks where each layer depends on data from
neighbouring chunks in lower layers, without generating everything eagerly or
losing coherence at chunk boundaries.

The framework handles scheduling, dependency resolution, and chunk lifecycle.
The developer writes generation logic in isolated `Create(level, destroy)` calls
and declares inter-layer relationships with an explicit padding distance. The
framework guarantees that when a chunk is created, all its dependencies are
already materialized within that padding.

---

## Core Concepts

### Chunks and Layers

A **Layer** is a type of spatial data (`ChunkBasedDataLayer<L, C>`). A
**Chunk** is one tile of that layer's grid. Each layer has its own chunk size
in world units — a biome-planning layer might use 1600-unit chunks while a
room-detail layer uses 100-unit chunks. This size difference is the mechanism
for multi-scale planning in a single pipeline.

Every chunk has one entry point: `Create(int level, bool destroy)`. When
`destroy` is false, generate. When true, release resources. Recycled chunks
live on a `RollingGrid` (a 2D ring buffer) so memory stays bounded as the
player moves through a large world.

### DAG of Dependencies

Layers are wired together in an acyclic graph (DAG). Each dependency is
declared with an **effect distance** — the maximum radius in world space at
which data from a lower layer can influence data in the current layer. This is
declared once per dependency pair via `AddLayerDependency(layer, effectDistance)`.

The framework's core invariant: when your chunk `Create` runs, every lower-layer
chunk within `effectDistance` of your chunk's bounds is already populated. You
can sample lower layers freely within that radius without out-of-bounds risk.

### Effect Distance and the Correctness Invariant

Effect distance is the central design constraint. Declaring it too small
produces subtle coherence bugs at chunk boundaries (data influences output
beyond the declared radius, causing seam artefacts). Declaring it too large
wastes memory and computation.

The rule: **effect distance must equal or exceed the maximum world-space distance
at which any pixel of output in your chunk is influenced by any pixel of input
from the lower layer.** This must hold by construction — there is no runtime
check.

### Multi-Scale Planning

Different layers can use vastly different chunk sizes. The canonical example:

- A 1600-unit `BiomePlanner` layer decides biome boundaries and region shape.
- A 400-unit `RegionContentLayer` reads biome data and places landmarks.
- A 100-unit `RoomDetailLayer` reads landmark data to select authored room templates.

The 1600-unit chunks are generated first (they have no dependencies), then 400,
then 100. Each layer only needs to be populated one step ahead of what the focus
point (player position) requires. The framework's `TopLayerDependency` walks the
DAG upward to determine which lower chunks need to be ready before the top-level
active window can expand.

### TopLayerDependency and the Active Window

`TopLayerDependency` is the entry point from game code. It declares the "focus
point" (typically the camera or player position) and the "active window"
(the viewport or preload radius). All chunk generation flows from this focus.
The `LayerManager` background thread generates chunks ahead of the focus point
using the DAG to determine traversal order.

### RandomHash

LayerProcGen's `RandomHash` provides deterministic per-chunk seed derivation
without a global state machine. Hash inputs are typically `(layerId, chunkX, chunkY)`.
This is chunk-local determinism — each chunk's seed is independent, reproducible,
and unaffected by the order in which other chunks are generated.

---

## Shadow Ascent's Current Worldgen Architecture

The existing pipeline is already layered by intent; the layers are described in
`docs/systems/WORLD_GEN.md` and implemented in `com.indieniinja.world`.

| Layer | Java owner | What it does |
| ----- | ---------- | ------------ |
| Progression graph | `WorldProgressionGenerator` | Macro narrative beats: hubs, dungeons, grants, requirements |
| Section layout | `HybridLayoutPlanner` | Assigns authored section templates to progression nodes |
| Socket/anchor contracts | `SocketAnchorPlanner` | Resolves section connections to directed contracts |
| Validation / repair | `GenerationValidationPlanner` | Records `critical_path_transition_debt`, blocked nodes, etc. |
| Room graph | `WorldGraph` / `WorldGenerator` | Per-room type assignment and neighbour topology |
| Zone planning | `ZonePlanner` | 16x16 zone role grid per room |
| Tile synthesis | `RoomGenerator` / `ZoneTemplateLibrary` | 8×8 zone patches → 128×128 tile grid |
| Postprocess | `AbilityLayer`, `PuzzleLayer`, `EntityPlanner` | Gates, puzzles, enemies, portals, pickups |
| Export | `MegamapStitcher`, `WorldgenLabAnalyzer` | Snapshot for tooling and CI diffs |

The pipeline is eager and graph-scoped: all rooms for a seed are generated at
world-init time and cached. Streaming (generating rooms on demand as the player
approaches) has not been implemented yet.

### Known Gaps

1. **`critical_path_transition_debt`** — socket mismatches between adjacent
   sections produce `needs_transition` contracts on mandatory edges. The
   validation layer records them but does not yet repair them. Quality score
   is penalised by `transitionDebtPenalty`.

2. **Single-scale section planning** — `HybridLayoutPlanner` operates at one
   spatial granularity. There is no layer above sections that plans regions
   before sections, or below sections that plans rooms before tiles.

3. **No streaming** — the entire world graph is generated at startup. This
   limits world size and makes open-world expansion a significant rewrite risk.

4. **Seam coherence is undeclared** — when two sections connect, there is no
   explicit contract specifying the maximum distance from the seam at which
   one section's content can influence the other's tile output. Socket
   compatibility covers topology but not spatial influence distance.

---

## Where LayerProcGen Principles Apply Directly

### 1. Formalise the Effect Distance for Section Seams

**Current situation:** Socket compatibility ensures doors align. But tile-level
content (platforms, hazards, entity placement) near a seam has no declared
influence radius. A room template placed close to a section boundary can
visually or mechanically interact with the adjacent section's rooms in ways
that are discovered by playtesting rather than by the pipeline.

**LayerProcGen principle:** Every inter-layer dependency must declare an effect
distance. Influence beyond that distance is a bug, not a feature.

**Concrete improvement:** For each socket contract, declare a **seam clearance
zone** — the tile distance from the section boundary within which authored
content must not place hazards, vertical drops, or enemy spawns that would
create unplayable junctions. The `SocketAnchorPlanner` is the right layer to
emit this as a resolved constraint, which `EntityPlanner` and `AbilityLayer`
respect when placing content near boundary rooms.

This would directly reduce `critical_path_transition_debt` cases where a
`needs_transition` contract is generated not because of a socket mismatch
but because the content placed near the connection point is incompatible.

### 2. Introduce a Region Planning Layer Above Sections

**Current situation:** `WorldProgressionGenerator` produces a narrative graph
(hub → dungeon → boss). `HybridLayoutPlanner` maps that graph to section
templates on a flat grid. There is no intermediate layer that groups sections
into spatial regions and makes aesthetic decisions (biome tone, density,
verticality, pacing curve) before individual section templates are chosen.

**LayerProcGen principle:** Use a large-chunk layer for decisions that need to
be coherent across many small-chunk regions. The large layer generates first,
providing stable context for finer layers.

**Concrete improvement:** Add a `RegionPlanningLayer` between the progression
graph and `HybridLayoutPlanner`. Each region-plan chunk covers multiple section
footprints and decides:

- Dominant traversal style (horizontal crawl, vertical climb, open arena)
- Hazard flavour within this region (water-heavy, lava-heavy, ice-heavy)
- Pacing curve (dense combat → puzzle relief → boss lead-up)
- Target room-count budget

`HybridLayoutPlanner` then reads region decisions to narrow section template
candidates before selection. This eliminates cases where a `water_depths` section
is selected immediately adjacent to a `sky_cliff` section because the macro
layout only tracks connectivity, not spatial coherence.

This aligns with the roadmap's intent for `SectionTemplateLibrary` biome
filtering — but currently biome assignment is a section-level property, not a
region-level constraint. Moving the decision upward makes it coherent across a
spatial area rather than per-node.

### 3. Adopt Chunk-Local Determinism (RandomHash Pattern)

**Current situation:** Shadow Ascent uses a seed hierarchy (`SeedHierarchy`)
that derives sub-seeds per world, per room, per zone step. This is already
excellent. The architecture is close to LayerProcGen's `RandomHash` philosophy.

**LayerProcGen principle:** Each chunk's seed is derived from `(layer, chunkX,
chunkY)` — no global counter, no order dependency. Adding or removing a chunk
somewhere in the world cannot change the seed of an unrelated chunk.

**Concrete improvement:** Verify that `SeedHierarchy` derivation is
position-based and not generation-order-based. If any sub-seed is derived
from a global counter (e.g. "Nth room created"), that seed changes if room
count changes, making it replay-breaking and generation-order-sensitive.
Switching to `(worldSeed, roomGridX, roomGridY)` as the derivation key (which
is the intent of the current `room.seed` field) would make the pipeline
order-independent in the same way as `RandomHash`.

### 4. Streaming Architecture via RollingGrid-Style Room Lifecycle

**Current situation:** All rooms are generated at world-init and cached in
Redis. This works for the current Act I scope (20–40 rooms) but becomes a
startup penalty and memory ceiling as world size grows.

**LayerProcGen principle:** Chunks are generated on demand as the focus point
(player) approaches, recycled via `RollingGrid` when they move out of range.
The key enabler is that all dependencies for a chunk are guaranteed to be
ready before the chunk `Create` runs.

**Concrete improvement for streaming:** Model the Shadow Ascent generation
pipeline as a LayerProcGen-style DAG even if the streaming infrastructure is
not adopted directly:

1. Define which layers are independent (progression graph — generated once)
   and which are chunk-local (room tiles — can be generated on demand).
2. For each chunk-local layer, define the effect distance from lower layers.
3. Route server-side zone init through `ZoneSimulationLoop.initSimulator()` with
   lazy room generation: generate tile grids for a room only when a player
   first enters its zone, using the declared effect distance to ensure the
   adjacent rooms' tile grids are available.

This does not require adopting the C# framework. It requires applying the same
constraint discipline: every room-generation call must see its neighbours within
the declared effect distance already generated.

The existing Redis tile cache (`RoomTileCache`) is structurally a `RollingGrid`
— it already evicts tile data on LRU. Formalising the effect-distance contract
allows safe lazy generation on top of that cache.

### 5. Repair by Regeneration at the Correct Granularity

**Current situation:** `GenerationValidationPlanner` records repair tiers:
`patch`, `replace`, `regenerate`. The `regenerate` tier implies regenerating
the entire world. For `critical_path_transition_debt`, the documented repair
action is `insert_transition_room` (tier `patch`).

**LayerProcGen principle:** When a chunk fails validation, regenerate only
that chunk and its dependents — not the whole world. The DAG makes the
dependency scope explicit.

**Concrete improvement:** Apply this principle to `critical_path_transition_debt`.
When a transition is needed between two sections:

1. Insert a bridge section at the connection point (narrow the repair to one
   new section node in the layout, not a world re-seed).
2. The bridge section's socket contracts are derived from the two adjacent
   sections' unresolved connection (already available in `SocketAnchorPlan.
   connectionContracts`).
3. Validate only the affected connection contracts after insertion.

This is a contained, section-level repair with no effect on unrelated parts of
the layout. It mirrors how LayerProcGen's chunk regeneration is scoped to the
affected spatial area.

---

## What NOT to Adopt Directly

### C# / Unity Infrastructure

LayerProcGen is a C# framework with Unity integration. Shadow Ascent is Java 21
with a custom ECS. Importing the framework is not possible. All value comes from
adopting the *design principles* not the *implementation*.

### Acyclicity Requirement

LayerProcGen requires a strict DAG — no circular dependencies between layers.
Shadow Ascent's current pipeline is already acyclic (progression → sections →
layout → sockets → validation), so this is not a constraint conflict. However,
if a future feature requires a room to influence progression (e.g. a discovery
unlocks a new narrative branch), that must be modelled as a separate
callback/event layer rather than a cycle in the generation DAG.

### 2D Assumption

LayerProcGen is designed for 2D spatial grids. Shadow Ascent is a 2D
platformer, so this is a natural fit. However, LayerProcGen's chunk coordinate
system assumes continuous world-space; Shadow Ascent's room graph is a logical
graph, not a continuous tile map. The spatial concepts apply, but chunk
boundaries must be mapped to room boundaries rather than world-pixel coordinates.

---

## Alignment with Existing Plans

| Existing plan | LayerProcGen alignment |
| ------------- | ---------------------- |
| `PLAN_LAYERED_HYBRID_WORLD_GENERATOR.md` — "generation should be layered in this order" | Directly mirrors the DAG-of-layers philosophy. Slices 2–9 not yet implemented correspond to the deeper dependency layers (schema versioning, validation gates, repair). |
| `PLAN_WORLDGEN_RUNTIME_ADOPTION.md` — RFC: promote validation to runtime gating | The effect-distance invariant is the mechanism that makes runtime gating safe. Gating a room's generation on its dependencies being ready is exactly `TopLayerDependency`. |
| `PLAN_WORLDGEN_VISION_EXECUTION.md` — traversal contracts, quality scoring v2 | Socket traversal contracts are the seam-level effect-distance declarations described in §1 above. |
| `systems/WORLD_GEN.md` — `critical_path_transition_debt` | Bridge-section repair (§5) is the resolution mechanism the validation layer is waiting for. |

---

## Prioritised Recommendations

These are ordered by ROI against current pain points:

1. **Seam clearance zones (§1)** — formalise effect distance for content near
   section boundaries. Directly reduces transition debt and unplayable
   junctions. Scope: extend `SocketAnchorPlanner` + `EntityPlanner`.

2. **Bridge-section repair for transition debt (§5)** — implement the
   `insert_transition_room` repair action the validation layer already records.
   Use `connectionContracts` as input. Scope: new `TransitionRoomPlanner` class.

3. **Region planning layer (§2)** — add a spatial coherence layer above sections
   to produce biome/pacing consistency across multi-section areas. Scope:
   `RegionPlanningLayer` + extend `HybridLayoutPlanner` to consume it.

4. **Seed derivation audit (§3)** — confirm `SeedHierarchy` room seeds are
   position-keyed not counter-keyed. Low effort, high replay safety value.

5. **Lazy room generation (§4)** — long-term streaming architecture. Only
   worth pursuing after items 1–3 are stable and Act I generation quality is
   verified across the 1–250 seed sweep.

---

## Summary

LayerProcGen's central insight — **declare the spatial radius of every
inter-layer dependency, guarantee it before generation runs, scope repairs to
the affected granularity** — maps directly onto the problems Shadow Ascent's
worldgen is already experiencing: transition debt between sections, seam
incoherence, and whole-world regeneration when a validation check fails.

The framework should be treated as a design pattern source, not an adoption
candidate. The existing `PLAN_LAYERED_HYBRID_WORLD_GENERATOR.md` pipeline
is structurally sound; the missing piece is the explicit effect-distance
discipline and the section-level repair strategy.
