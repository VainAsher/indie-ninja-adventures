## What changed

<!-- One-sentence summary -->

## Why

<!-- Problem or objective. Link issue/plan if available. -->

## How

<!-- Implementation approach and important tradeoffs. -->

## Plan linkage

- plan_id: <!-- required when tied to plan work, e.g. P0-10; otherwise n/a -->
- docs_impact: <!-- required: none | low | medium | high -->
- archive_action: <!-- required: none | create | update -->

## Testing done

```text
# Include exact commands and relevant output excerpts
```

## Checklist

- [ ] Version parity unaffected or validated (`python tools/check_version_sync.py`)
- [ ] Docs freshness checked (`python tools/check_docs_freshness.py --emit-report`)
- [ ] Java tests/build run when Java changed
- [ ] Python tests run when Python changed
- [ ] `docs/CHANGELOG.md` updated for user-visible behavior
- [ ] Active plan document updated for completed work
