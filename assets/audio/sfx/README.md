# SFX Asset Directory

Place `.wav` or `.ogg` files here. Filenames must match the table below.
Missing files are silently ignored — the game runs without audio if no assets are present.

| Filename          | Event                                  |
|-------------------|----------------------------------------|
| `swing.wav`       | Sword attack swing                     |
| `hit_enemy.wav`   | Sword connects with enemy or boss      |
| `player_hurt.wav` | Player takes damage (non-lethal)       |
| `player_death.wav`| Player dies                            |
| `jump.wav`        | Player jumps (ground or double-jump)   |
| `land.wav`        | Player lands after being airborne      |
| `dash.wav`        | Dash ability activates                 |
| `pickup_coin.wav` | Coin collected                         |
| `pickup_item.wav` | Collectible or health pickup collected |
| `menu_select.wav` | Menu cursor moves up/down              |
| `menu_confirm.wav`| Menu item activated                    |
| `inventory_open.wav` | Inventory opened or closed          |

Recommended format: 44100 Hz, 16-bit, mono or stereo `.wav` or `.ogg`.
