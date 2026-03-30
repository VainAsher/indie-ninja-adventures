# Label Setup Guide

Run these commands with the GitHub CLI (`gh`) to create all labels in the feedback repo.
Replace `VainAsher/indie-ninja-feedback` with your actual repo if different.

```bash
REPO="VainAsher/indie-ninja-feedback"

# Core type labels
gh label create "bug"          --color "d73a4a" --description "Bug, crash, or broken behaviour"       --repo $REPO
gh label create "feature"      --color "0075ca" --description "New feature or enhancement"             --repo $REPO
gh label create "feedback"     --color "e4e669" --description "General gameplay or UX feedback"        --repo $REPO
gh label create "performance"  --color "f9d0c4" --description "FPS, lag, or loading issues"            --repo $REPO

# Severity / urgency
gh label create "urgent"       --color "b60205" --description "Crash or unplayable — high priority"    --repo $REPO

# System labels
gh label create "multiplayer"  --color "0e8a16" --description "Affects online multiplayer"             --repo $REPO
gh label create "ui"           --color "bfd4f2" --description "Menus, HUD, or launcher"                --repo $REPO
gh label create "replay-system" --color "c5def5" --description "Recording or playback issues"          --repo $REPO
gh label create "world-gen"    --color "d4c5f9" --description "Procedural generation issues"           --repo $REPO
gh label create "combat"       --color "e99695" --description "Combat mechanics"                       --repo $REPO

# Workflow labels
gh label create "needs-triage" --color "ededed" --description "Not yet reviewed by dev"                --repo $REPO
gh label create "needs-info"   --color "d876e3" --description "Waiting for more details from reporter" --repo $REPO
gh label create "wont-fix"     --color "ffffff" --description "Out of scope or by design"              --repo $REPO
gh label create "duplicate"    --color "cfd3d7" --description "Already reported"                       --repo $REPO
gh label create "fixed"        --color "0e8a16" --description "Fixed in an upcoming release"           --repo $REPO
```

## After Running

1. Verify labels appear at `github.com/VainAsher/indie-ninja-feedback/labels`
2. Pin a "Welcome / Latest Release" issue to the repo
3. Set the repo description: "Bug reports and feedback for Indie Ninja Adventures"
4. Set the repo website to the launcher docs URL: `https://vainasher.github.io/indie-ninja-launcher/`
