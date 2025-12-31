
import random
import pygame
from collections import deque

from settings import (
    TILE_SIZE,
    ROOM_COLS, ROOM_ROWS,
    ROOM_W, ROOM_H,
    WORLD_W, WORLD_H,
)

class Room:
    def __init__(self, rx, ry):
        self.rx = rx
        self.ry = ry
        self.open_up = self.open_down = False
        self.open_left = self.open_right = False

def generate_macro_maze(cols, rows, rng, verticality_bias=0.5, branchiness=0.2):
    class Cell:
        __slots__ = ("open_up", "open_down", "open_left", "open_right", "visited")
        def __init__(self):
            self.open_up = self.open_down = self.open_left = self.open_right = False
            self.visited = False

    grid = [[Cell() for _ in range(cols)] for _ in range(rows)]

    def neighbors(cx, cy):
        dirs = []
        if cy > 0:          dirs.append((cx, cy - 1, "U", verticality_bias))
        if cy < rows - 1:   dirs.append((cx, cy + 1, "D", verticality_bias))
        if cx > 0:          dirs.append((cx - 1, cy, "L", 1.0 - verticality_bias))
        if cx < cols - 1:   dirs.append((cx + 1, cy, "R", 1.0 - verticality_bias))
        total = sum(w for *_, w in dirs) or 1.0
        weighted = []
        for item in dirs:
            w = item[3] / total
            weighted.append((w, item))
        rng.shuffle(weighted)
        weighted.sort(key=lambda x: rng.random() * (1.0 / max(1e-6, x[0])))
        return [item for _, item in weighted]

    def open_between(x, y, nx, ny, d):
        a = grid[y][x]; b = grid[ny][nx]
        if d == "U": a.open_up = True; b.open_down = True
        if d == "D": a.open_down = True; b.open_up = True
        if d == "L": a.open_left = True; b.open_right = True
        if d == "R": a.open_right = True; b.open_left = True

    sx, sy = 0, rows - 1
    stack = [(sx, sy)]
    grid[sy][sx].visited = True

    while stack:
        x, y = stack[-1]
        nxt = None
        for nx, ny, d, _ in neighbors(x, y):
            if not grid[ny][nx].visited:
                nxt = (nx, ny, d)
                break
        if not nxt:
            stack.pop(); continue
        nx, ny, d = nxt
        grid[ny][nx].visited = True
        open_between(x, y, nx, ny, d)
        stack.append((nx, ny))

        if rng.random() < branchiness:
            for tx, ty, td, _ in neighbors(x, y):
                if (tx, ty) != (nx, ny):
                    open_between(x, y, tx, ty, td)
                    break

    class RoomProxy:
        def __init__(self, c):
            self.open_up = c.open_up; self.open_down = c.open_down
            self.open_left = c.open_left; self.open_right = c.open_right

    return [[RoomProxy(grid[y][x]) for x in range(cols)] for y in range(rows)]

def find_room_path(rooms, start, goal):
    sx, sy = start
    gx, gy = goal
    q = deque([(sx, sy)])
    prev = {(sx, sy): None}

    while q:
        x, y = q.popleft()
        if (x, y) == (gx, gy): break
        r = rooms[y][x]
        for nx, ny, ok in (
            (x + 1, y, r.open_right),
            (x - 1, y, r.open_left),
            (x, y - 1, r.open_up),
            (x, y + 1, r.open_down),
        ):
            if ok and (nx, ny) not in prev and 0 <= nx < ROOM_COLS and 0 <= ny < ROOM_ROWS:
                prev[(nx, ny)] = (x, y)
                q.append((nx, ny))

    if (gx, gy) not in prev: return None

    path = []
    cur = (gx, gy)
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path

