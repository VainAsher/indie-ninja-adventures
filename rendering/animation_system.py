"""
Unified Animation System

Provides a data-driven, zero-duplication animation pipeline for all character
types (player, enemies, NPCs).

Architecture
------------
AnimationRegistry   — global store, loaded once at startup per character type.
                      Multiple entity instances share the same frame lists.
AnimationStateMachine — per-entity, owns ONLY current state name + timer.
                        Zero frame data; references shared registry data.

Usage
-----
Startup (once):
    from rendering.animation_system import AnimationRegistry, register_all_characters
    register_all_characters(assets_root)          # loads all sprite sheets

Per enemy spawn:
    enemy.anim_sm = AnimationRegistry.make_state_machine("goblin")

Per physics tick (60 Hz inside EnemyManager.update / NPC update):
    anim_state = ENEMY_AI_TO_ANIM[enemy.ai_state.value]
    enemy.anim_sm.transition(anim_state)
    enemy.anim_sm.update(dt * 1000)

Per render frame:
    frame = enemy.anim_sm.get_frame(1 if enemy.facing_right else -1)
    if frame:
        surface.blit(frame, screen_rect)
    else:
        procedural_fallback(surface, enemy, screen_rect)

Performance contract
--------------------
- No image loading after startup
- No pygame.transform calls after startup (frames pre-scaled at registration)
- No per-frame allocations
- Multiple entities of same type share identical list references (not copies)
"""

from __future__ import annotations

from pathlib import Path

import pygame  # type: ignore[import]

from rendering.sprite_manager import SpriteAnimation, SpriteFrame, SpriteSheet

# ---------------------------------------------------------------------------
# AI state → animation state name mappings
# ---------------------------------------------------------------------------

#: Map EnemyAIState.value strings to animation state names.
ENEMY_AI_TO_ANIM: dict[str, str] = {
    "idle":    "idle",
    "patrol":  "walk",
    "chase":   "run",
    "attack":  "attack",
    "stunned": "stunned",
    "dead":    "death",
}

# ---------------------------------------------------------------------------
# Per-character animation definitions
# Format: {state_name: (filename, frame_count, fps, loop)}
# ---------------------------------------------------------------------------

#: Player — sheets live in assets/sprites/player/
PLAYER_ANIM_DEFS: dict[str, tuple[str, int, int, bool]] = {
    "idle":            ("idle_spritesheet.png",         2,  8,  True),
    "walk":            ("walk_spritesheet.png",         4, 10,  True),
    "run":             ("run_spritesheet.png",          6, 12,  True),
    "slow_walk":       ("walk_spritesheet.png",         4,  8,  True),
    "jump":            ("jumpfall_spritesheet.png",     1, 10,  False),
    "fall":            ("jumpfall_spritesheet.png",     1, 10,  False),
    "crouch":          ("idle_spritesheet.png",         2,  6,  True),
    "dash":            ("run_spritesheet.png",          6, 20,  True),
    "wall_slide":      ("jumpfall_spritesheet.png",     2,  8,  True),
    "wall_hang":       ("jumpfall_spritesheet.png",     2,  6,  True),
    "ceiling_hang":    ("jumpfall_spritesheet.png",     2,  6,  True),
    "air_spin":        ("jumpfall_spritesheet.png",     2, 10,  True),
    "hurt":            ("hurt_spritesheet.png",         3, 12,  True),   # loop while i-frames active
    "hurt2":           ("hurt_spritesheet.png",         3, 12,  True),
    "death":           ("death_spritesheet.png",        5, 12,  False),
    "attack":          ("attack-sword_spritesheet.png", 6, 15,  False),
    "slash1":          ("attack-sword_spritesheet.png", 6, 15,  False),
    "slash2":          ("attack-sword_spritesheet.png", 6, 15,  False),
    "slash3":          ("attack-sword_spritesheet.png", 6, 15,  False),
    "slash_air":       ("attack-sword_spritesheet.png", 6, 15,  False),
    "jump_slash":      ("attack-sword_spritesheet.png", 6, 15,  False),
    "throw_ground":    ("attack-sword_spritesheet.png", 4, 12,  False),
    "throw_crouch":    ("attack-sword_spritesheet.png", 4, 12,  False),
    "throw_air":       ("attack-sword_spritesheet.png", 4, 12,  False),
    "teleport":        ("attack-sword_spritesheet.png", 4, 12,  False),
    "ninjutsu_hand":   ("attack-sword_spritesheet.png", 4, 10,  False),
    "ninjutsu_summon": ("attack-sword_spritesheet.png", 4, 10,  False),
}

