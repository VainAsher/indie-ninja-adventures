---
doc_type: workflow
status: living
owner: core-team
last_updated: 2026-04-18
version_anchor: v0.11.60
---

# Save, Schema, and Compatibility Workflow

Reference documents:
- [version.json](../../version.json)
- [docs/dev/JAVA_ARCHITECTURE.md](../dev/JAVA_ARCHITECTURE.md)
- [docs/plans/implementing/PLAN_SHADOW_ASCENT.md](../plans/implementing/PLAN_SHADOW_ASCENT.md)
- [docs/CHANGELOG.md](../CHANGELOG.md)

Workflow for protecting save, replay, schema, and protocol compatibility as the project evolves.

## Rules

1. Compatibility assumptions must be explicit.
2. Any change touching persisted data, schema, replay format, network protocol, or runtime serialization must be reviewed through this workflow.
3. Breaking compatibility without documentation is forbidden.
4. If compatibility status is unknown, treat the change as risky until proven otherwise.

## Compatibility Categories

- save-compatible: existing saves continue to load correctly
- replay-compatible: existing replays still play back correctly
- protocol-compatible: mixed-version clients/servers remain safe where supported
- schema-compatible: existing structured data remains valid without migration
- breaking: one or more of the above requires migration, version gate, or reset

## Trigger Conditions

Run this workflow when:
- persistence shape changes
- JSON/schema/message contracts change
- serialization/deserialization logic changes
- offline mode introduces new local storage rules
- protocol fields are added/removed/reinterpreted

## Canonical Loop

1. Identify the compatibility surfaces touched.
2. Classify the change for save, replay, protocol, and schema compatibility.
3. Decide whether migration is required.
4. Decide whether version bump or version gate is required.
5. Update docs and changelog notes for any breaking behavior.
6. Validate migration/load/playback behavior where applicable.

## Documentation Minimum

Every risky compatibility change must record:
- compatibility classification
- migration required or not
- rollback/restore plan
- user-visible impact
- version anchor

## Done Criteria

- [ ] Compatibility surfaces identified
- [ ] Classification recorded
- [ ] Migration need decided
- [ ] Version bump/gate need decided
- [ ] Docs/changelog updated for breaking changes
- [ ] Validation run for changed compatibility surface

## Failure Path

If compatibility impact cannot be determined quickly:

1. Stop release-facing progress on the change.
2. Mark compatibility as unknown-risk.
3. Reduce scope or isolate the change behind a flag.
4. Do not merge as a routine low-risk change.

## Related Workflows

- [ARCHITECTURE_AND_SPEC_SYNC.md](ARCHITECTURE_AND_SPEC_SYNC.md)
- [DECISION_RECORD_WORKFLOW.md](DECISION_RECORD_WORKFLOW.md)