def build_world_from_path(path):
    world = [[0 for _ in range(WORLD_W)] for _ in range(WORLD_H)]
    path_mask = [[False for _ in range(WORLD_W)] for _ in range(WORLD_H)]

    for x in range(WORLD_W):
        world[0][x] = 1; world[WORLD_H - 1][x] = 1
        path_mask[0][x] = path_mask[WORLD_H - 1][x] = True
    for y in range(WORLD_H):
        world[y][0] = 1; world[y][WORLD_W - 1] = 1
        path_mask[y][0] = path_mask[y][WORLD_W - 1] = True

    floor_y_for = {}
    for (rx, ry) in path:
        base_x = rx * ROOM_W
        base_y = ry * ROOM_H
        floor_y = base_y + ROOM_H - 3
        floor_y_for[(rx, ry)] = floor_y
        for x in range(base_x + 2, base_x + ROOM_W - 2):
            world[floor_y][x] = 1
            path_mask[floor_y][x] = True
            if floor_y - 1 > 0: world[floor_y - 1][x] = 0
            if floor_y - 2 > 0: world[floor_y - 2][x] = 0

    for (rx, ry), (nx, ny) in zip(path, path[1:]):
        base_x1 = rx * ROOM_W; base_y1 = ry * ROOM_H
        base_x2 = nx * ROOM_W; base_y2 = ny * ROOM_H
        fy1 = floor_y_for[(rx, ry)]; fy2 = floor_y_for[(nx, ny)]

        if ry == ny and abs(nx - rx) == 1:
            y = fy1
            if nx > rx: x_start = base_x1 + ROOM_W - 3; x_end = base_x2 + 2
            else:       x_start = base_x2 + ROOM_W - 3; x_end = base_x1 + 2
            if x_start > x_end: x_start, x_end = x_end, x_start
            for x in range(x_start, x_end + 1):
                world[y][x] = 1; path_mask[y][x] = True
                if y - 1 > 0: world[y - 1][x] = 0
                if y - 2 > 0: world[y - 2][x] = 0
        elif nx == rx and abs(ny - ry) == 1:
            x_mid = base_x1 + ROOM_W // 2
            if ny > ry: high = (rx, ry); low = (nx, ny)
            else: high = (nx, ny); low = (rx, ry)
            fy_high = floor_y_for[high]; fy_low = floor_y_for[low]
            shaft_top = fy_high - 2; shaft_bottom = fy_low - 1
            for y in range(shaft_top, shaft_bottom + 1):
                if 0 < y < WORLD_H - 1:
                    for dx in (-1, 0, 1):
                        xx = x_mid + dx
                        if 0 < xx < WORLD_W - 1: world[y][xx] = 0
            for dx in (-1, 0, 1):
                xx = x_mid + dx
                if 0 < xx < WORLD_W - 1:
                    if 0 < fy_high < WORLD_H - 1:
                        world[fy_high][xx] = 1; path_mask[fy_high][xx] = True
                    if 0 < fy_low < WORLD_H - 1:
                        world[fy_low][xx] = 1; path_mask[fy_low][xx] = True
            side = -1; step = 4
            for y in range(shaft_bottom - 2, shaft_top, -step):
                lx = x_mid + side * 3
                if 1 < lx < WORLD_W - 2 and 1 < y < WORLD_H - 2:
                    world[y][lx] = 1; world[y][lx + 1] = 1
                    path_mask[y][lx] = path_mask[y][lx + 1] = True
                side *= -1

    end_rx, end_ry = path[-1]
    base_x = end_rx * ROOM_W
    floor_y = floor_y_for[(end_rx, end_ry)]
    ex_x = base_x + ROOM_W - 3
    ex_y = floor_y - 1
    world[ex_y][ex_x] = 2
    if 0 < floor_y < WORLD_H: path_mask[floor_y][ex_x] = True

    return world, path_mask

