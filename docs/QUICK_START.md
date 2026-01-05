# Quick Start Guide - Ninja Dash v0.7.0

## How to Play

### Start the Game
```bash
python demo_game.py
```

---

## Game Modes

### 🏰 Campaign Mode
**Best for:** Story-driven progression with hub worlds and missions

**How to Access:**
1. Main Menu → Start Game
2. Select **Campaign Mode**
3. Wait for hub generation (~2 seconds)
4. Explore the Central Hub

**What You Can Do:**
- Walk around 10-room hub world
- Test all movement mechanics
- Fight enemies that spawn
- Take damage and heal (HP system)
- Explore procedurally-generated hub layout

**What's Not Ready Yet:**
- Can't talk to NPCs (Phase 2)
- Can't use portals (Phase 2)
- Can't start missions from hub (use Playtest Mode instead)

**Controls:**
- Arrow Keys / WASD: Move
- Space / W: Jump (double jump available)
- Shift: Dash
- S / Down: Crouch

---

### 🎮 Arcade Mode
**Best for:** Classic infinite procedural platforming

**How to Access:**
1. Main Menu → Start Game
2. Select **Arcade Mode**
3. Start playing immediately

**What You Get:**
- Infinite procedural world generation
- Classic gameplay (unchanged from before)
- All mechanics active (jump, dash, crouch)
- Health system enabled
- Enemies spawn and fight

**Perfect for:**
- Quick play sessions
- Testing procedural generation
- Practicing mechanics
- Speedrunning

---

### 🧪 Playtest Mode
**Best for:** Testing specific missions and world layouts

**How to Access:**
1. Main Menu → Start Game
2. Select **Playtest Mode**
3. Browse mission list (25 missions)
4. Select a mission and press Enter

**Mission Organization:**
```
Forest (5 missions)
  - forest_1: Forest Patrol (Difficulty 1, 8 rooms)
  - forest_2: Deep Woods (Difficulty 2, 10 rooms)
  - forest_3: Forest Guardian (Difficulty 3, 12 rooms) [BOSS]
  - forest_4: Canopy Sprint (Difficulty 2, 6 rooms) [TIMED]
  - forest_5: Ancient Grove (Difficulty 3, 10 rooms)

Town (6 missions)
  - town_1: Town Square (Difficulty 2, 8 rooms)
  - town_2: Rooftop Chase (Difficulty 3, 8 rooms) [TIMED]
  - town_3: Market District (Difficulty 3, 10 rooms)
  - town_4: Guard Barracks (Difficulty 3, 12 rooms)
  - town_5: Mayoral Manor (Difficulty 4, 15 rooms) [BOSS]
  - town_6: Secret Sewers (Difficulty 4, 12 rooms)

Caves (5 missions)
  - caves_1: Cave Entrance (Difficulty 4, 10 rooms)
  - caves_2: Underground River (Difficulty 4, 12 rooms)
  - caves_3: Crystal Caverns (Difficulty 5, 15 rooms)
  - caves_4: Golem's Lair (Difficulty 5, 12 rooms) [BOSS]
  - caves_5: Deep Descent (Difficulty 5, 15 rooms)

Castle (6 missions)
  - castle_1: Outer Walls (Difficulty 5, 12 rooms)
  - castle_2: Great Hall (Difficulty 5, 15 rooms)
  - castle_3: Royal Armory (Difficulty 6, 12 rooms)
  - castle_4: Throne Room (Difficulty 6, 15 rooms) [BOSS]
  - castle_5: King's Challenge (Difficulty 6, 10 rooms) [TIMED]
  - castle_6: Hidden Vault (Difficulty 6, 15 rooms)

Sewer (3 missions)
  - sewer_1: Toxic Tunnels (Difficulty 6, 15 rooms)
  - sewer_2: Plague Nest (Difficulty 7, 15 rooms) [BOSS]
  - sewer_3: Final Depths (Difficulty 7, 20 rooms)
```

**Navigation:**
- Arrow Keys: Browse missions
- Enter: Start selected mission
- ESC: Back to mode selection

---

## Controls Reference

### Movement
- **Arrow Keys** or **WASD**: Move left/right
- **Space** or **W** or **Up Arrow**: Jump
- **Space (in air)**: Double jump
- **Space (on wall)**: Wall jump
- **Shift**: Dash (with cooldown)
- **S** or **Down Arrow**: Crouch (toggle)

### Camera
- **C**: Cycle camera mode (World → Room → Free)
- **Arrow Keys (Free Cam)**: Move camera

### Game Controls
- **P**: Toggle static/procedural mode
- **ESC**: Pause menu
- **I**: Inventory (not yet implemented)

---

## Health System

