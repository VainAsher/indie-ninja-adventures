
import pygame
from settings import (
    TILE_SIZE,
    MAX_RUN_SPEED, RUN_ACCEL_GROUND, RUN_DECEL_GROUND,
    RUN_ACCEL_AIR, RUN_DECEL_AIR,
    GRAVITY, JUMP_POWER, MAX_JUMPS, COYOTE_TIME, JUMP_BUFFER_TIME,
    FALL_GRAVITY_MULT, JUMP_CUT_MULT,
    WALL_SLIDE_SPEED, WALL_JUMP_POWER_X, WALL_JUMP_POWER_Y, WALL_JUMP_INPUT_LOCK,
    DASH_SPEED, DASH_DURATION, DASH_COOLDOWN,
    FAST_FALL_MULT, MAX_FALL_SPEED,
    CROUCH_SPEED_MULT, CROUCH_JUMP_MULT,
    PLAYER_MAX_HEALTH, INVINCIBILITY_TIME,
    FEATURES,
)

class Player:
    def __init__(self, x, y):
        self.normal_height = int(TILE_SIZE * 1.5)
        self.crouch_height = self.normal_height // 2
        self.width = TILE_SIZE - 8
        self.rect = pygame.Rect(x, y, self.width, self.normal_height)

        self.vx = 0.0
        self.vy = 0.0
        self.facing = 1

        self.on_ground = False
        self.on_wall = False
        self.wall_dir = 0

        self.jumps_left = MAX_JUMPS

        self._jump_held = False
        self._dash_held = False
        self._down_prev = False

        self.coyote_timer = 0.0
        self.jump_buffer_timer = 0.0

        self.is_dashing = False
        self.dash_time = 0.0
        self.dash_cooldown = 0.0

        self.crouching = False
        self.wall_jump_lock = 0.0

        self.health = PLAYER_MAX_HEALTH
        self.inv_timer = 0.0

    def update(self, keys, tiles, dt):
        self._update_timers(dt)
        self._update_dash_state(dt)
        self._handle_input(keys, tiles)
        self._apply_gravity(keys)
        self._move_and_collide(tiles)
        if self.on_wall and not self.on_ground and self.vy > WALL_SLIDE_SPEED:
            self.vy = WALL_SLIDE_SPEED

    def take_damage(self, amount):
        if self.inv_timer > 0.0:
            return False
        self.health -= max(1, int(amount))
        self.inv_timer = INVINCIBILITY_TIME
        return True

    def heal(self, amount):
        self.health = min(PLAYER_MAX_HEALTH, self.health + max(1, int(amount)))

    def _update_timers(self, dt):
        if self.on_ground: self.coyote_timer = COYOTE_TIME
        else: self.coyote_timer = max(0.0, self.coyote_timer - dt)
        if self.jump_buffer_timer > 0.0:
            self.jump_buffer_timer = max(0.0, self.jump_buffer_timer - dt)
        if self.wall_jump_lock > 0.0:
            self.wall_jump_lock = max(0.0, self.wall_jump_lock - dt)
        if self.inv_timer > 0.0:
            self.inv_timer = max(0.0, self.inv_timer - dt)

    def _update_dash_state(self, dt):
        if self.is_dashing:
            self.dash_time -= dt
            if self.dash_time <= 0:
                self.is_dashing = False
                self.dash_cooldown = DASH_COOLDOWN
        elif self.dash_cooldown > 0:
            self.dash_cooldown = max(0.0, self.dash_cooldown - dt)

    def _handle_input(self, keys, tiles):
        import pygame
        left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        down_now = keys[pygame.K_s] or keys[pygame.K_DOWN]

        if self.wall_jump_lock > 0.0:
            left = False; right = False

        if FEATURES.get("crouch", True):
            if down_now and not self._down_prev and self.on_ground:
                if not self.crouching: self._enter_crouch()
                else: self._try_exit_crouch(tiles)
        self._down_prev = down_now

        dash_pressed = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        if FEATURES.get("dash", True):
            if dash_pressed and not self._dash_held and not self.is_dashing and self.dash_cooldown <= 0.0:
                if self.facing == 0: self.facing = 1
                self.is_dashing = True
                self.dash_time = DASH_DURATION
        self._dash_held = dash_pressed

        if self.is_dashing:
            self.vx = self.facing * DASH_SPEED
        else:
            target_dir = (-1 if left else 0) + (1 if right else 0)
            if target_dir != 0: self.facing = target_dir
            on_ground = self.on_ground
            accel = RUN_ACCEL_GROUND if on_ground else RUN_ACCEL_AIR
            decel = RUN_DECEL_GROUND if on_ground else RUN_DECEL_AIR

            if target_dir != 0:
                if (self.vx == 0) or (self.vx * target_dir > 0):
                    self.vx += target_dir * accel
                else:
                    self.vx += target_dir * decel
            else:
                if abs(self.vx) <= decel: self.vx = 0.0
                else: self.vx -= decel * (1 if self.vx > 0 else -1)

            if self.crouching:
                self.vx *= CROUCH_SPEED_MULT

            if abs(self.vx) > MAX_RUN_SPEED:
                self.vx = MAX_RUN_SPEED * (1 if self.vx > 0 else -1)

        jump_down = keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]
        if jump_down and not self._jump_held:
            self.jump_buffer_timer = JUMP_BUFFER_TIME
        self._jump_held = jump_down

        if self.jump_buffer_timer > 0.0:
            if self._try_ground_or_coyote_jump(): return
            if FEATURES.get("wall_jump", True) and self._try_wall_jump(): return
            if FEATURES.get("double_jump", True) and self._try_double_jump(): return

    def _try_ground_or_coyote_jump(self):
        if self.on_ground or self.coyote_timer > 0.0:
            power = JUMP_POWER * (CROUCH_JUMP_MULT if self.crouching else 1.0)
            self.vy = -power
            self.on_ground = False
            self.coyote_timer = 0.0
            self.jump_buffer_timer = 0.0
            self.jumps_left = MAX_JUMPS - 1
            return True
        return False

    def _try_wall_jump(self):
        if self.on_wall:
            self.facing = -self.wall_dir
            self.vy = -WALL_JUMP_POWER_Y
            self.vx = -self.wall_dir * WALL_JUMP_POWER_X
            self.jump_buffer_timer = 0.0
            self.jumps_left = MAX_JUMPS - 1
            self.is_dashing = False
            self.wall_jump_lock = WALL_JUMP_INPUT_LOCK
            return True
        return False

    def _try_double_jump(self):
        if self.jumps_left > 0:
            self.vy = -JUMP_POWER
            self.jumps_left -= 1
            self.jump_buffer_timer = 0.0
            return True
        return False

    def _apply_gravity(self, keys):
        import pygame
        down = keys[pygame.K_s] or keys[pygame.K_DOWN]
        jump_held = keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]

        self.vy += GRAVITY
        if self.vy < 0 and not jump_held:
            self.vy += GRAVITY * (JUMP_CUT_MULT - 1)
        if self.vy > 0:
            self.vy += GRAVITY * (FALL_GRAVITY_MULT - 1)
        if FEATURES.get("fast_fall", True) and self.vy > 0 and down and not self.on_ground:
            self.vy += GRAVITY * (FAST_FALL_MULT - 1)
        if self.vy > MAX_FALL_SPEED:
            self.vy = MAX_FALL_SPEED

    def _move_and_collide(self, tiles):
        self.rect.x += int(round(self.vx))
        self.on_wall = False; self.wall_dir = 0
        for t in tiles:
            if self.rect.colliderect(t):
                if self.vx > 0:
                    self.rect.right = t.left; self.on_wall = True; self.wall_dir = 1
                elif self.vx < 0:
                    self.rect.left = t.right; self.on_wall = True; self.wall_dir = -1
                self.vx = 0.0

        self.rect.y += int(round(self.vy))
        self.on_ground = False
        for t in tiles:
            if self.rect.colliderect(t):
                if self.vy > 0:
                    self.rect.bottom = t.top; self.vy = 0.0; self.on_ground = True; self.jumps_left = MAX_JUMPS
                elif self.vy < 0:
                    self.rect.top = t.bottom; self.vy = 0.0

    def _enter_crouch(self):
        if self.crouching: return
        diff = self.normal_height - self.crouch_height
        self.rect.y += diff; self.rect.height = self.crouch_height
        self.crouching = True

    def _try_exit_crouch(self, tiles):
        if not self.crouching: return
        diff = self.normal_height - self.crouch_height
        test_rect = pygame.Rect(self.rect.x, self.rect.y - diff, self.width, self.normal_height)
        if not any(test_rect.colliderect(t) for t in tiles):
            self.rect = test_rect; self.crouching = False