def decorate_world(world, path_mask, rng, *,
                   platform_band_step=4,
                   platform_len_range=(3, 7),
                   pillar_chance=0.3,
                   hole_chance=0.2):
    for ry in range(ROOM_ROWS):
        for rx in range(ROOM_COLS):
            base_x = rx * ROOM_W
            base_y = ry * ROOM_H

            for band in range(2, ROOM_H - 3, max(2, platform_band_step)):
                y = base_y + band
                if not (0 < y < WORLD_H - 1): continue
                segments = rng.randint(1, 3)
                for _ in range(segments):
                    L = rng.randint(*platform_len_range)
                    start_x = base_x + rng.randint(1, max(1, ROOM_W - L - 1))
                    for x in range(start_x, min(start_x + L, base_x + ROOM_W - 1)):
                        if 0 < x < WORLD_W - 1 and not path_mask[y][x] and world[y][x] != 2:
                            world[y][x] = 1
                            if y - 1 > 0 and not path_mask[y - 1][x] and world[y - 1][x] != 2:
                                world[y - 1][x] = 0

            if rng.random() < pillar_chance:
                pillars = rng.randint(1, 3)
                for _ in range(pillars):
                    vx = base_x + rng.randint(2, ROOM_W - 2)
                    if not (0 < vx < WORLD_W - 1): continue
                    top = base_y + rng.randint(2, max(2, ROOM_H - 8))
                    bottom = min(base_y + ROOM_H - 2, top + rng.randint(3, ROOM_H // 2))
                    gap_mod = rng.randint(3, 4)
                    for y in range(top, bottom):
                        if 0 < y < WORLD_H - 1 and not path_mask[y][vx] and world[y][vx] != 2 and (y - top) % gap_mod != 0:
                            world[y][vx] = 1

            if rng.random() < hole_chance:
                holes = rng.randint(1, 3)
                for _ in range(holes):
                    hx = base_x + rng.randint(1, ROOM_W - 2)
                    hy = base_y + rng.randint(1, ROOM_H - 2)
                    if 0 < hx < WORLD_W - 1 and 0 < hy < WORLD_H - 1 and not path_mask[hy][hx] and world[hy][hx] == 1:
                        for yy in range(hy, min(hy + 2, WORLD_H - 1)):
                            for xx in range(hx, min(hx + 2, WORLD_W - 1)):
                                if 0 < xx < WORLD_W - 1 and 0 < yy < WORLD_H - 1 and not path_mask[yy][xx] and world[yy][xx] != 2:
                                    world[yy][xx] = 0

def generate_hazards(world, rng, rate=0.03):
    hazards = []
    for y in range(2, WORLD_H - 1):
        for x in range(1, WORLD_W - 1):
            if world[y][x] == 1 and world[y - 1][x] == 0 and world[y - 2][x] == 0:
                if rng.random() < rate:
                    hx = x * TILE_SIZE + 2
                    hy = (y - 1) * TILE_SIZE + TILE_SIZE // 2
                    hazards.append(pygame.Rect(hx, hy, TILE_SIZE - 4, TILE_SIZE // 2))
    return hazards

def _valid_pickup_spot(world, tx, ty):
    if not (1 <= tx < WORLD_W - 1 and 2 <= ty < WORLD_H - 1): return False
    return world[ty][tx] == 0 and world[ty + 1][tx] == 1

def _far_from_hazards(tx, ty, hazard_tiles, radius=3):
    for hx, hy in hazard_tiles:
        if abs(hx - tx) <= radius and hy == ty: return False
        if abs(hy - ty) <= radius and hx == tx: return False
    return True

def generate_coins_and_pickups(world, rng, *, coin_density=0.04, health_density=0.006, lives_per_level=2, hazards=None):
    coins = []; healths = []; lives = []
    hazard_tiles = set()
    if hazards:
        for h in hazards:
            hx = (h.x + h.w // 2) // TILE_SIZE
            hy = (h.y + h.h // 2) // TILE_SIZE
            hazard_tiles.add((hx, hy))

    for ty in range(2, WORLD_H - 1):
        for tx in range(1, WORLD_W - 1):
            if not _valid_pickup_spot(world, tx, ty): continue
            if not _far_from_hazards(tx, ty, hazard_tiles, radius=3): continue
            import random as _r
            if _r.random() < coin_density:
                cx = tx * TILE_SIZE + TILE_SIZE // 4
                cy = ty * TILE_SIZE + TILE_SIZE // 4
                coins.append(pygame.Rect(cx, cy, TILE_SIZE // 2, TILE_SIZE // 2))
            elif _r.random() < health_density:
                hx = tx * TILE_SIZE + TILE_SIZE // 4
                hy = ty * TILE_SIZE + TILE_SIZE // 4
                healths.append(pygame.Rect(hx, hy, TILE_SIZE // 2, TILE_SIZE // 2))

    attempts = 0
    while len(lives) < max(0, int(lives_per_level)):
        attempts += 1
        if attempts > 10000: break
        tx = rng.randint(1, WORLD_W - 2); ty = rng.randint(2, WORLD_H - 2)
        if _valid_pickup_spot(world, tx, ty) and _far_from_hazards(tx, ty, hazard_tiles, radius=3):
            lx = tx * TILE_SIZE + TILE_SIZE // 4
            ly = ty * TILE_SIZE + TILE_SIZE // 4
            rect = pygame.Rect(lx, ly, TILE_SIZE // 2, TILE_SIZE // 2)
            if any(rect.colliderect(c) for c in coins + healths + lives): continue
            lives.append(rect)

    return coins, healths, lives

def build_solid_rects(world):
    tiles = []; exit_rect = None
    for y in range(WORLD_H):
        for x in range(WORLD_W):
            v = world[y][x]
            if v == 1:
                tiles.append(pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
            elif v == 2:
                exit_rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
    return tiles, exit_rect

def find_spawn(path):
    start_rx, start_ry = path[0]
    base_x = start_rx * ROOM_W; base_y = start_ry * ROOM_H
    floor_y = base_y + ROOM_H - 3
    sx = base_x + 3; sy = floor_y - 2
    return sx * TILE_SIZE, sy * TILE_SIZE

def generate_level(seed=None, diff_cfg=None):
    cfg = diff_cfg or {}
    rng = random.Random(seed)
    rooms = generate_macro_maze(
        ROOM_COLS, ROOM_ROWS, rng,
        verticality_bias=cfg.get("verticality_bias", 0.5),
        branchiness=cfg.get("branchiness", 0.2),
    )
    start = (0, ROOM_ROWS - 1); goal = (ROOM_COLS - 1, 0)
    path = find_room_path(rooms, start, goal)
    if not path:
        path = [(x, ROOM_ROWS - 1) for x in range(ROOM_COLS)] + [(ROOM_COLS - 1, y) for y in range(ROOM_ROWS - 2, -1, -1)]

    world, path_mask = build_world_from_path(path)
    decorate_world(
        world, path_mask, rng,
        platform_band_step=cfg.get("platform_band_step", 4),
        platform_len_range=cfg.get("platform_len_range", (3, 7)),
        pillar_chance=cfg.get("pillar_chance", 0.3),
        hole_chance=cfg.get("hole_chance", 0.2),
    )
    tiles, exit_rect = build_solid_rects(world)
    hazards = generate_hazards(world, rng, rate=cfg.get("hazard_rate", 0.03))
    coins, healths, lives = generate_coins_and_pickups(
        world, rng,
        coin_density=cfg.get("coin_density", 0.04),
        health_density=cfg.get("health_density", 0.006),
        lives_per_level=cfg.get("lives_per_level", 2),
        hazards=hazards
    )
    spawn = find_spawn(path)
    return world, tiles, exit_rect, spawn, coins, hazards, healths, lives
