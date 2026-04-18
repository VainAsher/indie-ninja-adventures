---
doc_type: workflow
status: living
owner: design-team
last_updated: 2026-04-18
version_anchor: v0.11.65
---

# Playtest Packet Workflow

Reference documents:

- [DAILY_SMOKE_WORKFLOW.md](DAILY_SMOKE_WORKFLOW.md)
- [FEEDBACK_TRIAGE_WORKFLOW.md](FEEDBACK_TRIAGE_WORKFLOW.md)

Workflow for shipping focused internal or external test builds with structured questions and collection instructions.

## Rules

1. Every playtest build must have a declared purpose.
2. Testers should receive tasks and questions, not only a download.
3. Packet scope should stay narrow enough to produce actionable feedback.
4. Logs, replays, and save data collection instructions must be explicit.

## Packet Minimum

- Build/version
- Focus area
- Known issues
- Session length target
- Required tasks
- Exact questions
- Controls reference
- Log/replay/save submission steps
- Feedback destination

## Canonical Loop

1. Define one primary test goal.
2. Define 2-4 required tasks.
3. Define 3-6 questions tied to that goal.
4. Package the build and support files.
5. Send the packet with submission instructions.
6. Triage returned feedback into the feedback repo or pipeline.
7. Summarize findings into the active plan or loop note.

## Example Focus Areas

- Onboarding clarity
- Mission tracker readability
- Yin/Yang differentiation
- Flow readability
- Boss fairness
- Respawn clarity
- Offline mode reliability

## Done Criteria

- [ ] Packet has a narrow focus
- [ ] Tester tasks are explicit
- [ ] Questions map to the focus area
- [ ] Submission path is clear
- [ ] Returned feedback is triaged into actionable categories

## Failure Path

If feedback returns vague or contradictory:

1. Check whether the packet asked broad questions instead of targeted ones.
2. Review logs/replays before making balance changes.
3. Narrow the next packet to one subsystem or one act slice.

## Known Regression Surfaces

Before shipping a playtest build, run the smoke pair for any system touched this session:

| System touched | Must verify |
| --- | --- |
| `EntityRenderer` / stance / animation | G4 in full — all five movement states, both stances |
| `GameScreen.pollZoneTransition` / `handleSoloPortalTravel` | G5 in full — all six checklist items |
| `PhysicsSystem` / `gravityFrozen` | G3 wall-climb and ledge-hang |
| `SimPlayer` / abilities / `prevLocalAbilities` | G5 step 5 (no spurious ability toasts) |
| `LevelLayout` / room placement | G5 step 1 (no start-room portal) |
| Persistence / `HikariCP` / save shape | G6 |

Reference: `docs/workflow/GOLDEN_PATH_REGRESSION.md`

## Related Workflows

- [FEEDBACK_TRIAGE_WORKFLOW.md](FEEDBACK_TRIAGE_WORKFLOW.md)
- [DEVLOG_AND_MARKETING_CAPTURE.md](DEVLOG_AND_MARKETING_CAPTURE.md)