GOBLIN_ANIM_DEFS: dict[str, tuple[str, int, int, bool]] = {
    "idle":    ("idle_spritesheet.png",   2,  8, True),
    "walk":    ("walk_spritesheet.png",   4, 10, True),
    "run":     ("run_spritesheet.png",    4, 12, True),
    "attack":  ("attack_spritesheet.png", 4, 12, False),
    "hurt":    ("hurt_spritesheet.png",   2, 10, False),
    "stunned": ("hurt_spritesheet.png",   2,  6, True),
    "death":   ("death_spritesheet.png",  4, 10, False),
}

BAT_ANIM_DEFS: dict[str, tuple[str, int, int, bool]] = {
    # Bat uses its idle sheet for all movement (it flies)
    "idle":    ("idle_spritesheet.png",   4, 12, True),
    "walk":    ("idle_spritesheet.png",   4, 12, True),
    "run":     ("idle_spritesheet.png",   4, 16, True),
    "attack":  ("attack_spritesheet.png", 4, 14, False),
    "hurt":    ("hurt_spritesheet.png",   2, 10, False),
    "stunned": ("hurt_spritesheet.png",   2,  6, True),
    "death":   ("death_spritesheet.png",  4, 10, False),
}

SLIME_ANIM_DEFS: dict[str, tuple[str, int, int, bool]] = {
    "idle":    ("idle_spritesheet.png",   2,  6, True),
    "walk":    ("walk_spritesheet.png",   4,  8, True),
    "run":     ("walk_spritesheet.png",   4, 10, True),
    "attack":  ("attack_spritesheet.png", 4, 10, False),
    "hurt":    ("hurt_spritesheet.png",   2, 10, False),
    "stunned": ("hurt_spritesheet.png",   2,  6, True),
    "death":   ("death_spritesheet.png",  4,  8, False),
}

SKELETON_ANIM_DEFS: dict[str, tuple[str, int, int, bool]] = {
    "idle":    ("idle_spritesheet.png",   2,  8, True),
    "walk":    ("walk_spritesheet.png",   4, 10, True),
    "run":     ("walk_spritesheet.png",   4, 12, True),
    "attack":  ("attack_spritesheet.png", 4, 12, False),
    "hurt":    ("hurt_spritesheet.png",   2, 10, False),
    "stunned": ("hurt_spritesheet.png",   2,  6, True),
    "death":   ("death_spritesheet.png",  4, 10, False),
}

WOLF_ANIM_DEFS: dict[str, tuple[str, int, int, bool]] = {
    "idle":    ("idle_spritesheet.png",   2,  8, True),
    "walk":    ("walk_spritesheet.png",   4, 10, True),
    "run":     ("run_spritesheet.png",    6, 14, True),
    "attack":  ("attack_spritesheet.png", 4, 14, False),
    "hurt":    ("hurt_spritesheet.png",   2, 10, False),
    "stunned": ("hurt_spritesheet.png",   2,  6, True),
    "death":   ("death_spritesheet.png",  4, 10, False),
}

NPC_ANIM_DEFS: dict[str, tuple[str, int, int, bool]] = {
    "idle": ("idle_spritesheet.png", 2, 6, True),
    "walk": ("walk_spritesheet.png", 4, 8, True),
}

