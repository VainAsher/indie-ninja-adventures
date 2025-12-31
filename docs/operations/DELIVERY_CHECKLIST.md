# Delivery Checklist (push-ready)

## Scope Freeze Focus
- Modes: Campaign, Arcade, Sandbox.
- Vertical slice: movement/jump/dash/crouch, pickups/hazards, exit/win flow, HUD/menus, camera, procedural/static toggle.

## Before Pushing to GitHub
- [ ] Ensure `python -m pytest` (or `python run_tests.py`) passes locally with `SDL_VIDEODRIVER=dummy`.
- [ ] Commit `requirements.txt`, docs updates, and operations folder.
- [ ] Verify `demo_game.py` runs in static and `--procedural --seed 12345` modes.
- [ ] Confirm `user_data/` paths are writable or override with `NINJADASH_USER_DATA`.
- [ ] Lint/logs: no noisy stdout on import; logger output is acceptable.

## CI/CD Artifacts to Include
- `.github/workflows/ci.yml` based on `docs/operations/CI_CD_PLAN.md` (to add after repo is on GitHub).
- Test logs/junit optional for PR visibility.

## Follow-up Tasks (post-push)
- Add `--headless` flag to demo for CI smoke.
- Expand tests to cover new systems (inventory/trading/missions/enemies/autotiling).
- Wire vertical-slice acceptance tests for Campaign/Arcade/Sandbox.
