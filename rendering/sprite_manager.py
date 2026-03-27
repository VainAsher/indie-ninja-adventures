"""
Sprite Sheet Manager and Animation System

Handles loading and animating sprite sheets for the player character.
Supports horizontal strip sprite sheets with automatic frame extraction.

Sprite sheets location: assets/sprites/player/
"""

from dataclasses import dataclass
from pathlib import Path

import pygame


@dataclass
class SpriteFrame:
    """Single animation frame with optional offset"""

    surface: pygame.Surface
    offset: tuple[int, int] = (0, 0)  # Anchor point offset


@dataclass
class SpriteAnimation:
    """Animation definition with frames and timing"""

    name: str
    frames: list[SpriteFrame]
    fps: int = 12  # Frames per second
    loop: bool = True


class SpriteSheet:
    """
    Sprite sheet loader for horizontal strip sprite sheets

    Usage:
        sheet = SpriteSheet("idle_spritesheet.png", frame_count=2)
        frames = sheet.get_frames()
    """

    def __init__(self, filepath: Path, frame_count: int):
        """
        Load sprite sheet and extract frames

        Args:
            filepath: Path to sprite sheet PNG file
            frame_count: Number of frames in the horizontal strip
        """
        self.filepath = filepath
        self.frame_count = frame_count

        # Load image (works before display mode is set)
        loaded_image = pygame.image.load(str(filepath))

        # Try to convert with alpha, but handle cases where display isn't initialized
        try:
            self.sheet_surface = loaded_image.convert_alpha()
        except pygame.error:
            # Display not initialized yet - just use the loaded image
            self.sheet_surface = loaded_image

        self.sheet_width, self.sheet_height = self.sheet_surface.get_size()
        self.frame_width = self.sheet_width // frame_count
        self.frame_height = self.sheet_height

    def get_frames(self) -> list[pygame.Surface]:
        """Extract all frames from the sprite sheet"""
        frames = []
        for i in range(self.frame_count):
            x = i * self.frame_width
            frame_rect = pygame.Rect(x, 0, self.frame_width, self.frame_height)
            frame_surface = pygame.Surface((self.frame_width, self.frame_height), pygame.SRCALPHA)
            frame_surface.blit(self.sheet_surface, (0, 0), frame_rect)
            frames.append(frame_surface)
        return frames


