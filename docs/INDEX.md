# Documentation Index

Vain Asher Gaming's: Indie Ninja Adventures — v0.7.1

Last updated: 2026-03-28

---

## Start here

| Document | Purpose |
| --- | --- |
| [OVERVIEW.md](OVERVIEW.md) | Project vision, modes, controls, tech stack, architecture summary |
| [TASK_LIST.md](TASK_LIST.md) | **Living task list** — what to work on now, next, and backlog |
| [ROADMAP.md](ROADMAP.md) | Milestone definitions and completion status |
| [HANDOVER.md](HANDOVER.md) | Full handover for someone new to the project |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [QUICK_START.md](QUICK_START.md) | Concise play guide and controls |

---

## System documentation

Each file covers a single system: rationale, architecture, key classes, usage, and how to extend it.

| Document | System |
| --- | --- |
| [systems/AUDIO.md](systems/AUDIO.md) | AudioManager, SFX events, volume wiring, how to add sounds |
| [systems/CAMPAIGN.md](systems/CAMPAIGN.md) | Regions, missions, ability gates, portal placement, save/load |
| [systems/COMPANIONS.md](systems/COMPANIONS.md) | Yin & Yang orbital orbs — story presence, visual design, API |
| [systems/ENDINGS.md](systems/ENDINGS.md) | Moral choice (SAVE/DESTROY), ending state machine, hub final state |
| [systems/LOOT.md](systems/LOOT.md) | Drop tables, rarity tiers, deterministic seeded generation |
| [systems/MECHANICS.md](systems/MECHANICS.md) | All player mechanics — tuning values, gating, interactions |
| [systems/MODDING.md](systems/MODDING.md) | Plugin API — ModInterface, GameContext, custom entities/components |
| [systems/PERFORMANCE.md](systems/PERFORMANCE.md) | O1–O10 optimizations, spatial hash, surface caching, guidelines |
| [systems/RENDERING.md](systems/RENDERING.md) | Camera, animation, sprites, particles, HUD, render order |
| [systems/REPLAY.md](systems/REPLAY.md) | Input pipeline — live/record/replay, file format, determinism |
| [systems/SETTINGS.md](systems/SETTINGS.md) | All settings keys, wiring status, how to add a setting |
| [systems/WORLD_GEN.md](systems/WORLD_GEN.md) | Procedural generation hierarchy, biomes, zones, autotiling |

---

## Reference

| Document | Purpose |
| --- | --- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Design principles, event-driven pattern, component ECS |
| [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md) | Full API reference for all systems |
| [WORLD_GENERATION.md](WORLD_GENERATION.md) | Extended world generation reference |

---

## Operations

| Document | Purpose |
| --- | --- |
| [UAT_SUITE.md](UAT_SUITE.md) | User acceptance test checklist (result columns need filling) |
| [operations/CI_CD_PLAN.md](operations/CI_CD_PLAN.md) | CI/CD pipeline |
| [operations/BUG_BACKLOG.md](operations/BUG_BACKLOG.md) | Bug tracking |
| [operations/DELIVERY_CHECKLIST.md](operations/DELIVERY_CHECKLIST.md) | Release checklist |

---

## Reviews and planning

| Document | Purpose |
| --- | --- |
| [PLAN_2026-03-28.md](PLAN_2026-03-28.md) | 2026-03-28 gap analysis and approved work plan (Phases 0–5) |
| [reviews/2026-03-25/](reviews/2026-03-25/) | March 2025 deep-dive review, issues, and risks |

---

## Notes

- Wall slide is **active** — light always-on vy clamp when touching a wall. Some older docs incorrectly say it is disabled.
- Boss system is wired into the mission flow but boss AI behaviour is not implemented.
- F9 opens the debug ability toggle menu in-game (password: `devmode`).
