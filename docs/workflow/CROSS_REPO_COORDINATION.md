---
doc_type: workflow
status: living
owner: core-team
last_updated: 2026-04-21
version_anchor: v0.11.71
---

# Cross-Repo Coordination Workflow

Workflow for coordinating changes across game, launcher, feedback, and pipeline repos.

## Control-Tower Rule

`VainAsher/indie-ninja-pipeline` is the master planning and coordination repo.

- Planning authority: pipeline
- Implementation authority: source repos
- Public intake authority: feedback
- Player delivery authority: launcher + game releases

## Trigger Conditions

Run this workflow when any change affects more than one repo, including:

- release automation or payload contract updates
- feedback intake, labels, or triage routing updates
- launcher behavior coupled to game release changes
- player-facing comms that depend on internal implementation state

## Canonical Coordination Loop

1. Identify all touched repos and expected outputs.
2. Open or update the coordinating pipeline issue.
3. Declare ownership per repo (who changes what).
4. Confirm event contract impact before code changes.
5. Implement per-repo changes with linked references.
6. Validate end-to-end behavior.
7. Close with release/user communication updates.

## Required Coordination Artifacts

- Planning issue in pipeline repo
- Linked implementation issue/PR in source repo(s)
- Linked feedback issue(s) when player-reported
- Release note entry if user-facing behavior changed

## Event Contract Checks

Before shipping cross-repo release changes, verify:

- `game-release` payload shape matches consumer expectations
- required secrets (`CROSS_REPO_PAT`) exist and are scoped correctly
- failure path is defined (manual fallback issue or step)

## Done Criteria

- [ ] Pipeline coordination issue updated and closed
- [ ] Repo ownership and boundaries respected
- [ ] Contract-impact check completed
- [ ] End-to-end validation evidence recorded
- [ ] Player-facing notes/feedback updates complete

## Failure Path

If any repo dependency is unowned or unverified:

1. Stop release-facing rollout.
2. Mark coordination issue blocked.
3. Assign owner and unblock plan.
4. Re-run end-to-end validation before merge/tag.

## References

- [OPERATING_RHYTHM_AND_HABITS.md](OPERATING_RHYTHM_AND_HABITS.md)
- [../operations/CROSS_REPO_CONTROL_TOWER_HANDOVER.md](../operations/CROSS_REPO_CONTROL_TOWER_HANDOVER.md)
- [../operations/PYGAME_MIGRATION_HANDOVER.md](../operations/PYGAME_MIGRATION_HANDOVER.md)
