---
doc_type: report
created: 2026-05-03
version_anchor: v0.13.29
---

# Worldgen Seed Sweep — Worst 5 Seeds (seeds 1..50, v0.13.29)

Sweep: `python tools/worldgen_lab.py batch --seeds 50 --rooms 20 --shape BLOB`

Full data: `docs/reports/worldgen/sweep-50-v0.13.29.csv`

## Summary

All 50 seeds fail `overallStatus`. Score range: **60–80**. Median: ~68.

**Root cause:** `critical_path_transition_debt` on Act II+ progression nodes (archive, cathedral, cavern, foundry, spire regions). These regions generate `needs_transition` edges but no section templates exist yet. Act I is fully resolved — seed 420 = `qualityScoreV2=96`, `valid=true`.

This sweep is a **baseline measurement**, not a regression. Failures are expected until Act II section templates are authored.

## Worst 5 Seeds

| Rank | Seed | qualityScoreV2 | socketCompatibility | transitionDebtPenalty | criticalPathVariety | Debt issues |
|------|------|---------------|--------------------|-----------------------|---------------------|-------------|
| 1    | 7    | 60            | 33                 | 75                    | 53                  | 9           |
| 2    | 40   | 61            | 27                 | 67                    | 47                  | 8           |
| 3    | 3    | 63            | 33                 | 67                    | 53                  | 8           |
| 4    | 5    | 64            | 40                 | 56                    | 35                  | 9           |
| 5    | 11   | 65            | 45                 | 63                    | 45                  | 10          |

## Seed 7 — Full Issue List (worst)

| Kind | Scope | Severity |
|------|-------|----------|
| `critical_path_transition_debt` | `archive_region_3->archive_region_3_entry` | error |
| `critical_path_transition_debt` | `archive_region_3_entry->archive_region_3_trial` | error |
| `critical_path_transition_debt` | `archive_region_3_gate->archive_region_3_boss` | error |
| `critical_path_transition_debt` | `archive_region_3_trial->archive_region_3_gate` | error |
| `critical_path_transition_debt` | `cathedral_region_1_entry->cathedral_region_1_trial` | error |
| `critical_path_transition_debt` | `cathedral_region_1_trial->cathedral_region_1_gate` | error |
| `critical_path_transition_debt` | `cavern_region_2->cavern_region_2_entry` | error |
| `critical_path_transition_debt` | `cavern_region_2_gate->cavern_region_2_boss` | error |
| `critical_path_transition_debt` | `cavern_region_2_trial->cavern_region_2_gate` | error |
| `optional_transition_debt` | `cavern_region_2->cavern_region_2_treasure` | warning |

## Next Step

Author section templates for Act II regions (archive, cathedral, cavern) to reduce debt. The sweep should be re-run after each region's templates are complete to track progress toward a passing baseline.