### HP Display
- **Location:** Top-left corner
- **Format:** Heart containers (♥♥♥)
- **Base HP:** 3 hearts
- **Max HP:** Can be increased via items

### Taking Damage
- **Enemy Contact:** 1 HP damage
- **Invincibility:** 1 second after hit (blinking)
- **Death:** Only occurs at 0 HP
- **Respawn:** At last checkpoint

### Healing
- **Health Pickups:** Drop from enemies
- **Small Potion:** Restores 1 HP
- **Medium Potion:** Restores 2 HP
- **Large Potion:** Restores 3 HP

---

## Enemy System

### Enemy Types
- **Goblins:** Ground patrol, melee attack
- **Bats:** Flying enemies (coming soon)
- **Slimes:** Slow, high HP (coming soon)

### Enemy Behavior
- **Patrol:** Enemies walk between waypoints
- **Detection:** 200 pixel radius
- **Chase:** Run toward player when detected
- **Attack:** Melee damage when close

### Combat
- **Dash Attack:** Dash into enemy for damage
- **Jump Attack:** Land on enemy from above
- **Contact Damage:** Enemy contact = 1 HP loss

### Loot Drops
- **Health Potions:** Common drop
- **Currency:** Gold coins
- **Items:** Random loot (future)

---

## Developer Testing

### Command-Line Shortcuts

```bash
# Start specific mission directly
python demo_game.py --mode playtest --mission forest_1

# Campaign mode with mission
python demo_game.py --mode campaign --mission forest_1

# Arcade mode with seed
python demo_game.py --mode arcade --procedural --seed 42

# Custom world generation
python demo_game.py --procedural --shape blob --rooms 10 --seed 999

# Headless mode for testing
python demo_game.py --headless --mode playtest --mission town_3
```

### Useful Flags
- `--mode [arcade|campaign|playtest]`: Set game mode
- `--mission [mission_id]`: Load specific mission
- `--procedural`: Enable procedural generation
- `--seed [number]`: Set world seed
- `--shape [blob|snake|line|grid]`: Set room layout
- `--rooms [number]`: Set room count
- `--headless`: Run without display (testing)

---

## Troubleshooting

### Game doesn't start
```bash
# Check if all dependencies installed
pip install pygame

# Verify game directory
cd c:\Users\asher\Downloads\ninja_dash_v0_3
python demo_game.py
```

### Menu doesn't appear
- Check window size (should be 1280x720)
- Press ESC to ensure not in game state
- Restart the game

### Campaign mode crashes
- Delete corrupted save: `del user_data\saves\savegame.json`
- Restart game to create fresh save

### Enemies don't spawn
- Check room shape (blob/snake work best)
- Verify mission has enemy anchors
- Check console for spawn warnings

### Health bar not visible
- Press H to toggle HUD visibility
- Check top-left corner of screen
- Verify health system initialized (console logs)

---

## What's Next?

### Currently Working
- ✅ Menu system with 3 game modes
- ✅ Health system (HP, damage, healing)
- ✅ Enemy system (AI, combat, loot)
- ✅ 25 missions across 5 regions
- ✅ Campaign progression (regions, abilities)

### Coming in Phase 2
- 🔜 NPC system (talk to mission givers)
- 🔜 Portal system (fast travel between hubs)
- 🔜 Dialogue system (conversations with NPCs)
- 🔜 Shop system (buy/sell items)
- 🔜 Full campaign progression

### Future Phases
- Inventory UI (currently backend only)
- More enemy types (bats, slimes, bosses)
- Advanced boss mechanics
- Level editor
- Multiplayer

---

## Getting Help

### Documentation
- **[INTEGRATION_STATUS.md](docs/INTEGRATION_STATUS.md)** - Full integration report
- **[READY_TO_TEST.md](docs/READY_TO_TEST.md)** - Testing guide
- **[MENU_INTEGRATION_GUIDE.md](docs/MENU_INTEGRATION_GUIDE.md)** - Menu system guide

### Testing Checklist
See [docs/READY_TO_TEST.md](docs/READY_TO_TEST.md) for complete testing instructions.

### Bug Reports
Check console output for error messages and include:
- Game mode being tested
- Steps to reproduce
- Error messages from console
- Log files from `user_data/logs/`

---

## Quick Tips

### For Players
- **Start with Arcade Mode** to learn mechanics
- **Try Playtest Mode** to see different mission layouts
- **Use Campaign Mode** when Phase 2 (NPCs) is ready

### For Developers
- **Use command-line** for quick mission testing
- **Check logs** in `user_data/logs/` for debugging
- **Run tests** with `pytest tests/` to verify systems
- **Read docs** in `docs/` folder for implementation details

---

**Have fun testing! 🎮**

*Version: v0.7.0*
*Last Updated: 2025-12-15*
