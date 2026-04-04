"""
Enemy and NPC Procedural Renderer

Draws recognizable character shapes for each enemy/NPC type using pygame
primitives. Acts as a drop-in replacement for the placeholder colored squares,
and is designed to be swapped for sprite sheets later.

Public API:
    draw_enemy(surface, enemy, screen_rect, ticks)
    draw_npc(surface, npc, npc_def, screen_rect, ticks)
"""

import math

import pygame


# ─────────────────────────────────────────────────────────────── helpers ────


def _shadow(surface: pygame.Surface, rect: pygame.Rect) -> None:
    """Soft ellipse drop-shadow beneath a character."""
    sw = max(rect.width - 6, 4)
    sh = max(5, rect.height // 9)
    surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
    pygame.draw.ellipse(surf, (0, 0, 0, 55), (0, 0, sw, sh))
    surface.blit(surf, (rect.centerx - sw // 2, rect.bottom - sh // 2))


def _hurt_flash(surface: pygame.Surface, rect: pygame.Rect, invincibility_frames: int) -> None:
    """White flash overlay when recently hit."""
    if invincibility_frames > 0:
        alpha = min(180, invincibility_frames * 20)
        flash = pygame.Surface(rect.size, pygame.SRCALPHA)
        flash.fill((255, 255, 255, alpha))
        surface.blit(flash, rect.topleft)


# ──────────────────────────────────────────────────────────────── GOBLIN ────
#
#  Small humanoid enemy: pointed hat, big eyes, dagger.
#  Goblin (32 × 48)


def draw_goblin(
    surface: pygame.Surface,
    rect: pygame.Rect,
    facing_right: bool,
    animation_frame: int,
    ai_state,
    invincibility_frames: int,
    ticks: int,
) -> None:
    from entities.enemy import EnemyAIState

    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    cx = rect.centerx
    flip = 1 if facing_right else -1

    C_BODY = (65, 140, 65)
    C_HEAD = (90, 165, 80)
    C_SKIN = (135, 195, 105)
    C_EYE = (15, 15, 15)
    C_MOUTH = (145, 65, 65)
    C_HAT = (45, 95, 45)
    C_WEAPON = (175, 145, 85)

    _shadow(surface, rect)

    moving = ai_state in (EnemyAIState.PATROL, EnemyAIState.CHASE)
    stunned = ai_state == EnemyAIState.STUNNED
    bob = -1 if (moving and animation_frame % 2 == 0) else 0

    # Legs
    lw = max(w // 5, 4)
    lh = h // 4
    ly = y + h - lh
    for i, lx in enumerate((cx - lw - 1, cx + 1)):
        walk = (
            ((-3 if i == 0 else 3) if animation_frame % 2 == 0 else (3 if i == 0 else -3))
            if moving
            else 0
        )
        pygame.draw.rect(surface, C_BODY, (lx, ly + walk, lw, lh))

    # Body
    bw = int(w * 0.74)
    bh = int(h * 0.36)
    bx = cx - bw // 2
    by = y + h - lh - bh + bob
    pygame.draw.rect(surface, C_BODY, (bx, by, bw, bh))

    # Arm + weapon
    aw = max(w // 6, 3)
    ah = bh - 4
    ax = cx + flip * (bw // 2) - (aw if flip > 0 else 0)
    pygame.draw.rect(surface, C_SKIN, (ax, by + 2, aw, ah))
    wx = ax + (aw if flip > 0 else -3)
    pygame.draw.rect(surface, C_WEAPON, (wx, by + ah // 2, 3, ah // 2 + 2))

    # Head
    hr = int(w * 0.37)
    hcx, hcy = cx, by - hr + 2 + bob
    pygame.draw.circle(surface, C_HEAD, (hcx, hcy), hr)

    # Pointed hat
    hat_pts = [
        (hcx - hr + 3, hcy - hr // 2),
        (hcx + hr - 3, hcy - hr // 2),
        (hcx + flip * 4, hcy - hr * 2),
    ]
    pygame.draw.polygon(surface, C_HAT, hat_pts)

    # Eyes — X-eyes when stunned
    ey = hcy - 2
    for ex in (hcx - 4, hcx + 4):
        if stunned:
            pygame.draw.line(surface, C_EYE, (ex - 2, ey - 2), (ex + 2, ey + 2), 1)
            pygame.draw.line(surface, C_EYE, (ex + 2, ey - 2), (ex - 2, ey + 2), 1)
        else:
            pygame.draw.circle(surface, C_EYE, (ex, ey), 2)
            pygame.draw.circle(surface, (255, 255, 255), (ex + 1, ey - 1), 1)

    # Mouth
    pygame.draw.line(surface, C_MOUTH, (hcx - 3, hcy + hr // 3), (hcx + 3, hcy + hr // 3), 1)

    _hurt_flash(surface, rect, invincibility_frames)


# ────────────────────────────────────────────────────────────────── BAT ────
#
#  Flying enemy: leathery wings that flap, glowing red eyes.
#  Bat (24 × 24)


def draw_bat(
    surface: pygame.Surface,
    rect: pygame.Rect,
    facing_right: bool,
    animation_frame: int,
    ai_state,
    invincibility_frames: int,
    ticks: int,
) -> None:
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    cx, cy = rect.centerx, rect.centery

    C_BODY = (55, 50, 75)
    C_MEM = (72, 62, 95)  # wing membrane
    C_EDGE = (38, 33, 58)  # wing outline
    C_EYE = (215, 55, 55)
    C_EAR = (80, 68, 100)

    _shadow(surface, rect)

    # Wing flap: 0=mid 1=up 2=mid 3=down
    droop_table = [0, -1, 0, 1]
    droop = droop_table[animation_frame % 4] * (h // 3)
    spread = int(w * 0.9)

    # Left wing
    lw_pts = [
        (cx - w // 6, cy - 2),
        (cx - w // 4, cy + h // 4),
        (x - spread // 3, cy + h // 4 + droop),
        (x - spread // 3 - 2, cy + droop),
    ]
    pygame.draw.polygon(surface, C_MEM, lw_pts)
    pygame.draw.polygon(surface, C_EDGE, lw_pts, 1)

    # Right wing
    rw_pts = [
        (cx + w // 6, cy - 2),
        (cx + w // 4, cy + h // 4),
        (x + w + spread // 3, cy + h // 4 + droop),
        (x + w + spread // 3 + 2, cy + droop),
    ]
    pygame.draw.polygon(surface, C_MEM, rw_pts)
    pygame.draw.polygon(surface, C_EDGE, rw_pts, 1)

    # Body oval
    br, bry = w // 3, h // 3
    pygame.draw.ellipse(surface, C_BODY, (cx - br, cy - bry, br * 2, bry * 2))

    # Ears
    for side, ex in ((-1, cx - 5), (1, cx + 5)):
        pygame.draw.polygon(
            surface,
            C_EAR,
            [
                (ex, cy - bry),
                (ex + side * 5, cy - bry - 7),
                (ex + side * 1, cy - bry - 1),
            ],
        )

    # Eyes
    for ex in (cx - 4, cx + 4):
        pygame.draw.circle(surface, C_EYE, (ex, cy - 1), 2)

    _hurt_flash(surface, rect, invincibility_frames)


# ──────────────────────────────────────────────────────────────── SLIME ────
#
#  Slow blob: squishes wide when walking, glossy highlight, wobbly eyes.
#  Slime (40 × 32)


def draw_slime(
    surface: pygame.Surface,
    rect: pygame.Rect,
    facing_right: bool,
    animation_frame: int,
    ai_state,
    invincibility_frames: int,
    ticks: int,
) -> None:
    from entities.enemy import EnemyAIState

    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    cx = rect.centerx

    C_BODY = (120, 80, 188)
    C_SHINE = (168, 128, 228)
    C_EYE = (240, 240, 255)
    C_PUPIL = (28, 18, 58)

    _shadow(surface, rect)

    moving = ai_state in (EnemyAIState.PATROL, EnemyAIState.CHASE)
    squish = moving and (animation_frame % 2 == 1)

    bw = int(w * 1.04) if squish else int(w * 0.88)
    bh = int(h * 0.78) if squish else int(h * 0.94)
    bx = cx - bw // 2
    by = y + h - bh  # always touches floor

    # Main body
    pygame.draw.ellipse(surface, C_BODY, (bx, by, bw, bh))

    # Top bump
    bump_w = bw // 2
    bump_h = bh // 3
    pygame.draw.ellipse(surface, C_BODY, (cx - bump_w // 2, by - bump_h // 2, bump_w, bump_h))

    # Shine
    sw, sh = bw // 5, bh // 6
    pygame.draw.ellipse(surface, C_SHINE, (bx + bw // 5, by + bh // 6, sw, sh))

    # Eyes
    eye_cy = by + bh // 3
    pupil_ox = 1 if facing_right else -1
    for ex in (cx - bw // 4, cx + bw // 4):
        pygame.draw.ellipse(surface, C_EYE, (ex - 4, eye_cy - 4, 8, 8))
        pygame.draw.circle(surface, C_PUPIL, (ex + pupil_ox, eye_cy), 2)

    _hurt_flash(surface, rect, invincibility_frames)


# ──────────────────────────────────────────────────────────────── SKELETON ────
#
#  Undead humanoid: visible ribcage, glowing green eye sockets, bony joints.
#  Skeleton (32 × 56)


def draw_skeleton(
    surface: pygame.Surface,
    rect: pygame.Rect,
    facing_right: bool,
    animation_frame: int,
    ai_state,
    invincibility_frames: int,
    ticks: int,
) -> None:
    from entities.enemy import EnemyAIState

    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    cx = rect.centerx
    flip = 1 if facing_right else -1

    C_BONE = (215, 205, 185)
    C_JOINT = (150, 138, 120)
    C_EYE = (15, 15, 15)
    C_GLOW = (75, 200, 95)
    C_TEETH = (255, 255, 255)

    _shadow(surface, rect)

    moving = ai_state in (EnemyAIState.PATROL, EnemyAIState.CHASE)
    stunned = ai_state == EnemyAIState.STUNNED
    bob = -1 if (moving and animation_frame % 2 == 0) else 0

    bw = max(w // 7, 3)  # bone width
    base = y + h  # floor

    # Proportions
    leg_h = int(h * 0.28)
    torso_h = int(h * 0.32)
    arm_h = int(torso_h * 0.85)
    head_r = int(w * 0.37)

    # Legs
    for i, lx in enumerate((cx - bw - 1, cx + 1)):
        walk = (
            ((-3 if i == 0 else 3) if animation_frame % 2 == 0 else (3 if i == 0 else -3))
            if moving
            else 0
        )
        femur_top = base - leg_h + bob
        pygame.draw.rect(surface, C_BONE, (lx, femur_top, bw, leg_h // 2))
        pygame.draw.circle(surface, C_JOINT, (lx + bw // 2, femur_top + leg_h // 2), bw // 2 + 1)
        shin_x = lx + walk // 2
        pygame.draw.rect(surface, C_BONE, (shin_x, femur_top + leg_h // 2, bw, leg_h // 2))
        pygame.draw.rect(surface, C_BONE, (shin_x - 1, base - 3 + bob, bw + 2, 3))

    # Torso / ribcage
    torso_top = base - leg_h - torso_h + bob
    torso_w = int(w * 0.70)
    # Spine
    pygame.draw.line(surface, C_BONE, (cx, torso_top), (cx, torso_top + torso_h), max(bw - 1, 2))
    # Three rib pairs
    for i in range(3):
        ry = torso_top + int(torso_h * (0.18 + i * 0.28))
        rw = int(torso_w * (0.88 - i * 0.12))
        pygame.draw.line(surface, C_BONE, (cx - rw // 2, ry), (cx + rw // 2, ry), 1)

    # Arms
    for side in (-1, 1):
        ax = cx + side * int(w * 0.38) - (bw if side > 0 else 0)
        arm_off = (-2 if side == flip else 2) if moving else 0
        pygame.draw.rect(surface, C_BONE, (ax, torso_top + 2 + arm_off, bw, arm_h // 2))
        pygame.draw.circle(
            surface, C_JOINT, (ax + bw // 2, torso_top + 2 + arm_off + arm_h // 2), bw // 2 + 1
        )
        pygame.draw.rect(
            surface,
            C_BONE,
            (ax - arm_off // 2, torso_top + 2 + arm_off + arm_h // 2, bw, arm_h // 2),
        )

    # Skull
    skull_cy = torso_top - head_r + bob
    tilt = 6 if stunned else 0
    pygame.draw.circle(surface, C_BONE, (cx + tilt, skull_cy), head_r)

    # Jaw
    jaw_h = head_r // 2
    jaw_pts = [
        (cx + tilt - head_r + 4, skull_cy + 2),
        (cx + tilt + head_r - 4, skull_cy + 2),
        (cx + tilt + head_r - 6, skull_cy + jaw_h),
        (cx + tilt - head_r + 6, skull_cy + jaw_h),
    ]
    pygame.draw.polygon(surface, C_BONE, jaw_pts)
    for tx in (cx + tilt - 4, cx + tilt + 1):
        pygame.draw.rect(surface, C_TEETH, (tx, skull_cy + jaw_h - 3, 3, 3))

    # Eye sockets
    for ex in (cx + tilt - 7, cx + tilt + 3):
        pygame.draw.ellipse(surface, C_EYE, (ex, skull_cy - 5, 6, 5))
        pygame.draw.circle(surface, C_GLOW, (ex + 3, skull_cy - 3), 1)

    _hurt_flash(surface, rect, invincibility_frames)


# ────────────────────────────────────────────────────────────────── WOLF ────
#
#  Fast quadruped: four legs, snout, perked ears, wagging tail.
#  Wolf (48 × 32)


def draw_wolf(
    surface: pygame.Surface,
    rect: pygame.Rect,
    facing_right: bool,
    animation_frame: int,
    ai_state,
    invincibility_frames: int,
    ticks: int,
) -> None:
    from entities.enemy import EnemyAIState

    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    cx, cy = rect.centerx, rect.centery
    flip = 1 if facing_right else -1

    C_FUR = (92, 72, 52)
    C_DARK = (52, 40, 28)
    C_BELLY = (142, 118, 92)
    C_EYE = (198, 158, 38)
    C_NOSE = (28, 22, 22)
    C_TEETH = (242, 238, 225)

    _shadow(surface, rect)

    moving = ai_state in (EnemyAIState.PATROL, EnemyAIState.CHASE)
    attacking = ai_state == EnemyAIState.ATTACK

    body_w = int(w * 0.58)
    body_h = int(h * 0.52)
    leg_w = max(w // 10, 3)
    leg_h = int(h * 0.44)
    head_w = int(w * 0.30)
    head_h = int(h * 0.56)

    if facing_right:
        head_x = x + w - head_w - 2
        body_x = x + 4
        tail_x = x + 6
    else:
        head_x = x + 2
        body_x = x + head_w - 4
        tail_x = x + w - 6

    body_y = y + h - body_h - leg_h + 4

    # Tail (at the back)
    sway = (animation_frame % 2) * 4 - 2 if moving else 0
    tail_pts = [
        (tail_x, body_y + body_h // 2),
        (tail_x - flip * 8, body_y - 2 + sway),
        (tail_x - flip * 14, body_y - 10 + sway),
    ]
    pygame.draw.lines(surface, C_DARK, False, tail_pts, 4)

    # Four legs
    leg_xs = [
        body_x + body_w // 5,
        body_x + body_w * 2 // 5,
        body_x + body_w * 3 // 5,
        body_x + body_w * 4 // 5,
    ]
    for i, lx in enumerate(leg_xs):
        walk = (
            ((-3 if i % 2 == 0 else 3) if animation_frame % 2 == 0 else (3 if i % 2 == 0 else -3))
            if moving
            else 0
        )
        pygame.draw.rect(
            surface, C_DARK, (lx - leg_w // 2, body_y + body_h - 2, leg_w, leg_h + walk)
        )

    # Body
    pygame.draw.rect(surface, C_FUR, (body_x, body_y, body_w, body_h), border_radius=4)
    # Belly patch
    belly_y = body_y + body_h // 3
    pygame.draw.ellipse(
        surface, C_BELLY, (body_x + body_w // 5, belly_y, body_w * 3 // 5, body_h // 2)
    )

    # Head
    head_y = y + h - head_h - leg_h + 2
    pygame.draw.rect(surface, C_FUR, (head_x, head_y, head_w, head_h), border_radius=3)

    # Snout
    snout_h = head_h // 3
    snout_w = head_w // 2
    snout_x = (head_x + head_w - snout_w + 2) if facing_right else (head_x - 2)
    snout_y = head_y + head_h - snout_h - 2
    pygame.draw.rect(surface, C_BELLY, (snout_x, snout_y, snout_w, snout_h), border_radius=2)

    # Nose
    nose_x = snout_x + (snout_w - 4 if facing_right else 0)
    pygame.draw.ellipse(surface, C_NOSE, (nose_x, snout_y + 1, 4, 3))

    # Teeth (only when attacking)
    if attacking:
        tooth_x = snout_x + (snout_w if facing_right else -3)
        pygame.draw.rect(surface, C_TEETH, (tooth_x, snout_y + snout_h // 2, 3, 4))

    # Ears
    ear_base_y = head_y + 3
    if facing_right:
        ear_xs = (head_x + 2, head_x + head_w // 2)
    else:
        ear_xs = (head_x + head_w - 8, head_x + head_w // 2 - 2)
    for ex in ear_xs:
        pygame.draw.polygon(
            surface, C_DARK, [(ex, ear_base_y), (ex + 4, ear_base_y), (ex + 2, ear_base_y - 6)]
        )

    # Eye
    eye_y = head_y + head_h // 4
    eye_x = head_x + (head_w * 2 // 3 if facing_right else head_w // 3)
    pygame.draw.circle(surface, C_EYE, (eye_x, eye_y), 2)
    pygame.draw.circle(surface, (0, 0, 0), (eye_x, eye_y), 1)

    _hurt_flash(surface, rect, invincibility_frames)


# ──────────────────────────────────────────────────────────── NPC HELPERS ────


def _npc_base(
    surface: pygame.Surface,
    rect: pygame.Rect,
    facing_right: bool,
    animation_frame: int,
    body_color: tuple,
    skin_color: tuple,
    leg_color: tuple,
) -> tuple:
    """
    Draw a shared humanoid base (legs, body, arms, head) and return
    layout coordinates for the caller to add accessories on top.

    Returns: (cx, bx, by, bw, bh, hcx, hcy, hr)
    """
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    cx = rect.centerx

    bob = -1 if animation_frame % 2 == 0 else 0

    _shadow(surface, rect)

    # Legs
    lw = max(w // 5, 4)
    lh = h // 4
    ly = y + h - lh
    for i, lx in enumerate((cx - lw - 1, cx + 1)):
        walk = (-2 if i == 0 else 2) if animation_frame % 2 == 0 else (2 if i == 0 else -2)
        pygame.draw.rect(surface, leg_color, (lx, ly + walk, lw, lh))

    # Body
    bw = int(w * 0.72)
    bh = int(h * 0.36)
    bx = cx - bw // 2
    by = y + h - lh - bh + bob
    pygame.draw.rect(surface, body_color, (bx, by, bw, bh))

    # Arms
    aw = max(w // 6, 3)
    ah = bh - 4
    for side in (-1, 1):
        ax = cx + side * (bw // 2 + 1) - (aw if side > 0 else 0)
        arm_off = (-1 if side == 1 else 1) if animation_frame % 2 == 0 else (1 if side == 1 else -1)
        pygame.draw.rect(surface, skin_color, (ax, by + 2 + arm_off, aw, ah))

    # Head
    hr = int(w * 0.37)
    hcx, hcy = cx, by - hr + 2 + bob
    pygame.draw.circle(surface, skin_color, (hcx, hcy), hr)

    # Eyes
    eye_y = hcy - 2
    ox = 1 if facing_right else -1
    for ex in (hcx - 4, hcx + 4):
        pygame.draw.circle(surface, (28, 22, 18), (ex, eye_y), 2)
        pygame.draw.circle(surface, (255, 255, 255), (ex + ox, eye_y - 1), 1)

    return cx, bx, by, bw, bh, hcx, hcy, hr


# ─────────────────────────────────────────────────── NPC: MISSION GIVER ────
#
#  Golden-cloaked figure with a scroll — quest givers.


def draw_npc_mission_giver(
    surface: pygame.Surface,
    rect: pygame.Rect,
    facing_right: bool,
    animation_frame: int,
    ticks: int,
) -> None:
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    flip = 1 if facing_right else -1

    cx, bx, by, bw, bh, hcx, hcy, hr = _npc_base(
        surface,
        rect,
        facing_right,
        animation_frame,
        body_color=(175, 138, 58),
        skin_color=(218, 182, 138),
        leg_color=(138, 102, 42),
    )

    # Cloak over body
    cloak_pts = [
        (bx - 2, by),
        (bx + bw + 2, by),
        (bx + bw + 6, by + bh),
        (bx - 6, by + bh),
    ]
    pygame.draw.polygon(surface, (128, 92, 28), cloak_pts)
    pygame.draw.line(surface, (255, 212, 58), (bx - 2, by + 2), (bx + bw + 2, by + 2), 1)

    # Scroll in forward hand
    sx = cx + flip * (bw // 2 + 4)
    sy = by + bh // 4
    pygame.draw.rect(surface, (218, 198, 148), (sx, sy, 5, 12))
    pygame.draw.circle(surface, (198, 178, 128), (sx + 2, sy), 3)
    pygame.draw.circle(surface, (198, 178, 128), (sx + 2, sy + 12), 3)


# ────────────────────────────────────────────────────────── NPC: SHOP ────
#
#  Green-aproned merchant carrying a coin bag.


def draw_npc_shop(
    surface: pygame.Surface,
    rect: pygame.Rect,
    facing_right: bool,
    animation_frame: int,
    ticks: int,
) -> None:
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    flip = 1 if facing_right else -1

    cx, bx, by, bw, bh, hcx, hcy, hr = _npc_base(
        surface,
        rect,
        facing_right,
        animation_frame,
        body_color=(48, 175, 88),
        skin_color=(182, 222, 168),
        leg_color=(38, 138, 68),
    )

    # Apron
    apron_pts = [
        (cx - bw // 4, by + 2),
        (cx + bw // 4, by + 2),
        (cx + bw // 3, by + bh),
        (cx - bw // 3, by + bh),
    ]
    pygame.draw.polygon(surface, (198, 228, 198), apron_pts)

    # Coin bag
    bx2 = cx + flip * (bw // 2 + 2)
    by2 = by + bh // 3
    pygame.draw.circle(surface, (198, 168, 48), (bx2 + 3, by2 + 5), 5)
    pygame.draw.rect(surface, (158, 128, 38), (bx2, by2, 6, 4))
    # Coin glint
    pygame.draw.line(surface, (255, 218, 0), (bx2 + 3, by2 + 1), (bx2 + 3, by2 + 9), 1)


# ──────────────────────────────────────────────────────── NPC: TUTORIAL ────
#
#  Blue-robed elder with a glowing staff.


def draw_npc_tutorial(
    surface: pygame.Surface,
    rect: pygame.Rect,
    facing_right: bool,
    animation_frame: int,
    ticks: int,
) -> None:
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    flip = 1 if facing_right else -1

    cx, bx, by, bw, bh, hcx, hcy, hr = _npc_base(
        surface,
        rect,
        facing_right,
        animation_frame,
        body_color=(58, 108, 198),
        skin_color=(168, 192, 232),
        leg_color=(48, 88, 168),
    )

    # Robe over body
    robe_pts = [
        (bx, by),
        (bx + bw, by),
        (bx + bw + 4, by + bh),
        (bx - 4, by + bh),
    ]
    pygame.draw.polygon(surface, (48, 92, 178), robe_pts)

    # Staff (bobs gently)
    staff_bob = -2 if animation_frame % 2 == 0 else 0
    sx = cx + flip * (bw // 2 + 6)
    stop = by - hr - 12 + staff_bob
    sbot = by + bh + 4
    pygame.draw.line(surface, (178, 142, 78), (sx, stop), (sx, sbot), 2)
    # Orb on tip
    pygame.draw.circle(surface, (255, 238, 98), (sx, stop), 4)
    pygame.draw.circle(surface, (255, 198, 48), (sx, stop), 2)


# ──────────────────────────────────────────────────────────── NPC: LORE ────
#
#  Gray-robed scholar reading a book.


def draw_npc_lore(
    surface: pygame.Surface,
    rect: pygame.Rect,
    facing_right: bool,
    animation_frame: int,
    ticks: int,
) -> None:
    x, y, w, h = rect.x, rect.y, rect.width, rect.height

    cx, bx, by, bw, bh, hcx, hcy, hr = _npc_base(
        surface,
        rect,
        facing_right,
        animation_frame,
        body_color=(138, 128, 158),
        skin_color=(198, 192, 212),
        leg_color=(108, 102, 128),
    )

    # Book held in front
    book_x = cx - 8
    book_y = by + bh // 5
    pygame.draw.rect(surface, (178, 128, 78), (book_x, book_y, 16, 12))
    pygame.draw.line(
        surface, (238, 232, 218), (book_x + 7, book_y + 1), (book_x + 7, book_y + 10), 1
    )
    for i in range(3):
        pygame.draw.line(
            surface,
            (98, 88, 78),
            (book_x + 2, book_y + 2 + i * 3),
            (book_x + 6, book_y + 2 + i * 3),
            1,
        )


# ─────────────────────────────────────────────────────────── PUBLIC API ────


def draw_enemy(
    surface: pygame.Surface,
    enemy,
    screen_rect: pygame.Rect,
    ticks: int,
) -> None:
    """Render one enemy to surface at the given camera-space rect.

    Uses sprite sheet if an AnimationStateMachine is attached (enemy.anim_sm),
    otherwise falls back to procedural primitive rendering.
    """
    from entities.enemy import EnemyType

    # ── Sprite path ────────────────────────────────────────────────────────
    anim_sm = getattr(enemy, "anim_sm", None)
    if anim_sm is not None:
        facing = 1 if enemy.facing_right else -1
        frame = anim_sm.get_frame(facing)
        if frame is not None:
            surface.blit(frame, screen_rect)
            _hurt_flash(surface, screen_rect, enemy.health_state.invincibility_frames)
            return

    # ── Procedural fallback ────────────────────────────────────────────────
    inv = enemy.health_state.invincibility_frames
    fr = enemy.facing_right
    af = enemy.animation_frame
    st = enemy.ai_state

    t = enemy.enemy_type
    if t == EnemyType.GOBLIN:
        draw_goblin(surface, screen_rect, fr, af, st, inv, ticks)
    elif t == EnemyType.BAT:
        draw_bat(surface, screen_rect, fr, af, st, inv, ticks)
    elif t == EnemyType.SLIME:
        draw_slime(surface, screen_rect, fr, af, st, inv, ticks)
    elif t == EnemyType.SKELETON:
        draw_skeleton(surface, screen_rect, fr, af, st, inv, ticks)
    elif t == EnemyType.WOLF:
        draw_wolf(surface, screen_rect, fr, af, st, inv, ticks)
    else:
        pygame.draw.rect(surface, (200, 100, 100), screen_rect)


def draw_npc(
    surface: pygame.Surface,
    npc,
    npc_def,
    screen_rect: pygame.Rect,
    ticks: int,
) -> None:
    """Render one NPC to surface at the given camera-space rect."""
    from entities.npc import NPCType

    fr = npc.facing == 1
    af = npc.animation_frame

    if npc_def is None:
        pygame.draw.rect(surface, (200, 200, 200), screen_rect)
        return

    t = npc_def.npc_type
    if t == NPCType.MISSION_GIVER:
        draw_npc_mission_giver(surface, screen_rect, fr, af, ticks)
    elif t == NPCType.SHOP:
        draw_npc_shop(surface, screen_rect, fr, af, ticks)
    elif t == NPCType.TUTORIAL:
        draw_npc_tutorial(surface, screen_rect, fr, af, ticks)
    else:
        draw_npc_lore(surface, screen_rect, fr, af, ticks)