class SpriteManager:
    """
    Sprite and animation manager for player character

    Loads sprite sheets from assets/sprites/player/ and manages animations.
    Supports automatic flipping for left/right facing.

    Usage:
        sprite_mgr = SpriteManager()
        frame = sprite_mgr.get_frame("run", facing=1, time_ms=pygame.time.get_ticks())
    """

    # Animation definitions: (filename, frame_count, fps, loop)
    ANIMATION_DEFS = {
        "idle": ("idle_spritesheet.png", 2, 8, True),
        "walk": ("walk_spritesheet.png", 4, 10, True),
        "run": ("run_spritesheet.png", 6, 12, True),
        "slow_walk": ("walk_spritesheet.png", 4, 8, True),
        "jump": ("jumpfall_spritesheet.png", 2, 10, False),  # Use first frame
        "fall": ("jumpfall_spritesheet.png", 2, 10, False),  # Use second frame
        "crouch": ("idle_spritesheet.png", 2, 6, True),  # Reuse idle, will scale
        "dash": ("run_spritesheet.png", 6, 20, True),  # Fast run animation
        "wall_slide": ("jumpfall_spritesheet.png", 2, 8, True),  # Reuse jump/fall
        "wall_hang": ("jumpfall_spritesheet.png", 2, 6, True),
        "ceiling_hang": ("jumpfall_spritesheet.png", 2, 6, True),
        "air_spin": ("jumpfall_spritesheet.png", 2, 10, True),
        "hurt": ("hurt_spritesheet.png", 3, 12, False),
        "hurt2": ("hurt_spritesheet.png", 3, 12, False),
        "death": ("death_spritesheet.png", 5, 12, False),
        "attack": ("attack-sword_spritesheet.png", 6, 15, False),
        "slash1": ("attack-sword_spritesheet.png", 6, 15, False),
        "slash2": ("attack-sword_spritesheet.png", 6, 15, False),
        "slash3": ("attack-sword_spritesheet.png", 6, 15, False),
        "slash_air": ("attack-sword_spritesheet.png", 6, 15, False),
        "jump_slash": ("attack-sword_spritesheet.png", 6, 15, False),
        "throw_ground": ("attack-sword_spritesheet.png", 4, 12, False),
        "throw_crouch": ("attack-sword_spritesheet.png", 4, 12, False),
        "throw_air": ("attack-sword_spritesheet.png", 4, 12, False),
        "teleport": ("attack-sword_spritesheet.png", 4, 12, False),
        "ninjutsu_hand": ("attack-sword_spritesheet.png", 4, 10, False),
        "ninjutsu_summon": ("attack-sword_spritesheet.png", 4, 10, False),
    }

    def __init__(self, sprites_dir: Path | None = None):
        """
        Initialize sprite manager

        Args:
            sprites_dir: Path to sprites directory (defaults to assets/sprites/player/)
        """
        if sprites_dir is None:
            project_root = Path(__file__).parent.parent
            sprites_dir = project_root / "assets" / "sprites" / "player"

        self.sprites_dir = sprites_dir
        self.animations: dict[str, SpriteAnimation] = {}
        self.cache: dict[tuple[str, int], list[SpriteFrame]] = {}
        self.fallback_size = (28, 56)  # Player hitbox size

        self._load_animations()

    def _load_animations(self):
        """Load all animation sprite sheets"""
        for anim_name, (filename, frame_count, fps, loop) in self.ANIMATION_DEFS.items():
            filepath = self.sprites_dir / filename

            if not filepath.exists():
                print(f"Warning: Sprite sheet not found: {filepath}")
                self._create_fallback_animation(anim_name, frame_count, fps, loop)
                continue

            try:
                sheet = SpriteSheet(filepath, frame_count)
                raw_frames = sheet.get_frames()

                # Special handling for jump/fall (split jumpfall sheet)
                if anim_name == "jump":
                    raw_frames = [raw_frames[0]]  # First frame
                elif anim_name == "fall":
                    raw_frames = [raw_frames[1]]  # Second frame

                # Wrap in SpriteFrame objects
                frames = [SpriteFrame(surface=surf) for surf in raw_frames]

                self.animations[anim_name] = SpriteAnimation(
                    name=anim_name, frames=frames, fps=fps, loop=loop
                )

                # Cache both facing directions
                self.cache[(anim_name, 1)] = frames
                flipped = [
                    SpriteFrame(
                        surface=pygame.transform.flip(f.surface, True, False), offset=f.offset
                    )
                    for f in frames
                ]
                self.cache[(anim_name, -1)] = flipped

            except Exception as e:
                print(f"Error loading sprite sheet {filename}: {e}")
                self._create_fallback_animation(anim_name, frame_count, fps, loop)

        # Register loaded data with the global AnimationRegistry so the player
        # can use an AnimationStateMachine without re-loading any assets.
        from rendering.animation_system import AnimationRegistry
        AnimationRegistry.register_from_sprite_manager("player", self.animations, self.cache)

    def _create_fallback_animation(self, anim_name: str, frame_count: int, fps: int, loop: bool):
        """Create colored placeholder animation if sprite sheet missing"""
        state_colors = {
            "idle": (255, 255, 255),
            "walk": (200, 200, 255),
            "run": (80, 200, 255),
            "slow_walk": (120, 200, 255),
            "jump": (120, 240, 120),
            "fall": (200, 180, 80),
            "wall_slide": (255, 140, 120),
            "wall_hang": (255, 160, 120),
            "ceiling_hang": (255, 160, 120),
            "air_spin": (120, 200, 200),
            "crouch": (180, 180, 255),
            "dash": (255, 120, 255),
            "hurt": (255, 100, 100),
            "hurt2": (255, 110, 110),
            "death": (128, 128, 128),
            "attack": (255, 200, 100),
            "slash1": (255, 200, 120),
            "slash2": (255, 180, 120),
            "slash3": (255, 160, 120),
            "slash_air": (255, 220, 140),
            "jump_slash": (255, 220, 140),
            "throw_ground": (180, 220, 255),
            "throw_crouch": (160, 200, 255),
            "throw_air": (140, 180, 255),
            "teleport": (180, 120, 255),
            "ninjutsu_hand": (200, 160, 255),
            "ninjutsu_summon": (220, 180, 255),
        }

        color = state_colors.get(anim_name, (200, 200, 200))
        w, h = self.fallback_size
        if anim_name == "crouch":
            h = h // 2

        frames = []
        for i in range(max(1, frame_count // 2)):  # Fewer placeholder frames
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            surf.fill((*color, 255))
            # Add stripe for visual distinction
            if i % 2 == 0:
                stripe_rect = pygame.Rect(0, 0, w, h // 4)
                pygame.draw.rect(surf, (255, 255, 255, 60), stripe_rect)
            frames.append(SpriteFrame(surface=surf))

        self.animations[anim_name] = SpriteAnimation(
            name=anim_name, frames=frames, fps=fps, loop=loop
        )

        self.cache[(anim_name, 1)] = frames
        flipped = [
            SpriteFrame(surface=pygame.transform.flip(f.surface, True, False), offset=f.offset)
            for f in frames
        ]
        self.cache[(anim_name, -1)] = flipped

    def get_frame(self, state: str, facing: int, time_ms: int) -> SpriteFrame:
        """
        Get current animation frame for a state

        Args:
            state: Animation state (idle, run, jump, fall, etc.)
            facing: 1 for right, -1 for left
            time_ms: Current time in milliseconds (pygame.time.get_ticks())

        Returns:
            SpriteFrame for the current animation frame
        """
        # Get cached frames for this state and facing
        frames = self.cache.get((state, facing))

        if not frames:
            # Fallback to idle if state not found
            frames = self.cache.get(("idle", facing), self.cache.get(("idle", 1), []))

        if not frames:
            # Ultimate fallback: create emergency placeholder
            surf = pygame.Surface(self.fallback_size, pygame.SRCALPHA)
            surf.fill((255, 0, 255, 255))  # Magenta = missing sprite
            return SpriteFrame(surface=surf)

        # Single frame animation
        if len(frames) == 1:
            return frames[0]

        # Multi-frame animation: calculate frame index based on time
        animation = self.animations.get(state)
        if animation:
            frame_duration_ms = 1000 / animation.fps
            frame_index = int(time_ms / frame_duration_ms)

            if animation.loop:
                frame_index = frame_index % len(frames)
            else:
                frame_index = min(frame_index, len(frames) - 1)

            return frames[frame_index]

        # Fallback timing (150ms per frame)
        idx = (time_ms // 150) % len(frames)
        return frames[idx]

    def get_scaled_frame(
        self, state: str, facing: int, time_ms: int, target_size: tuple[int, int] | None = None
    ) -> SpriteFrame:
        """
        Get animation frame scaled to target size

        Args:
            state: Animation state
            facing: 1 for right, -1 for left
            time_ms: Current time in milliseconds
            target_size: Target (width, height) or None for original size

        Returns:
            SpriteFrame scaled to target size
        """
        frame = self.get_frame(state, facing, time_ms)

        if target_size is None:
            return frame

        scaled_surface = pygame.transform.scale(frame.surface, target_size)
        return SpriteFrame(surface=scaled_surface, offset=frame.offset)

    def get_animation_info(self, state: str) -> SpriteAnimation | None:
        """Get animation definition for debugging/info"""
        return self.animations.get(state)

    def list_animations(self) -> list[str]:
        """List all available animation names"""
        return list(self.animations.keys())
