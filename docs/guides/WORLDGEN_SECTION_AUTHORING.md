# Worldgen Section Authoring Guide

Use this guide when adding or editing files under `data/worldgen/sections/`.
It is focused on authored section templates consumed by
`SectionTemplateLibrary`.

## Required shape by kind

### Generic navigable kinds (`key_trial`, `shop_save_loop`, `lock_gate`, etc.)

```json
{
  "id": "forest_key_trial_variant",
  "biome": "forest",
  "kind": "key_trial",
  "footprint": { "gridW": 3, "gridH": 2 },
  "nodeKinds": ["entry", "beat_a", "reward", "shortcut"],
  "edgeRules": [
    { "from": "entry", "to": "beat_a" },
    { "from": "beat_a", "to": "reward" },
    { "from": "reward", "to": "shortcut" }
  ],
  "requiredSockets": ["west_low_walk", "east_mid_jump"],
  "mutableZones": [
    { "x": 8, "y": 12, "w": 16, "h": 6, "role": "enemy_pool" }
  ],
  "anchors": [
    {
      "id": "reward_anchor",
      "kind": "key_reward",
      "phase": "global",
      "localBounds": { "x": 42, "y": 12, "w": 3, "h": 2 },
      "tags": ["critical"],
      "weight": 1.0,
      "quotaGroup": "critical_rewards",
      "minDistance": 0,
      "requires": [],
      "forbids": []
    }
  ]
}
```

### `boss_approach`

`boss_approach` can omit navigation fields in non-strict mode, but full schema
is recommended for consistency and future runtime adoption.

```json
{
  "id": "lantern_boss_approach_variant",
  "biome": "lantern",
  "kind": "boss_approach",
  "footprint": { "gridW": 3, "gridH": 1 },
  "nodeKinds": ["entry", "gauntlet", "boss_door"],
  "edgeRules": [
    { "from": "entry", "to": "gauntlet" },
    { "from": "gauntlet", "to": "boss_door" }
  ],
  "requiredSockets": ["west_mid_jump", "east_mid_jump"],
  "anchors": [
    {
      "id": "boss_door_anchor",
      "kind": "boss_door",
      "localBounds": { "x": 52, "y": 12, "w": 4, "h": 4 }
    }
  ]
}
```

### `hub_home`

`hub_home` also allows navigation-field omissions, but anchors are still
required and full schema is preferred.

```json
{
  "id": "lantern_heights_hub_variant",
  "biome": "lantern",
  "kind": "hub_home",
  "anchors": [
    {
      "id": "service_anchor",
      "kind": "service",
      "localBounds": { "x": 40, "y": 40, "w": 8, "h": 8 }
    }
  ]
}
```

## Socket token grammar

Use: `side_band_traversal[_modifier...]`

- valid examples: `west_low_walk`, `east_mid_jump`, `north_high_climb_bridge`
- invalid examples: `west-low-walk`, `mid_walk`, `portal_mid_jump` (invalid side)

When strict contract mode is enabled (`-Dninja.socketContractStrict=true`),
unknown side/band tokens are rejected.

## Anti-patterns to avoid

- mismatched sockets that force every critical path edge into `needs_transition`
- empty required arrays (`nodeKinds`, `edgeRules`, `requiredSockets`, `anchors`)
- anchors with missing `id` or `kind`
- tiny/placeholder footprints that do not represent actual section intent
- using one template id for materially different layouts (create new ids instead)

## Pre-PR checklist (content-only contributors)

- [ ] File is valid JSON and formatted.
- [ ] `id` is unique and stable.
- [ ] `biome` + `kind` pair is intentional and test-covered if it changes counts.
- [ ] Required arrays are non-empty for navigable kinds.
- [ ] Socket ids follow `side_band_traversal[_modifier...]`.
- [ ] Anchors include at least `id`, `kind`, and valid `localBounds`.
- [ ] `./gradlew.bat :shadowascent:test --tests com.indieniinja.world.sections.SectionTemplateLibraryTest --tests com.indieniinja.world.sections.SectionTemplateVarietyDataTest --no-daemon` passes from `java/`.
