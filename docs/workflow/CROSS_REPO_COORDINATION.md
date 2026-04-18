---
doc_type: workflow
status: living
owner: core-team
last_updated: 2026-04-18
version_anchor: v0.11.60
---

# Cross-Repo Coordination Workflow

Reference documents:
- [README.md](../../README.md)
- [docs/CHANGELOG.md](../CHANGELOG.md)
- [docs/DEVLOG.md](../DEVLOG.md)
- [docs/production/decisions.md](../production/decisions.md)

Workflow for keeping game, launcher, feedback, and pipeline repositories aligned when work crosses repository boundaries.

## Rules

1. Multi-repo work must identify repo ownership explicitly.
2. Version references must not drift across repos silently.
3. Public notes must have one owning repo or publication path.
4. Cross-repo dependencies must be called out before release.

## Trigger Conditions

Run this workflow when:
- a game change requires launcher behavior/update
- feedback templates or intake paths must change
- release automation/pipeline behavior must change
- public notes or version references must be updated in more than one repo

## Canonical Loop

1. Identify all repos touched by the change.
2. Assign the owning repo for implementation and the owning repo for public notes.
3. Record required follow-up updates in the other repos.
4. Update version references deliberately.
5. Validate the release path across the affected repos.
6. Close the loop only when linked repos are aligned.

## Ownership Guidance

- game repo: code, runtime behavior, technical docs
- launcher repo: launcher behavior, player guides, GitHub Pages
- feedback repo: public bug/feature intake
- pipeline repo: internal triage, planning, release management

## Done Criteria

- [ ] Affected repos identified
- [ ] Ownership clear
- [ ] Version/reference updates recorded
- [ ] Public notes owner chosen
- [ ] Follow-up actions completed or tracked

## Failure Path

If a release-facing task depends on another repo but no owner is assigned:

1. Stop treating it as single-repo work.
2. Record the missing dependency.
3. Assign the owning follow-up before shipping.

## Related Workflows

- [RELEASE_NOTES_AND_PUBLIC_COMMS.md](RELEASE_NOTES_AND_PUBLIC_COMMS.md)
- [DECISION_RECORD_WORKFLOW.md](DECISION_RECORD_WORKFLOW.md)
