
import sys
import math
import random
import pygame

from settings import (
    LOGICAL_W, LOGICAL_H, FPS, VSYNC, WINDOW_FLAGS,
    TILE_SIZE, WORLD_PX_W, WORLD_PX_H, HUD_HEIGHT,
    COLOR_BG, COLOR_TILE, COLOR_PLAYER, COLOR_EXIT, COLOR_EXIT_LOCKED, COLOR_TEXT, COLOR_COIN, COLOR_HAZARD, COLOR_HEALTH, COLOR_LIFE,
    FONT, DIFFICULTY, DIFFICULTY_CONFIG,
    BASE_TIME_SCORE, COIN_SCORE_VALUE,
    PLAYER_LIVES, PLAYER_MAX_HEALTH, HEALTH_VALUE, LIFE_VALUE,
    DEBUG_DEFAULT, DEBUG_SHOW_GRID, DEBUG_SHOW_BBOX,
    DEFAULT_SEED,
)
from level_gen import generate_level
from player import Player
from camera import get_camera_rect
from ui import Button, TextInput, draw_hud

def create_window():
    pygame.display.set_caption("Vain Asher Gaming's: Indie Ninja Adventures")
    return pygame.display.set_mode((LOGICAL_W, LOGICAL_H), WINDOW_FLAGS, vsync=VSYNC)

def blit_letterboxed(src, dst):
    sw, sh = src.get_size()
    dw, dh = dst.get_size()
    scale = min(dw / sw, dh / sh)
    tw, th = int(sw * scale), int(sh * scale)
    temp = pygame.transform.smoothscale(src, (tw, th))
    x = (dw - tw) // 2; y = (dh - th) // 2
    dst.fill((0,0,0))
    dst.blit(temp, (x, y))

