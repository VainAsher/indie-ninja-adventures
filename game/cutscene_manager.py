"""
Cutscene Manager - Handles narrative cutscene playback

Manages story cutscenes for key narrative moments in The Hollowed Ninja.
Supports text-based scenes, dialogue, and sequential playback.

Version: v0.7.0 (Phase 4 - Polish & Integration)
"""

from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass


class CutsceneState(Enum):
    """Current state of cutscene playback"""
    NOT_PLAYING = "not_playing"
    PLAYING = "playing"
    PAUSED = "paused"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class SceneType(Enum):
    """Types of cutscene scenes"""
    TEXT = "text"           # Narrator text only
    DIALOGUE = "dialogue"   # Character dialogue with speaker
    CREDITS = "credits"     # End credits
    FADE = "fade"          # Fade transition
    IMAGE = "image"        # Display image (future use)


@dataclass
class Scene:
    """Individual scene within a cutscene"""
    scene_type: SceneType
    speaker: Optional[str] = None
    text: str = ""
    duration: float = 3.0  # Duration in seconds
    auto_advance: bool = True  # Auto-advance after duration
    fade_in: float = 0.5  # Fade in duration
    fade_out: float = 0.5  # Fade out duration
    on_start_event: Optional[str] = None  # Event to emit when scene starts
    on_end_event: Optional[str] = None    # Event to emit when scene ends


@dataclass
class CutsceneDefinition:
    """Complete cutscene definition"""
    cutscene_id: str
    title: str
    scenes: List[Scene]
    skippable: bool = True
    on_complete_event: Optional[str] = None


