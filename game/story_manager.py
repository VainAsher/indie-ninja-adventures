"""
Story Manager - Tracks narrative progression for The Hollowed Ninja story.

Manages:
- Current act progression (0-4)
- Hub visual state (brightness, NPC presence)
- Companion visibility (Yin & Yang)
- Story-triggered events
- Ending and moral choice system
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from game.ending_manager import EndingManager, EndingChoice
from game.cutscene_manager import CutsceneManager


@dataclass
class HubState:
    """Represents the current state of the hub area."""
    brightness: float = 1.0  # 0.0 (dark) to 1.0 (bright)
    npc_ids: List[str] = field(default_factory=list)  # NPCs currently in hub
    atmosphere: str = "vibrant"  # vibrant, dimming, dark, recovering, restored

    def to_dict(self) -> Dict[str, Any]:
        """Serialize hub state to dictionary."""
        return {
            "brightness": self.brightness,
            "npc_ids": self.npc_ids.copy(),
            "atmosphere": self.atmosphere
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "HubState":
        """Deserialize hub state from dictionary."""
        return HubState(
            brightness=data.get("brightness", 1.0),
            npc_ids=data.get("npc_ids", []).copy(),
            atmosphere=data.get("atmosphere", "vibrant")
        )


class StoryManager:
    """
    Manages the narrative state for The Hollowed Ninja story.

    Acts:
    - Act 0: Rising Grounds (Forest + Town) - Hub empties
    - Act 1: The Veil Descends (Caves) - Scripted defeat
    - Act 2: The Hollow Depths (New zone) - Recovery
    - Act 3: Ascending Paths (Castle) - Hub restored
    - Act 4: Winding Skyroad (Sewer + Final Boss) - Confrontation
    """

    def __init__(self):
        # Core story state
        self.current_act: int = 0  # 0-4
        self.yin_yang_present: bool = True  # Companions visible
        self.hub_state: HubState = HubState()

        # Story progression tracking
        self.veil_maiden_encountered: bool = False
        self.veil_maiden_defeated_act1: bool = False  # Scripted defeat
        self.veil_maiden_defeated_final: bool = False  # Actual defeat
        self.special_missions_completed: int = 0  # Veil Maiden's missions

        # Act-specific flags
        self.act0_hub_degradation_level: int = 0  # 0-9 (one per mission in Act 0)
        self.act1_defeat_triggered: bool = False
        self.act2_lanterns_met: int = 0  # Number of Lantern NPCs encountered
        self.act3_veil_backstory_revealed: bool = False
        self.act4_moral_choice: Optional[str] = None  # "save" or "destroy"

        # Ending state
        self.game_completed: bool = False
        self.ending_achieved: Optional[str] = None  # "save" or "destroy"

        # Ending manager (handles moral choice and ending cutscenes)
        self.ending_manager: EndingManager = EndingManager()

        # Cutscene manager (handles narrative cutscene playback)
        self.cutscene_manager: CutsceneManager = CutsceneManager()

    # ===== Act Management =====

    def advance_act(self, new_act: int) -> None:
        """
        Advance to a new act and apply corresponding state changes.

        Args:
            new_act: Act number (0-4)
        """
        if new_act < 0 or new_act > 4:
            raise ValueError(f"Invalid act number: {new_act}. Must be 0-4.")

        old_act = self.current_act
        self.current_act = new_act

        # Apply act-specific state changes
        if new_act == 0:
            self._setup_act0()
        elif new_act == 1:
            self._setup_act1()
        elif new_act == 2:
            self._setup_act2()
        elif new_act == 3:
            self._setup_act3()
        elif new_act == 4:
            self._setup_act4()

        print(f"[StoryManager] Advanced from Act {old_act} to Act {new_act}")

    def _setup_act0(self) -> None:
        """Setup for Act 0: Rising Grounds."""
        self.yin_yang_present = True
        self.hub_state.atmosphere = "vibrant"
        self.hub_state.brightness = 1.0
        # Hub NPCs will be set by campaign manager

    def _setup_act1(self) -> None:
        """Setup for Act 1: The Veil Descends."""
        self.yin_yang_present = True  # Still present until defeat
        self.hub_state.atmosphere = "dark"
        self.hub_state.brightness = 0.2
        # Hub should be empty from Act 0's progression

    def _setup_act2(self) -> None:
        """Setup for Act 2: The Hollow Depths."""
        self.yin_yang_present = False  # Consumed by Veil Maiden
        self.hub_state.atmosphere = "recovering"
        self.hub_state.brightness = 0.3  # Starts dark, brightens as Lanterns join
        self.hub_state.npc_ids = []  # Start empty, The Lanterns join gradually

    def _setup_act3(self) -> None:
        """Setup for Act 3: Ascending Paths."""
        self.yin_yang_present = False  # Still absent
        self.hub_state.atmosphere = "restored"
        self.hub_state.brightness = 0.9
        # Hub populated with The Lanterns NPCs

    def _setup_act4(self) -> None:
        """Setup for Act 4: Winding Skyroad."""
        self.yin_yang_present = False  # Still absent until ending
        self.hub_state.atmosphere = "restored"
        self.hub_state.brightness = 0.9

    # ===== Mission Event Handlers =====

    def on_mission_complete(self, mission_id: str, campaign_manager=None) -> Dict[str, Any]:
        """
        Trigger story events when a mission is completed.

        Args:
            mission_id: ID of completed mission
            campaign_manager: Reference to campaign manager (for mission data)

        Returns:
            Dictionary of story events triggered
        """
        events = {
            "act_changed": False,
            "hub_changed": False,
            "cutscene": None,
            "npcs_removed": [],
            "npcs_added": []
        }

        # Act 0 progression: Hub degradation
        if self.current_act == 0:
            events.update(self._handle_act0_mission_complete(mission_id))

        # Act 1 progression: Toward scripted defeat
        elif self.current_act == 1:
            events.update(self._handle_act1_mission_complete(mission_id))

        # Act 2 progression: Meeting The Lanterns
        elif self.current_act == 2:
            events.update(self._handle_act2_mission_complete(mission_id))

        # Act 3 progression: Preparing for final battle
        elif self.current_act == 3:
            events.update(self._handle_act3_mission_complete(mission_id))

        # Act 4 progression: Final confrontation
        elif self.current_act == 4:
            events.update(self._handle_act4_mission_complete(mission_id))

        return events

    def _handle_act0_mission_complete(self, mission_id: str) -> Dict[str, Any]:
        """Handle mission completion in Act 0."""
        events = {}

        # Veil Maiden introduction (after town_1)
        if mission_id == "town_1" and not self.veil_maiden_encountered:
            self.veil_maiden_encountered = True
            events["cutscene"] = "veil_maiden_intro"
            events["cutscene_id"] = "veil_maiden_intro"

        # Hub degradation (each mission removes NPCs and dims hub)
        if mission_id.startswith("forest_") or mission_id.startswith("town_"):
            self.act0_hub_degradation_level += 1

            # Decrease brightness (from 1.0 to 0.2 over 9 missions)
            brightness_decrease = 0.8 / 9  # Total decrease of 0.8 over 9 missions
            new_brightness = 1.0 - (self.act0_hub_degradation_level * brightness_decrease)
            self.hub_state.brightness = max(0.2, new_brightness)

            # Update atmosphere
            if self.act0_hub_degradation_level <= 3:
                self.hub_state.atmosphere = "vibrant"
            elif self.act0_hub_degradation_level <= 6:
                self.hub_state.atmosphere = "dimming"
            else:
                self.hub_state.atmosphere = "dark"

            events["hub_changed"] = True

            # Final mission of Act 0: Hub completely empty
            if mission_id == "town_4":
                events["cutscene"] = "hub_empty"
                events["cutscene_id"] = "hub_empty"
                events["act_changed"] = True
                # Advance to Act 1 will happen via campaign progression

        return events

    def _handle_act1_mission_complete(self, mission_id: str) -> Dict[str, Any]:
        """Handle mission completion in Act 1."""
        events = {}

        # Scripted defeat at cave_1 boss fight
        if mission_id == "cave_1" and not self.act1_defeat_triggered:
            self.act1_defeat_triggered = True
            self.veil_maiden_defeated_act1 = True
            self.yin_yang_present = False  # Companions consumed
            events["cutscene"] = "scripted_defeat"
            events["cutscene_id"] = "scripted_defeat"
            events["act_changed"] = True
            # Player will wake up in Act 2

        return events

    def _handle_act2_mission_complete(self, mission_id: str) -> Dict[str, Any]:
        """Handle mission completion in Act 2 (Hollow Depths)."""
        events = {}

        # Meeting The Lanterns (gradual hub restoration)
        if mission_id.startswith("hollow_"):
            self.act2_lanterns_met += 1

            # Gradually brighten hub (from 0.3 to 0.7 over Act 2 missions)
            brightness_increase = 0.4 / 5  # Assuming 5 Hollow Depths missions
            self.hub_state.brightness = min(0.7, 0.3 + (self.act2_lanterns_met * brightness_increase))

            events["hub_changed"] = True

            # First Lantern encounter
            if self.act2_lanterns_met == 1:
                events["cutscene"] = "first_lantern"
                events["cutscene_id"] = "first_lantern"

        return events

    def _handle_act3_mission_complete(self, mission_id: str) -> Dict[str, Any]:
        """Handle mission completion in Act 3."""
        events = {}

        # Veil Maiden backstory reveal (mid-Act 3)
        if mission_id == "castle_3" and not self.act3_veil_backstory_revealed:
            self.act3_veil_backstory_revealed = True
            events["cutscene"] = "veil_backstory"
            events["cutscene_id"] = "veil_backstory"

        return events

    def _handle_act4_mission_complete(self, mission_id: str) -> Dict[str, Any]:
        """Handle mission completion in Act 4."""
        events = {}

        # Final boss defeated: Moral choice
        if mission_id == "sewer_3" and not self.veil_maiden_defeated_final:
            self.veil_maiden_defeated_final = True

            # Trigger ending manager
            should_present_choice = self.ending_manager.on_final_boss_defeated()
            if should_present_choice:
                events["moral_choice"] = True
                events["choice_data"] = self.ending_manager.present_choice()

        return events

    # ===== Special Events =====

    def trigger_scripted_defeat(self) -> None:
        """Trigger the scripted defeat event (Act 1 boss fight)."""
        self.act1_defeat_triggered = True
        self.yin_yang_present = False
        print("[StoryManager] Scripted defeat triggered - Yin & Yang consumed")

    def set_moral_choice(self, choice: str) -> Dict[str, Any]:
        """
        Set the player's moral choice at the end.

        Args:
            choice: "save" or "destroy"

        Returns:
            Dictionary with ending data and cutscene info
        """
        if choice not in ["save", "destroy"]:
            raise ValueError(f"Invalid moral choice: {choice}. Must be 'save' or 'destroy'.")

        # Convert string to EndingChoice enum
        ending_choice = EndingChoice.SAVE if choice == "save" else EndingChoice.DESTROY

        # Register choice with ending manager
        success = self.ending_manager.make_choice(ending_choice)
        if not success:
            raise RuntimeError(f"Failed to register moral choice: {choice}")

        # Update story state
        self.act4_moral_choice = choice
        self.ending_achieved = choice
        self.game_completed = True

        print(f"[StoryManager] Moral choice set: {choice}")

        # Return ending data
        return {
            "choice": choice,
            "cutscene_data": self.ending_manager.get_ending_cutscene_data(),
            "hub_final_state": self.ending_manager.get_hub_final_state(),
            "constellation_data": self.ending_manager.get_constellation_position()
        }

    def complete_ending(self, choice: str) -> Dict[str, Any]:
        """
        Mark the game as completed with the chosen ending.

        Args:
            choice: "save" or "destroy"

        Returns:
            Dictionary with ending data
        """
        ending_data = self.set_moral_choice(choice)

        # Mark ending as complete in ending manager
        self.ending_manager.complete_ending()

        # Update hub state based on ending
        if ending_data.get("hub_final_state"):
            hub_final = ending_data["hub_final_state"]
            self.hub_state.brightness = hub_final.get("brightness", 0.9)
            self.hub_state.atmosphere = "restored"

        # Yin & Yang become constellation (visual only, not gameplay restore)
        print(f"[StoryManager] Game completed with '{choice}' ending")

        return ending_data

    # ===== Hub State Queries =====

    def get_hub_state(self) -> HubState:
        """Get the current hub visual state."""
        return self.hub_state

    def should_spawn_yin_yang(self) -> bool:
        """Check if Yin & Yang companions should be visible."""
        return self.yin_yang_present

    def get_hub_brightness(self) -> float:
        """Get current hub brightness (0.0 to 1.0)."""
        return self.hub_state.brightness

    def get_current_act(self) -> int:
        """Get the current act number."""
        return self.current_act

    def get_constellation_visible(self) -> bool:
        """Check if Yin & Yang constellation should be visible (post-game)."""
        return self.game_completed

    def get_constellation_position(self) -> Optional[Dict[str, float]]:
        """Get constellation star positions if game is completed."""
        if self.game_completed:
            return self.ending_manager.get_constellation_position()
        return None

    def get_ending_data(self) -> Optional[Dict[str, Any]]:
        """Get ending data if game is completed."""
        if self.game_completed and self.ending_manager.ending_data:
            return {
                "choice": self.ending_achieved,
                "title": self.ending_manager.ending_data.title,
                "veil_maiden_fate": self.ending_manager.ending_data.veil_maiden_fate,
                "hub_final_state": self.ending_manager.ending_data.hub_final_state
            }
        return None

    # ===== Cutscene Management =====

    def trigger_cutscene(self, cutscene_id: str) -> bool:
        """
        Trigger a story cutscene.

        Args:
            cutscene_id: ID of cutscene to play

        Returns:
            True if cutscene started successfully
        """
        return self.cutscene_manager.play_cutscene(cutscene_id)

    def update_cutscene(self, dt: float) -> bool:
        """
        Update active cutscene.

        Args:
            dt: Delta time in seconds

        Returns:
            True if cutscene is still playing
        """
        return self.cutscene_manager.update(dt)

    def is_cutscene_playing(self) -> bool:
        """Check if a cutscene is currently playing."""
        return self.cutscene_manager.is_playing()

    def skip_cutscene(self) -> bool:
        """Skip the currently playing cutscene."""
        return self.cutscene_manager.skip_cutscene()

    def get_cutscene_text(self) -> str:
        """Get current cutscene scene text for display."""
        return self.cutscene_manager.get_scene_text()

    # ===== Serialization =====

    def to_dict(self) -> Dict[str, Any]:
        """Serialize story state to dictionary for saving."""
        return {
            "current_act": self.current_act,
            "yin_yang_present": self.yin_yang_present,
            "hub_state": self.hub_state.to_dict(),
            "veil_maiden_encountered": self.veil_maiden_encountered,
            "veil_maiden_defeated_act1": self.veil_maiden_defeated_act1,
            "veil_maiden_defeated_final": self.veil_maiden_defeated_final,
            "special_missions_completed": self.special_missions_completed,
            "act0_hub_degradation_level": self.act0_hub_degradation_level,
            "act1_defeat_triggered": self.act1_defeat_triggered,
            "act2_lanterns_met": self.act2_lanterns_met,
            "act3_veil_backstory_revealed": self.act3_veil_backstory_revealed,
            "act4_moral_choice": self.act4_moral_choice,
            "game_completed": self.game_completed,
            "ending_achieved": self.ending_achieved,
            "ending_manager_state": self.ending_manager.to_dict()
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "StoryManager":
        """Deserialize story state from dictionary."""
        manager = StoryManager()

        manager.current_act = data.get("current_act", 0)
        manager.yin_yang_present = data.get("yin_yang_present", True)
        manager.hub_state = HubState.from_dict(data.get("hub_state", {}))
        manager.veil_maiden_encountered = data.get("veil_maiden_encountered", False)
        manager.veil_maiden_defeated_act1 = data.get("veil_maiden_defeated_act1", False)
        manager.veil_maiden_defeated_final = data.get("veil_maiden_defeated_final", False)
        manager.special_missions_completed = data.get("special_missions_completed", 0)
        manager.act0_hub_degradation_level = data.get("act0_hub_degradation_level", 0)
        manager.act1_defeat_triggered = data.get("act1_defeat_triggered", False)
        manager.act2_lanterns_met = data.get("act2_lanterns_met", 0)
        manager.act3_veil_backstory_revealed = data.get("act3_veil_backstory_revealed", False)
        manager.act4_moral_choice = data.get("act4_moral_choice", None)
        manager.game_completed = data.get("game_completed", False)
        manager.ending_achieved = data.get("ending_achieved", None)

        # Load ending manager state if present
        if "ending_manager_state" in data:
            manager.ending_manager = EndingManager.from_dict(data["ending_manager_state"])

        return manager

    # ===== Debug/Info =====

    def get_story_summary(self) -> str:
        """Get a human-readable summary of the current story state."""
        act_names = [
            "Rising Grounds",
            "The Veil Descends",
            "The Hollow Depths",
            "Ascending Paths",
            "Winding Skyroad"
        ]

        summary = f"""
=== Story State Summary ===
Current Act: {self.current_act} - {act_names[self.current_act]}
Yin & Yang Present: {self.yin_yang_present}
Hub Brightness: {self.hub_state.brightness:.2f}
Hub Atmosphere: {self.hub_state.atmosphere}

Story Progress:
- Veil Maiden Encountered: {self.veil_maiden_encountered}
- Act 1 Defeat: {self.veil_maiden_defeated_act1}
- Final Defeat: {self.veil_maiden_defeated_final}
- Lanterns Met: {self.act2_lanterns_met}
- Backstory Revealed: {self.act3_veil_backstory_revealed}
- Moral Choice: {self.act4_moral_choice or 'Not made'}
- Game Completed: {self.game_completed}"""

        if self.game_completed:
            ending_data = self.get_ending_data()
            if ending_data:
                summary += f"""

Ending:
- Choice: {ending_data['choice'].upper()}
- Title: {ending_data['title']}
- Veil Maiden Fate: {ending_data['veil_maiden_fate']}
- Constellation Visible: {self.get_constellation_visible()}"""

        summary += "\n========================"

        return summary