def draw_world(play_surf, world, tiles, exit_rect, coins, hazards, healths, lives, cam, debug, exit_unlocked):
    if not debug:
        play_surf.fill(COLOR_BG)
        for t in tiles:
            if cam.colliderect(t):
                pygame.draw.rect(play_surf, COLOR_TILE, (t.x - cam.x, t.y - cam.y, t.w, t.h))
        for h in hazards:
            if cam.colliderect(h):
                pygame.draw.polygon(play_surf, COLOR_HAZARD, [
                    (h.x - cam.x, h.bottom - cam.y),
                    (h.centerx - cam.x, h.top - cam.y),
                    (h.right - cam.x, h.bottom - cam.y)
                ])
        for c in coins:
            if cam.colliderect(c):
                pygame.draw.ellipse(play_surf, COLOR_COIN, (c.x - cam.x, c.y - cam.y, c.w, c.h))
        for hp in healths:
            if cam.colliderect(hp):
                pygame.draw.rect(play_surf, COLOR_HEALTH, (hp.x - cam.x, hp.y - cam.y, hp.w, hp.h), border_radius=4)
        for life in lives:
            if cam.colliderect(life):
                pygame.draw.rect(play_surf, COLOR_LIFE, (life.x - cam.x, life.y - cam.y, life.w, life.h), border_radius=4)
        if exit_rect and cam.colliderect(exit_rect):
            color = COLOR_EXIT if exit_unlocked else COLOR_EXIT_LOCKED
            pygame.draw.rect(play_surf, color, (exit_rect.x - cam.x, exit_rect.y - cam.y, exit_rect.w, exit_rect.h), border_radius=6)
        return

    from settings import ROOM_W, ROOM_H, ROOM_COLS, ROOM_ROWS
    rng = random.Random(42)
    macro_colors = [(rng.randint(40, 160), rng.randint(40, 160), rng.randint(40, 160)) for _ in range(ROOM_ROWS * ROOM_COLS)]
    play_surf.fill((10, 10, 20))

    for ry in range(ROOM_ROWS):
        for rx in range(ROOM_COLS):
            color = macro_colors[ry * ROOM_COLS + rx]
            rect = pygame.Rect(rx * ROOM_W * TILE_SIZE - cam.x, ry * ROOM_H * TILE_SIZE - cam.y, ROOM_W * TILE_SIZE, ROOM_H * TILE_SIZE)
            pygame.draw.rect(play_surf, color, rect)

    for t in tiles:
        if cam.colliderect(t):
            rx = (t.x // TILE_SIZE) // ROOM_W
            ry = (t.y // TILE_SIZE) // ROOM_H
            idx = max(0, min(ry * ROOM_COLS + rx, len(macro_colors) - 1))
            base = macro_colors[idx]
            shade = (int(base[0] * 0.6), int(base[1] * 0.6), int(base[2] * 0.6))
            pygame.draw.rect(play_surf, shade, (t.x - cam.x, t.y - cam.y, t.w, t.h))

    for h in hazards:
        if cam.colliderect(h):
            pygame.draw.rect(play_surf, (255, 30, 30), (h.x - cam.x, h.y - cam.y, h.w, h.h), 2)

    for c in coins:
        if cam.colliderect(c):
            pygame.draw.ellipse(play_surf, COLOR_COIN, (c.x - cam.x, c.y - cam.y, c.w, c.h))
    for hp in healths:
        if cam.colliderect(hp):
            pygame.draw.rect(play_surf, COLOR_HEALTH, (hp.x - cam.x, hp.y - cam.y, hp.w, hp.h), 2, border_radius=4)
    for life in lives:
        if cam.colliderect(life):
            pygame.draw.rect(play_surf, COLOR_LIFE, (life.x - cam.x, life.y - cam.y, life.w, life.h), 2, border_radius=4)

    if exit_rect and cam.colliderect(exit_rect):
        color = COLOR_EXIT if exit_unlocked else COLOR_EXIT_LOCKED
        pygame.draw.rect(play_surf, color, (exit_rect.x - cam.x, exit_rect.y - cam.y, exit_rect.w, exit_rect.h), border_radius=6)

    if DEBUG_SHOW_GRID:
        for y in range(0, WORLD_PX_H, TILE_SIZE * ROOM_H):
            pygame.draw.line(play_surf, (255,255,255), (0 - cam.x, y - cam.y), (WORLD_PX_W - cam.x, y - cam.y), 1)
        for x in range(0, WORLD_PX_W, TILE_SIZE * ROOM_W):
            pygame.draw.line(play_surf, (255,255,255), (x - cam.x, 0 - cam.y), (x - cam.x, WORLD_PX_H - cam.y), 1)

STATE_MENU = "menu"
STATE_PLAY = "play"
STATE_PAUSE = "pause"
STATE_GAMEOVER = "gameover"
STATE_SEED = "seed"

class Game:
    def __init__(self):
        self.window = create_window()
        self.logical = pygame.Surface((LOGICAL_W, LOGICAL_H))
        self.play_area = pygame.Surface((LOGICAL_W, LOGICAL_H - HUD_HEIGHT))

        self.state = STATE_MENU
        self.debug = DEBUG_DEFAULT
        self.difficulty = DIFFICULTY
        self.seed = DEFAULT_SEED

        self.level_index = 1
        self.total_score = 0
        self.lives = PLAYER_LIVES
        self.game_time = 0.0

        # NEW: track whether we can resume an existing run
        self.can_resume = False

        self._build_level()  # prebuild so Start works instantly
        self._build_menu_ui()
        self.seed_input = None

    def _build_level(self):
        cfg = DIFFICULTY_CONFIG[self.difficulty]
        world, tiles, exit_rect, spawn, coins, hazards, healths, lives = generate_level(self.seed, cfg)
        self.world = world
        self.tiles = tiles
        self.exit_rect = exit_rect
        self.coins = coins
        self.hazards = hazards
        self.healths = healths
        self.lives_pickups = lives
        self.player = Player(spawn[0], spawn[1])

        self.coin_total = len(self.coins)
        self.coin_required = max(0, math.ceil(cfg["coin_ratio"] * self.coin_total))
        self.coins_collected = 0
        self.exit_unlocked = (self.coin_required == 0)
        self.game_time = 0.0

    def _build_menu_ui(self):
        buttons = []
        def add(label, cb): buttons.append(Button(label, cb))

        # If there's a paused/active run, show RESUME at the top
        if self.can_resume:
            add("Resume", self._resume_game)

        add("Start New", self._start_new_run)
        add("Enter Seed", self._goto_seed)
        add("Random Seed", self._randomize_seed)
        add("Difficulty: " + self.difficulty.capitalize(), self._cycle_diff)
        add("Toggle Debug", self._toggle_debug)
        add("Quit", self._quit_game)
        self.menu_buttons = buttons

    def _layout_menu(self):
        w, h = 360, 56
        gap = 16
        total = len(self.menu_buttons) * (h + gap) - gap
        start_y = (LOGICAL_H - total) // 2
        x = (LOGICAL_W - w) // 2
        for i, b in enumerate(self.menu_buttons):
            b.layout(x, start_y + i * (h + gap), w, h)

    # ---- menu actions ----
    def _start_new_run(self):
        self._build_level()
        self.can_resume = True
        self.state = STATE_PLAY

    def _resume_game(self):
        # Simply unpause to gameplay without rebuilding anything
        self.state = STATE_PLAY

    def _goto_seed(self):
        self.state = STATE_SEED
        self.seed_input = TextInput("Level Seed (enter to confirm):", self.seed or "")

    def _randomize_seed(self):
        self.seed = None
        self._build_menu_ui()

    def _cycle_diff(self):
        order = ["easy", "medium", "hard", "expert"]
        i = (order.index(self.difficulty) + 1) % len(order)
        self.difficulty = order[i]
        self._build_menu_ui()

    def _toggle_debug(self):
        self.debug = not self.debug

    def _quit_game(self):
        self.state = STATE_GAMEOVER
        pygame.event.post(pygame.event.Event(pygame.QUIT))

    # ---------- events ----------
    def handle_event(self, event):
        if self.state == STATE_MENU:
            for b in self.menu_buttons: b.handle_event(event)
        elif self.state == STATE_SEED:
            self.seed_input.handle_event(event)
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                txt = self.seed_input.text.strip()
                self.seed = txt if txt != "" else None
                self._build_menu_ui()
                self.state = STATE_MENU
        elif self.state == STATE_PLAY:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = STATE_PAUSE
                elif event.key == pygame.K_TAB:
                    self.debug = not self.debug
                elif event.key == pygame.K_m:
                    # Go to main menu and mark that we can resume current run
                    self.can_resume = True
                    self._build_menu_ui()
                    self.state = STATE_MENU
                elif event.key == pygame.K_r:
                    # soft reset current level
                    cfg = DIFFICULTY_CONFIG[self.difficulty]
                    # rebuild ONLY the level but keep meta like lives/score
                    world, tiles, exit_rect, spawn, coins, hazards, healths, lives = generate_level(self.seed, cfg)
                    self.world = world; self.tiles = tiles; self.exit_rect = exit_rect
                    self.coins = coins; self.hazards = hazards
                    self.healths = healths; self.lives_pickups = lives
                    self.player = Player(spawn[0], spawn[1])
                    self.coin_total = len(self.coins)
                    self.coin_required = max(0, math.ceil(cfg["coin_ratio"] * self.coin_total))
                    self.coins_collected = 0
                    self.exit_unlocked = (self.coin_required == 0)
                    self.game_time = 0.0
        elif self.state == STATE_PAUSE:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = STATE_PLAY
                elif event.key == pygame.K_m:
                    # From pause -> main menu, with resume available
                    self.can_resume = True
                    self._build_menu_ui()
                    self.state = STATE_MENU

    # ---------- update/draw ----------
    def update(self, dt):
        if self.state != STATE_PLAY:
            return
        self.game_time += dt
        keys = pygame.key.get_pressed()
        self.player.update(keys, self.tiles, dt)

        # pick-ups and hazards same as v0.3
        for c in self.coins[:]:
            if self.player.rect.colliderect(c):
                self.coins.remove(c)
                self.coins_collected += 1

        if not self.exit_unlocked and self.coin_required > 0 and self.coins_collected >= self.coin_required:
            self.exit_unlocked = True

        for h in self.hazards:
            if self.player.rect.colliderect(h):
                if self.player.take_damage(1):
                    dir_x = -1 if self.player.rect.centerx > h.centerx else 1
                    self.player.vx = dir_x * 10.0
                    self.player.vy = -8.0
                    if self.player.health <= 0:
                        self.lives -= 1
                        if self.lives < 0:
                            self.state = STATE_GAMEOVER
                        else:
                            # death -> rebuild current level but keep meta, mark resumable
                            cfg = DIFFICULTY_CONFIG[self.difficulty]
                            world, tiles, exit_rect, spawn, coins, hazards, healths, lives = generate_level(self.seed, cfg)
                            self.world = world; self.tiles = tiles; self.exit_rect = exit_rect
                            self.coins = coins; self.hazards = hazards
                            self.healths = healths; self.lives_pickups = lives
                            self.player = Player(spawn[0], spawn[1])
                            self.coin_total = len(self.coins)
                            self.coin_required = max(0, math.ceil(cfg["coin_ratio"] * self.coin_total))
                            self.coins_collected = 0
                            self.exit_unlocked = (self.coin_required == 0)
                            self.game_time = 0.0
                        break

        for hp in self.healths[:]:
            if self.player.rect.colliderect(hp):
                self.player.heal(HEALTH_VALUE)
                self.healths.remove(hp)

        for life in self.lives_pickups[:]:
            if self.player.rect.colliderect(life):
                self.lives += LIFE_VALUE
                self.lives_pickups.remove(life)

        if self.exit_rect and self.exit_unlocked and self.player.rect.colliderect(self.exit_rect):
            cfg = DIFFICULTY_CONFIG[self.difficulty]
            time_score = max(0, int(BASE_TIME_SCORE / max(1.0, self.game_time)))
            coin_score = self.coins_collected * COIN_SCORE_VALUE
            level_score = int((time_score + coin_score) * cfg["multiplier"])
            self.total_score += level_score
            self.level_index += 1
            # next level: rebuild but keep meta and mark resumable
            world, tiles, exit_rect, spawn, coins, hazards, healths, lives = generate_level(self.seed, cfg)
            self.world = world; self.tiles = tiles; self.exit_rect = exit_rect
            self.coins = coins; self.hazards = hazards
            self.healths = healths; self.lives_pickups = lives
            self.player = Player(spawn[0], spawn[1])
            self.coin_total = len(self.coins)
            self.coin_required = max(0, math.ceil(cfg["coin_ratio"] * self.coin_total))
            self.coins_collected = 0
            self.exit_unlocked = (self.coin_required == 0)
            self.game_time = 0.0

    def draw(self):
        cam = get_camera_rect(self.player.rect)
        self.play_area.fill(COLOR_BG)
        draw_world(self.play_area, self.world, self.tiles, self.exit_rect, self.coins, self.hazards, self.healths, self.lives_pickups, cam, self.debug, self.exit_unlocked)

        pygame.draw.rect(self.play_area, COLOR_PLAYER, (self.player.rect.x - cam.x, self.player.rect.y - cam.y, self.player.rect.w, self.player.rect.h), border_radius=4)
        if DEBUG_SHOW_BBOX:
            pygame.draw.rect(self.play_area, (0,255,0), (self.player.rect.x - cam.x, self.player.rect.y - cam.y, self.player.rect.w, self.player.rect.h), 1)

        self.logical.blit(self.play_area, (0, HUD_HEIGHT))

        diff_txt = f"{self.difficulty.capitalize()}"
        coin_txt = f"Coins {self.coins_collected}/{self.coin_required if self.coin_required>0 else self.coin_total}"
        time_txt = f"{self.game_time:5.2f}s"
        score_txt = f"Score {self.total_score}"
        hp_txt = f"HP {self.player.health}/{PLAYER_MAX_HEALTH}"
        lives_txt = f"Lives {max(0, self.lives)}"
        left = f"Vain Asher Gaming's: Indie Ninja Adventures | Lvl {self.level_index} | {diff_txt} | {coin_txt}"
        right = f"{hp_txt} | {lives_txt} | {time_txt} | {score_txt}"
        draw_hud(self.logical, left, right)

        if self.state == STATE_MENU:
            self._layout_menu()
            self._draw_overlay_title("NINJA DASH — Resume or Start New")
            for b in self.menu_buttons: b.draw(self.logical)
        elif self.state == STATE_PAUSE:
            self._draw_overlay_title("PAUSED — ESC resume | M menu")
        elif self.state == STATE_SEED:
            self._draw_overlay_title("ENTER SEED")
            r = pygame.Rect(LOGICAL_W//2 - 300, LOGICAL_H//2 - 70, 600, 140)
            self.seed_input.draw(self.logical, r)
        elif self.state == STATE_GAMEOVER:
            self._draw_overlay_title("GAME OVER — Press R to restart | M for Menu")

        blit_letterboxed(self.logical, self.window)
        pygame.display.flip()

    def _draw_overlay_title(self, title):
        s = FONT.render("TAB: Toggle Debug | R: Reset Level | M: Main Menu", True, COLOR_TEXT)
        t = pygame.font.SysFont("consolas", 48).render(title, True, COLOR_TEXT)
        tr = t.get_rect(center=(LOGICAL_W//2, LOGICAL_H//2 - 120))
        self.logical.blit(t, tr)
        sr = s.get_rect(center=(LOGICAL_W//2, LOGICAL_H//2 - 60))
        self.logical.blit(s, sr)

def main():
    pygame.init()
    clock = pygame.time.Clock()
    game = Game()

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                game.window = pygame.display.set_mode(event.size, WINDOW_FLAGS, vsync=VSYNC)
            else:
                game.handle_event(event)

        pressed = pygame.key.get_pressed()
        if pressed[pygame.K_r] and game.state in (STATE_MENU, STATE_GAMEOVER):
            # Start a fresh run quickly from menu/gameover
            game.level_index = 1
            game.total_score = 0
            game.lives = PLAYER_LIVES
            game._build_level()
            game.can_resume = True
            game.state = STATE_PLAY

        game.update(dt)
        game.draw()

    pygame.quit(); sys.exit()

if __name__ == "__main__":
    main()