# Maps EnemyType.value → (anim_defs, hitbox_size)
_ENEMY_REGISTRY_CONFIG: dict[str, tuple[dict, tuple[int, int]]] = {
    "goblin":   (GOBLIN_ANIM_DEFS,   (32, 48)),
    "bat":      (BAT_ANIM_DEFS,      (24, 24)),
    "slime":    (SLIME_ANIM_DEFS,    (40, 32)),
    "skeleton": (SKELETON_ANIM_DEFS, (32, 56)),
    "wolf":     (WOLF_ANIM_DEFS,     (48, 32)),
}

# Maps NPCType.value → (sprite subdir, anim_defs, hitbox_size)
_NPC_REGISTRY_CONFIG: dict[str, tuple[str, dict, tuple[int, int]]] = {
    "mission_giver": ("npc_mission_giver", NPC_ANIM_DEFS, (32, 48)),
    "shop":          ("npc_shop",          NPC_ANIM_DEFS, (32, 48)),
    "tutorial":      ("npc_tutorial",      NPC_ANIM_DEFS, (32, 48)),
    "lore":          ("npc_lore",          NPC_ANIM_DEFS, (32, 48)),
}


# ---------------------------------------------------------------------------
# AnimationStateMachine
# ---------------------------------------------------------------------------

class AnimationStateMachine:
    """
    Lightweight per-entity animation controller.

    Owns ONLY: current state name + the timestamp when that state was entered.
    Frame data lives in AnimationRegistry — shared, zero duplication.

    Timer design: records pygame.time.get_ticks() on every state transition,
    then computes elapsed time on demand in get_frame().  This means:
    - No update() call needed anywhere — always correct at call time
    - Non-looping animations (attack, hurt) always start from frame 0
    - Exactly matches how SpriteManager already works, but with reset-on-transition

    Constraints:
    - No Surface copies at construction or during get_frame()
    - get_frame() is O(1) — dict lookup + integer arithmetic
    """

    __slots__ = ("_state", "_entry_ms", "_anims", "_flip_cache")

    def __init__(
        self,
        anims: dict[str, SpriteAnimation],
        flip_cache: dict[tuple[str, int], list[SpriteFrame]],
    ) -> None:
        """
        Args:
            anims: Shared animation metadata (state → SpriteAnimation).
            flip_cache: Shared frame data ((state, facing) → list[SpriteFrame]).
            Both are REFERENCES to registry data — never copy them.
        """
        self._state: str = "idle"
        self._entry_ms: int = 0  # pygame.time.get_ticks() at last transition
        self._anims: dict[str, SpriteAnimation] = anims
        self._flip_cache: dict[tuple[str, int], list[SpriteFrame]] = flip_cache

    # ── State control ──────────────────────────────────────────────────────

    def transition(self, new_state: str) -> None:
        """
        Switch to new_state and record entry time.
        No-op if already in that state or state has no registered animation.
        """
        if new_state == self._state:
            return
        if new_state in self._anims:
            self._state = new_state
            self._entry_ms = pygame.time.get_ticks()

    # ── Frame access ───────────────────────────────────────────────────────

    def get_frame(self, facing: int = 1) -> pygame.Surface | None:
        """
        Return the current animation frame surface.

        Args:
            facing: 1 = right (default), -1 = left.

        Returns:
            pygame.Surface, or None if no frames are registered.
            Never allocates; always returns a pre-loaded surface.
        """
        frames = self._flip_cache.get((self._state, facing))
        if not frames:
            # Graceful fallback: idle in requested facing, then idle right
            frames = (
                self._flip_cache.get(("idle", facing))
                or self._flip_cache.get(("idle", 1))
            )
        if not frames:
            return None

        count = len(frames)
        if count == 1:
            return frames[0].surface

        anim = self._anims.get(self._state) or self._anims.get("idle")
        if anim is None:
            return frames[0].surface

        elapsed_ms = pygame.time.get_ticks() - self._entry_ms
        frame_dur_ms = 1000.0 / anim.fps
        idx = int(elapsed_ms / frame_dur_ms)
        idx = (idx % count) if anim.loop else min(idx, count - 1)
        return frames[idx].surface

    # ── State inspection ───────────────────────────────────────────────────

    @property
    def state(self) -> str:
        """Current animation state name."""
        return self._state

    @property
    def finished(self) -> bool:
        """
        True when a non-looping animation has fully played through.
        Always False for looping animations.
        """
        anim = self._anims.get(self._state)
        if anim is None or anim.loop:
            return False
        frames = self._flip_cache.get((self._state, 1)) or []
        total_ms = (1000.0 / anim.fps) * len(frames)
        elapsed_ms = pygame.time.get_ticks() - self._entry_ms
        return elapsed_ms >= total_ms