class CutsceneManager:
    """
    Manages cutscene playback for narrative moments.

    Responsibilities:
    - Load cutscene definitions
    - Play cutscenes sequentially
    - Handle scene transitions
    - Support skipping
    - Emit events for game integration
    """

    def __init__(self):
        """Initialize cutscene manager"""
        self.state = CutsceneState.NOT_PLAYING
        self.current_cutscene: Optional[CutsceneDefinition] = None
        self.current_scene_index: int = 0
        self.current_scene_time: float = 0.0
        self.total_elapsed_time: float = 0.0

        # Callbacks
        self.on_cutscene_start_callback: Optional[Callable] = None
        self.on_cutscene_complete_callback: Optional[Callable] = None
        self.on_scene_change_callback: Optional[Callable] = None

        # Cutscene library (loaded from data)
        self.cutscenes: Dict[str, CutsceneDefinition] = self._create_default_cutscenes()

    def _create_default_cutscenes(self) -> Dict[str, CutsceneDefinition]:
        """Create default cutscene definitions"""
        cutscenes = {}

        # Act 0: Veil Maiden Introduction
        cutscenes["veil_maiden_intro"] = CutsceneDefinition(
            cutscene_id="veil_maiden_intro",
            title="A Stranger Arrives",
            skippable=True,
            scenes=[
                Scene(
                    scene_type=SceneType.TEXT,
                    speaker="Narrator",
                    text="As you return to the hub, a figure awaits you in the shadows.",
                    duration=3.0
                ),
                Scene(
                    scene_type=SceneType.DIALOGUE,
                    speaker="The Veil Maiden",
                    text="Greetings, young ninja. I've been watching your progress. Impressive.",
                    duration=3.5
                ),
                Scene(
                    scene_type=SceneType.DIALOGUE,
                    speaker="The Veil Maiden",
                    text="I have... special missions for talented individuals like yourself. Interested?",
                    duration=4.0
                ),
                Scene(
                    scene_type=SceneType.TEXT,
                    speaker="Narrator",
                    text="Her smile is cold, but her words are warm. Something feels off, but the promise of challenge is enticing.",
                    duration=4.5
                )
            ],
            on_complete_event="veil_maiden_introduced"
        )

        # Act 0: Hub Empty
        cutscenes["hub_empty"] = CutsceneDefinition(
            cutscene_id="hub_empty",
            title="Isolation",
            skippable=True,
            scenes=[
                Scene(
                    scene_type=SceneType.TEXT,
                    speaker="Narrator",
                    text="You return to the hub. The portals glow dimly. The once-vibrant space feels... empty.",
                    duration=4.0
                ),
                Scene(
                    scene_type=SceneType.TEXT,
                    speaker="Narrator",
                    text="Where did everyone go? The NPCs, the merchants, even the Elder... all gone.",
                    duration=3.5
                ),
                Scene(
                    scene_type=SceneType.DIALOGUE,
                    speaker="The Veil Maiden",
                    text="Just you and me now. Isn't this what you wanted? To prove yourself without distractions?",
                    duration=4.5
                ),
                Scene(
                    scene_type=SceneType.TEXT,
                    speaker="Narrator",
                    text="Yin and Yang orbit nervously. You feel a chill.",
                    duration=3.0
                )
            ],
            on_complete_event="hub_emptied"
        )

        # Act 1: Scripted Defeat
        cutscenes["scripted_defeat"] = CutsceneDefinition(
            cutscene_id="scripted_defeat",
            title="The Veil Descends",
            skippable=False,  # Important story moment
            scenes=[
                Scene(
                    scene_type=SceneType.TEXT,
                    speaker="Narrator",
                    text="The Veil Maiden's power overwhelms you. No matter how hard you fight, she's always one step ahead.",
                    duration=4.0
                ),
                Scene(
                    scene_type=SceneType.DIALOGUE,
                    speaker="The Veil Maiden",
                    text="You fought well. But you were always meant to lose. I needed your light... and theirs.",
                    duration=4.5
                ),
                Scene(
                    scene_type=SceneType.TEXT,
                    speaker="Narrator",
                    text="She reaches out. Yin and Yang try to flee, but her power is absolute. They're pulled toward her, crying out.",
                    duration=5.0
                ),
                Scene(
                    scene_type=SceneType.DIALOGUE,
                    speaker="Hollowed Ninja",
                    text="No! Not them! Take me instead!",
                    duration=3.0
                ),
                Scene(
                    scene_type=SceneType.DIALOGUE,
                    speaker="The Veil Maiden",
                    text="I already have.",
                    duration=2.5
                ),
                Scene(
                    scene_type=SceneType.TEXT,
                    speaker="Narrator",
                    text="Yin and Yang vanish into her veil. Darkness consumes you. You fall... and fall... and fall.",
                    duration=5.0
                ),
                Scene(
                    scene_type=SceneType.FADE,
                    text="...",
                    duration=2.0
                )
            ],
            on_complete_event="player_defeated"
        )

        # Act 2: Wake in Hollow Depths
        cutscenes["wake_hollow_depths"] = CutsceneDefinition(
            cutscene_id="wake_hollow_depths",
            title="Awakening",
            skippable=True,
            scenes=[
                Scene(
                    scene_type=SceneType.TEXT,
                    speaker="Narrator",
                    text="You wake in darkness. The air is heavy, empty. You reach out, but Yin and Yang aren't there.",
                    duration=4.5
                ),
                Scene(
                    scene_type=SceneType.TEXT,
                    speaker="Narrator",
                    text="This is the Hollow Depths. A place where light struggles to exist. Where those broken by the Veil Maiden are cast aside.",
                    duration=5.0
                ),
                Scene(
                    scene_type=SceneType.DIALOGUE,
                    speaker="Hollowed Ninja",
                    text="I... failed them. I failed everyone.",
                    duration=3.0
                ),
                Scene(
                    scene_type=SceneType.TEXT,
                    speaker="Narrator",
                    text="But you're still here. Still breathing. Still capable of standing. Perhaps there's a way forward.",
                    duration=4.5
                )
            ],
            on_complete_event="hollow_depths_entered"
        )

        # Act 2: First Lantern
        cutscenes["first_lantern"] = CutsceneDefinition(
            cutscene_id="first_lantern",
            title="A Light in the Dark",
            skippable=True,
            scenes=[
                Scene(
                    scene_type=SceneType.TEXT,
                    speaker="Narrator",
                    text="Ahead, a faint glow. Another person, sitting in the darkness, holding a small lantern.",
                    duration=4.0
                ),
                Scene(
                    scene_type=SceneType.DIALOGUE,
                    speaker="The First Lantern",
                    text="Hey. You made it through. That's... that's good. Not everyone does.",
                    duration=4.0
                ),
                Scene(
                    scene_type=SceneType.DIALOGUE,
                    speaker="Hollowed Ninja",
                    text="Who are you? What is this place?",
                    duration=3.0
                ),
                Scene(
                    scene_type=SceneType.DIALOGUE,
                    speaker="The First Lantern",
                    text="We're The Lanterns. People who've been where you are. Lost, hollow, alone. But we found each other.",
                    duration=5.0
                ),
                Scene(
                    scene_type=SceneType.DIALOGUE,
                    speaker="The First Lantern",
                    text="You don't have to do this alone. Come. Let me show you that there are others.",
                    duration=4.5
                )
            ],
            on_complete_event="first_lantern_met"
        )

        # Act 3: Hub Restored
        cutscenes["hub_restored"] = CutsceneDefinition(
            cutscene_id="hub_restored",
            title="Return to Light",
            skippable=True,
            scenes=[
                Scene(
                    scene_type=SceneType.TEXT,
                    speaker="Narrator",
                    text="You step through the portal. The hub glows warmly once more. The Lanterns have returned, filling the space with life.",
                    duration=4.5
                ),
                Scene(
                    scene_type=SceneType.DIALOGUE,
                    speaker="Elder Guardian",
                    text="Welcome back. You've changed—grown stronger through connection. I'm proud of you.",
                    duration=4.0
                ),
                Scene(
                    scene_type=SceneType.TEXT,
                    speaker="Narrator",
                    text="But Yin and Yang are still gone. That absence remains, a constant ache. Yet you're no longer consumed by it.",
                    duration=5.0
                ),
                Scene(
                    scene_type=SceneType.DIALOGUE,
                    speaker="Hollowed Ninja",
                    text="I'm ready to face her again. Not for revenge... but to stop her from doing this to anyone else.",
                    duration=5.0
                )
            ],
            on_complete_event="hub_restoration_complete"
        )

        # Act 3: Veil Maiden Backstory
        cutscenes["veil_backstory"] = CutsceneDefinition(
            cutscene_id="veil_backstory",
            title="Understanding the Enemy",
            skippable=True,
            scenes=[
                Scene(
                    scene_type=SceneType.DIALOGUE,
                    speaker="Elder Guardian",
                    text="Before you face her again, you should know... The Veil Maiden wasn't always like this.",
                    duration=4.5
                ),
                Scene(
                    scene_type=SceneType.TEXT,
                    speaker="Narrator",
                    text="The Elder tells you her story. Once, she was like you—a ninja who lost everything.",
                    duration=4.0
                ),
                Scene(
                    scene_type=SceneType.TEXT,
                    speaker="Narrator",
                    text="But she had no Lanterns. No community. No support. She hollowed out, and in her emptiness, she became a predator.",
                    duration=5.5
                ),
                Scene(
                    scene_type=SceneType.DIALOGUE,
                    speaker="Elder Guardian",
                    text="She feeds on others' light because she has none of her own. She's as much a victim as those she breaks.",
                    duration=5.0
                ),
                Scene(
                    scene_type=SceneType.DIALOGUE,
                    speaker="Hollowed Ninja",
                    text="Then... maybe she can be saved?",
                    duration=3.0
                ),
                Scene(
                    scene_type=SceneType.DIALOGUE,
                    speaker="Elder Guardian",
                    text="Perhaps. But that choice will be yours to make, when the time comes.",
                    duration=4.5
                )
            ],
            on_complete_event="veil_backstory_revealed"
        )

        # Act 4: Final Battle Start
        cutscenes["final_battle_start"] = CutsceneDefinition(
            cutscene_id="final_battle_start",
            title="The Final Confrontation",
            skippable=True,
            scenes=[
                Scene(
                    scene_type=SceneType.TEXT,
                    speaker="Narrator",
                    text="You stand before The Veil Maiden once more. But this time, you're different. Stronger. Connected.",
                    duration=4.5
                ),
                Scene(
                    scene_type=SceneType.DIALOGUE,
                    speaker="The Veil Maiden",
                    text="You've returned. I'm impressed. Most who fall into the Depths never climb out.",
                    duration=4.5
                ),
                Scene(
                    scene_type=SceneType.DIALOGUE,
                    speaker="Hollowed Ninja",
                    text="I'm not the same person you broke. I've found my light again—in others, in community, in shared burden.",
                    duration=5.0
                ),
                Scene(
                    scene_type=SceneType.DIALOGUE,
                    speaker="The Veil Maiden",
                    text="How naive. Let's see if that 'light' can withstand my darkness.",
                    duration=4.0
                ),
                Scene(
                    scene_type=SceneType.TEXT,
                    speaker="Narrator",
                    text="The battle begins. This time, you fight not from a place of hollowness, but of wholeness.",
                    duration=4.5
                )
            ],
            on_complete_event="final_battle_started"
        )

        return cutscenes

    def play_cutscene(self, cutscene_id: str) -> bool:
        """
        Start playing a cutscene.

        Args:
            cutscene_id: ID of cutscene to play

        Returns:
            True if cutscene started successfully
        """
        if cutscene_id not in self.cutscenes:
            print(f"[CutsceneManager] Cutscene '{cutscene_id}' not found")
            return False

        if self.state == CutsceneState.PLAYING:
            print(f"[CutsceneManager] Already playing a cutscene")
            return False

        self.current_cutscene = self.cutscenes[cutscene_id]
        self.current_scene_index = 0
        self.current_scene_time = 0.0
        self.total_elapsed_time = 0.0
        self.state = CutsceneState.PLAYING

        print(f"[CutsceneManager] Playing cutscene: {cutscene_id}")

        # Trigger callback
        if self.on_cutscene_start_callback:
            self.on_cutscene_start_callback(self.current_cutscene)

        # Start first scene
        self._start_current_scene()

        return True

    def play_cutscene_from_data(self, cutscene_data: Dict) -> bool:
        """
        Play a cutscene from raw data dictionary.

        Args:
            cutscene_data: Cutscene configuration dictionary

        Returns:
            True if cutscene started successfully
        """
        # Convert dictionary to CutsceneDefinition
        scenes = []
        for scene_data in cutscene_data.get("scenes", []):
            scene = Scene(
                scene_type=SceneType(scene_data.get("type", "text")),
                speaker=scene_data.get("speaker"),
                text=scene_data.get("text", ""),
                duration=scene_data.get("duration", 3.0),
                auto_advance=scene_data.get("auto_advance", True),
                fade_in=scene_data.get("fade_in", 0.5),
                fade_out=scene_data.get("fade_out", 0.5)
            )
            scenes.append(scene)

        cutscene = CutsceneDefinition(
            cutscene_id=cutscene_data.get("cutscene_id", "dynamic"),
            title=cutscene_data.get("title", ""),
            scenes=scenes,
            skippable=cutscene_data.get("skippable", True)
        )

        # Store temporarily
        self.current_cutscene = cutscene
        self.current_scene_index = 0
        self.current_scene_time = 0.0
        self.total_elapsed_time = 0.0
        self.state = CutsceneState.PLAYING

        # Trigger callback
        if self.on_cutscene_start_callback:
            self.on_cutscene_start_callback(self.current_cutscene)

        # Start first scene
        self._start_current_scene()

        return True

    def update(self, dt: float) -> bool:
        """
        Update cutscene playback.

        Args:
            dt: Delta time in seconds

        Returns:
            True if cutscene is still playing
        """
        if self.state != CutsceneState.PLAYING:
            return False

        if not self.current_cutscene:
            return False

        self.current_scene_time += dt
        self.total_elapsed_time += dt

        # Check if current scene is complete
        current_scene = self.get_current_scene()
        if current_scene and current_scene.auto_advance:
            if self.current_scene_time >= current_scene.duration:
                self.advance_scene()

        return self.state == CutsceneState.PLAYING

    def advance_scene(self) -> bool:
        """
        Advance to next scene.

        Returns:
            True if advanced, False if cutscene ended
        """
        if not self.current_cutscene:
            return False

        # End current scene
        current_scene = self.get_current_scene()
        if current_scene and current_scene.on_end_event:
            print(f"[CutsceneManager] Scene end event: {current_scene.on_end_event}")

        # Move to next scene
        self.current_scene_index += 1
        self.current_scene_time = 0.0

        # Check if cutscene is complete
        if self.current_scene_index >= len(self.current_cutscene.scenes):
            self._complete_cutscene()
            return False

        # Start next scene
        self._start_current_scene()
        return True

    def skip_cutscene(self) -> bool:
        """
        Skip the current cutscene.

        Returns:
            True if skipped successfully
        """
        if not self.current_cutscene:
            return False

        if not self.current_cutscene.skippable:
            print(f"[CutsceneManager] Cutscene is not skippable")
            return False

        print(f"[CutsceneManager] Skipping cutscene: {self.current_cutscene.cutscene_id}")
        self.state = CutsceneState.SKIPPED
        self._complete_cutscene()
        return True

    def pause(self):
        """Pause cutscene playback"""
        if self.state == CutsceneState.PLAYING:
            self.state = CutsceneState.PAUSED

    def resume(self):
        """Resume cutscene playback"""
        if self.state == CutsceneState.PAUSED:
            self.state = CutsceneState.PLAYING

    def _start_current_scene(self):
        """Start the current scene"""
        scene = self.get_current_scene()
        if not scene:
            return

        print(f"[CutsceneManager] Scene {self.current_scene_index + 1}/{len(self.current_cutscene.scenes)}: {scene.speaker or 'Narrator'}")

        # Trigger scene start event
        if scene.on_start_event:
            print(f"[CutsceneManager] Scene start event: {scene.on_start_event}")

        # Trigger scene change callback
        if self.on_scene_change_callback:
            self.on_scene_change_callback(scene, self.current_scene_index)

    def _complete_cutscene(self):
        """Complete the current cutscene"""
        if not self.current_cutscene:
            return

        cutscene_id = self.current_cutscene.cutscene_id
        was_skipped = self.state == CutsceneState.SKIPPED

        # Emit completion event
        if self.current_cutscene.on_complete_event:
            print(f"[CutsceneManager] Cutscene complete event: {self.current_cutscene.on_complete_event}")

        # Trigger callback
        if self.on_cutscene_complete_callback:
            self.on_cutscene_complete_callback(self.current_cutscene, was_skipped)

        print(f"[CutsceneManager] Cutscene completed: {cutscene_id} (skipped: {was_skipped})")

        # Clear state
        self.state = CutsceneState.COMPLETED
        self.current_cutscene = None
        self.current_scene_index = 0
        self.current_scene_time = 0.0
        self.total_elapsed_time = 0.0

    def get_current_scene(self) -> Optional[Scene]:
        """Get the currently playing scene"""
        if not self.current_cutscene:
            return None

        if self.current_scene_index >= len(self.current_cutscene.scenes):
            return None

        return self.current_cutscene.scenes[self.current_scene_index]

    def is_playing(self) -> bool:
        """Check if a cutscene is currently playing"""
        return self.state == CutsceneState.PLAYING

    def get_progress(self) -> float:
        """Get cutscene progress (0.0 to 1.0)"""
        if not self.current_cutscene or len(self.current_cutscene.scenes) == 0:
            return 0.0

        return self.current_scene_index / len(self.current_cutscene.scenes)

    def get_scene_text(self) -> str:
        """Get current scene's display text"""
        scene = self.get_current_scene()
        if not scene:
            return ""

        if scene.speaker:
            return f"{scene.speaker}: {scene.text}"
        return scene.text


# ============================================================
# Helper Functions
# ============================================================

def create_cutscene_manager() -> CutsceneManager:
    """Create a new cutscene manager instance"""
    return CutsceneManager()