# ---------------------------------------------------------------------------
# AnimationRegistry
# ---------------------------------------------------------------------------

class AnimationRegistry:
    """
    Global animation data store. Load once at startup, zero duplication.

    All entities of the same character type share identical list references
    (not copies). A goblin with 20 instances uses the same frame lists —
    only the AnimationStateMachine (state + float timer) is per-instance.
    """

    # _anims[char_type][state] = SpriteAnimation  (fps, loop, frame metadata)
    _anims: dict[str, dict[str, SpriteAnimation]] = {}
    # _flip_cache[char_type][(state, facing)] = list[SpriteFrame]
    _flip_cache: dict[str, dict[tuple[str, int], list[SpriteFrame]]] = {}

    # ── Registration ───────────────────────────────────────────────────────

    @classmethod
    def register(
        cls,
        char_type: str,
        sprites_dir: Path,
        anim_defs: dict[str, tuple[str, int, int, bool]],
        target_size: tuple[int, int] | None = None,
    ) -> None:
        """
        Load sprite sheets and build frame cache for char_type.
        Call once per character type at game startup.

        Args:
            char_type:   Unique identifier e.g. "goblin", "player".
            sprites_dir: Directory containing PNG sprite sheets.
            anim_defs:   {state: (filename, frame_count, fps, loop)}.
            target_size: If given, ALL frames are scaled to (w, h) at load
                         time. Zero runtime cost after startup. Use for
                         enemies/NPCs so the render loop needs no transform.
        """
        anims: dict[str, SpriteAnimation] = {}
        flip_cache: dict[tuple[str, int], list[SpriteFrame]] = {}

        for state, (filename, frame_count, fps, loop) in anim_defs.items():
            fallback_size = target_size or (32, 48)
            frames_r, frames_l = cls._load_state_frames(
                sprites_dir / filename, state, frame_count,
                char_type, target_size, fallback_size,
            )
            anims[state] = SpriteAnimation(name=state, frames=frames_r, fps=fps, loop=loop)
            flip_cache[(state, 1)]  = frames_r
            flip_cache[(state, -1)] = frames_l

        cls._anims[char_type]      = anims
        cls._flip_cache[char_type] = flip_cache

    @classmethod
    def _load_state_frames(
        cls,
        filepath: Path,
        state: str,
        frame_count: int,
        char_type: str,
        target_size: tuple[int, int] | None,
        fallback_size: tuple[int, int],
    ) -> tuple[list[SpriteFrame], list[SpriteFrame]]:
        """Load + scale frames for one animation state, with fallback on failure."""
        if not filepath.exists():
            return cls._make_fallback(state, frame_count, fallback_size)
        try:
            raw = SpriteSheet(filepath, frame_count).get_frames()
            # Player jumpfall sheet: frame 0 = falling pose, frame 1 = ascending pose
            # (sheet layout confirmed from sprite asset; vy<0 = ascending uses frame 1)
            if char_type == "player":
                if state == "jump":
                    raw = raw[1:2] if len(raw) > 1 else raw
                elif state == "fall":
                    raw = [raw[0]]
            if target_size is not None:
                raw = [pygame.transform.scale(s, target_size) for s in raw]
            frames_r = [SpriteFrame(surface=s) for s in raw]
            frames_l = [
                SpriteFrame(
                    surface=pygame.transform.flip(f.surface, True, False),
                    offset=f.offset,
                )
                for f in frames_r
            ]
            return frames_r, frames_l
        except (OSError, pygame.error, ValueError) as exc:
            print(f"[AnimationRegistry] Error loading {filepath}: {exc}")
            return cls._make_fallback(state, frame_count, fallback_size)

    @classmethod
    def register_from_sprite_manager(
        cls,
        char_type: str,
        animations: dict[str, SpriteAnimation],
        cache: dict[tuple[str, int], list[SpriteFrame]],
    ) -> None:
        """
        Register pre-loaded data from an existing SpriteManager.
        Uses REFERENCES — zero re-loading, zero duplication.

        Called automatically by SpriteManager after it finishes loading.
        """
        cls._anims[char_type]      = animations
        cls._flip_cache[char_type] = cache

    # ── Factory ────────────────────────────────────────────────────────────

    @classmethod
    def make_state_machine(cls, char_type: str) -> AnimationStateMachine | None:
        """
        Create a per-entity state machine sharing this type's frame data.
        Returns None if char_type was never registered.
        """
        if char_type not in cls._anims:
            return None
        return AnimationStateMachine(
            anims=cls._anims[char_type],
            flip_cache=cls._flip_cache[char_type],
        )

    @classmethod
    def is_registered(cls, char_type: str) -> bool:
        """Return True if char_type has been registered."""
        return char_type in cls._anims

    # ── Internal ───────────────────────────────────────────────────────────

    @classmethod
    def _make_fallback(
        cls,
        state: str,
        frame_count: int,
        size: tuple[int, int],
    ) -> tuple[list[SpriteFrame], list[SpriteFrame]]:
        """Generate coloured placeholder frames when a sprite sheet is missing."""
        _colors: dict[str, tuple[int, int, int]] = {
            "idle":    (80,  80,  180),
            "walk":    (80,  150, 180),
            "run":     (80,  200, 200),
            "jump":    (120, 220, 120),
            "fall":    (180, 180, 80),
            "attack":  (220, 120, 80),
            "hurt":    (220, 80,  80),
            "stunned": (180, 80,  180),
            "death":   (120, 120, 120),
            "patrol":  (100, 160, 200),
            "chase":   (200, 140, 80),
            "dead":    (80,  80,  80),
        }
        color = _colors.get(state, (160, 160, 160))
        w, h = size
        frames_r: list[SpriteFrame] = []
        for i in range(max(1, frame_count)):
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            surf.fill((*color, 220))
            if i % 2 == 0:
                pygame.draw.rect(surf, (255, 255, 255, 40), (0, 0, w, max(1, h // 4)))
            frames_r.append(SpriteFrame(surface=surf))
        frames_l = [
            SpriteFrame(surface=pygame.transform.flip(f.surface, True, False))
            for f in frames_r
        ]
        return frames_r, frames_l


# ---------------------------------------------------------------------------
# Startup registration helper
# ---------------------------------------------------------------------------

def register_all_characters(assets_root: Path) -> None:
    """
    Register all character animation data with AnimationRegistry.
    Call ONCE at game startup, after pygame.display is initialised.

    Player data is registered via SpriteManager (see SpriteManager._load_animations).
    This function handles enemies and NPCs.

    Args:
        assets_root: Project root / assets directory (contains sprites/).
    """
    chars_dir = assets_root / "sprites" / "characters"

    # ── Enemies ────────────────────────────────────────────────────────────
    for enemy_type_val, (anim_defs, hitbox_size) in _ENEMY_REGISTRY_CONFIG.items():
        sprites_dir = chars_dir / enemy_type_val
        AnimationRegistry.register(
            char_type=enemy_type_val,
            sprites_dir=sprites_dir,
            anim_defs=anim_defs,
            target_size=hitbox_size,  # Pre-scale to hitbox — no runtime transform needed
        )

    # ── NPCs ───────────────────────────────────────────────────────────────
    for npc_type_val, (subdir, anim_defs, hitbox_size) in _NPC_REGISTRY_CONFIG.items():
        sprites_dir = chars_dir / subdir
        AnimationRegistry.register(
            char_type=f"npc_{npc_type_val}",
            sprites_dir=sprites_dir,
            anim_defs=anim_defs,
            target_size=hitbox_size,
        )
