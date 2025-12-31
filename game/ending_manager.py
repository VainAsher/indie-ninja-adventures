"""
Ending Manager - Handles final moral choice and multiple endings

Manages the final confrontation with The Veil Maiden and the player's
moral choice: Save or Destroy. Both endings share the bittersweet
outcome where Yin & Yang remain as stars.

Version: v0.7.0 (Phase 3 - Story Integration)
"""

from typing import Dict, Optional, Callable
from enum import Enum
from dataclasses import dataclass


class EndingChoice(Enum):
    """Possible ending choices"""
    SAVE = "save"      # Redeem the Veil Maiden
    DESTROY = "destroy"  # Defeat the Veil Maiden
    NOT_CHOSEN = "not_chosen"


class EndingState(Enum):
    """Current state of ending sequence"""
    NOT_STARTED = "not_started"
    FINAL_BATTLE = "final_battle"
    CHOICE_PRESENTED = "choice_presented"
    ENDING_PLAYING = "ending_playing"
    COMPLETED = "completed"


@dataclass
class EndingData:
    """Data for an ending variant"""
    ending_id: str
    choice: EndingChoice
    title: str
    description: str
    cutscene_id: str
    veil_maiden_fate: str  # "redeemed" or "defeated"
    hub_final_state: Dict[str, any]


class EndingManager:
    """
    Manages the final battle, moral choice, and multiple endings.

    Responsibilities:
    - Detect final battle completion
    - Present moral choice to player
    - Play appropriate ending based on choice
    - Update story state with ending result
    - Handle Yin/Yang constellation finale
    """

    def __init__(self):
        """Initialize ending manager"""
        self.state = EndingState.NOT_STARTED
        self.choice_made: EndingChoice = EndingChoice.NOT_CHOSEN
        self.ending_data: Optional[EndingData] = None

        # Callbacks for game integration
        self.on_choice_callback: Optional[Callable] = None
        self.on_ending_complete_callback: Optional[Callable] = None

        # Ending definitions
        self.endings = self._create_ending_definitions()

    def _create_ending_definitions(self) -> Dict[EndingChoice, EndingData]:
        """Create ending variant definitions"""
        return {
            EndingChoice.SAVE: EndingData(
                ending_id="save_veil_maiden",
                choice=EndingChoice.SAVE,
                title="The Path of Mercy",
                description="You chose to save The Veil Maiden, offering her redemption.",
                cutscene_id="ending_save",
                veil_maiden_fate="redeemed",
                hub_final_state={
                    "brightness": 0.9,  # Warm, hopeful
                    "veil_maiden_present": True,  # She joins as NPC
                    "npcs_active": True,
                    "constellation_visible": True
                }
            ),
            EndingChoice.DESTROY: EndingData(
                ending_id="destroy_veil_maiden",
                choice=EndingChoice.DESTROY,
                title="The Path of Justice",
                description="You chose to destroy The Veil Maiden, ending her threat.",
                cutscene_id="ending_destroy",
                veil_maiden_fate="defeated",
                hub_final_state={
                    "brightness": 0.7,  # Dimmer, melancholic
                    "veil_maiden_present": False,
                    "npcs_active": True,
                    "constellation_visible": True
                }
            )
        }

    def trigger_final_battle(self):
        """Trigger the final battle with Veil Maiden (Act 4)"""
        if self.state == EndingState.NOT_STARTED:
            self.state = EndingState.FINAL_BATTLE

    def on_final_boss_defeated(self):
        """Called when Veil Maiden is defeated in final battle"""
        if self.state == EndingState.FINAL_BATTLE:
            self.state = EndingState.CHOICE_PRESENTED
            return True  # Signal to present choice
        return False

    def present_choice(self) -> Dict[str, str]:
        """
        Get choice presentation data.

        Returns:
            Dictionary with choice options and descriptions
        """
        return {
            "title": "The Veil Falls",
            "context": (
                "The Veil Maiden lies defeated before you. You see now that she, too, "
                "was hollow—consumed by her own pain, lashing out to fill the void. "
                "Yin and Yang watch from the stars above, distant but present.\n\n"
                "What will you do?"
            ),
            "choices": [
                {
                    "id": "save",
                    "label": "Offer her your hand",
                    "description": (
                        "Extend mercy. Help her find the light you found in The Lanterns. "
                        "She can heal, as you did."
                    ),
                    "outcome_hint": "Redemption, but loss remains"
                },
                {
                    "id": "destroy",
                    "label": "End her suffering",
                    "description": (
                        "She took what was precious to you. Some wounds cannot heal, "
                        "some threats must be eliminated."
                    ),
                    "outcome_hint": "Justice, but emptiness lingers"
                }
            ],
            "shared_outcome": (
                "Either way, Yin and Yang will not return. "
                "They remain in the stars—a memory, a reminder."
            )
        }

    def make_choice(self, choice: EndingChoice) -> bool:
        """
        Player makes their moral choice.

        Args:
            choice: The ending choice

        Returns:
            True if choice was valid and registered
        """
        if self.state != EndingState.CHOICE_PRESENTED:
            return False

        if choice not in [EndingChoice.SAVE, EndingChoice.DESTROY]:
            return False

        self.choice_made = choice
        self.ending_data = self.endings[choice]
        self.state = EndingState.ENDING_PLAYING

        # Trigger callback if set
        if self.on_choice_callback:
            self.on_choice_callback(choice, self.ending_data)

        return True

    def get_ending_cutscene_data(self) -> Optional[Dict]:
        """
        Get cutscene data for the chosen ending.

        Returns:
            Cutscene configuration dictionary
        """
        if not self.ending_data:
            return None

        if self.choice_made == EndingChoice.SAVE:
            return self._get_save_ending_cutscene()
        elif self.choice_made == EndingChoice.DESTROY:
            return self._get_destroy_ending_cutscene()

        return None

    def _get_save_ending_cutscene(self) -> Dict:
        """Cutscene for redemption ending"""
        return {
            "cutscene_id": "ending_save",
            "title": "The Path of Mercy",
            "scenes": [
                {
                    "type": "text",
                    "speaker": "Narrator",
                    "text": (
                        "You extend your hand. The Veil Maiden hesitates, "
                        "then takes it. Her veil begins to dissolve."
                    ),
                    "duration": 4.0
                },
                {
                    "type": "dialogue",
                    "speaker": "The Veil Maiden",
                    "text": (
                        "Why...? After everything I took from you...?"
                    ),
                    "duration": 3.0
                },
                {
                    "type": "dialogue",
                    "speaker": "Hollowed Ninja",
                    "text": (
                        "Because I know what it's like to be hollow. "
                        "And I know that no one heals alone."
                    ),
                    "duration": 4.0
                },
                {
                    "type": "text",
                    "speaker": "Narrator",
                    "text": (
                        "The Lanterns gather around. The hub glows with warm light. "
                        "The Veil Maiden—now just a woman—sits among them, weeping."
                    ),
                    "duration": 5.0
                },
                {
                    "type": "text",
                    "speaker": "Narrator",
                    "text": (
                        "You look to the night sky. Yin and Yang shine as twin stars—"
                        "forever watching, forever distant."
                    ),
                    "duration": 4.0
                },
                {
                    "type": "dialogue",
                    "speaker": "Hollowed Ninja",
                    "text": (
                        "I couldn't save you... but I can remember you. "
                        "And I can keep others from falling into the darkness."
                    ),
                    "duration": 5.0
                },
                {
                    "type": "text",
                    "speaker": "Narrator",
                    "text": (
                        "The journey forward won't be easy. The loss remains. "
                        "But you are not alone.\n\n"
                        "And that makes all the difference."
                    ),
                    "duration": 5.0
                },
                {
                    "type": "credits",
                    "text": "THE END - The Path of Mercy",
                    "duration": 3.0
                }
            ]
        }

    def _get_destroy_ending_cutscene(self) -> Dict:
        """Cutscene for justice ending"""
        return {
            "cutscene_id": "ending_destroy",
            "title": "The Path of Justice",
            "scenes": [
                {
                    "type": "text",
                    "speaker": "Narrator",
                    "text": (
                        "You raise your blade. The Veil Maiden doesn't resist. "
                        "She closes her eyes, accepting her fate."
                    ),
                    "duration": 4.0
                },
                {
                    "type": "dialogue",
                    "speaker": "The Veil Maiden",
                    "text": (
                        "Perhaps... this is what I deserve. I'm sorry... "
                        "for what I took from you."
                    ),
                    "duration": 4.0
                },
                {
                    "type": "text",
                    "speaker": "Narrator",
                    "text": (
                        "The veil dissipates into shadow. She is gone. "
                        "The threat is ended."
                    ),
                    "duration": 3.0
                },
                {
                    "type": "text",
                    "speaker": "Narrator",
                    "text": (
                        "You return to the hub. The Lanterns welcome you back—"
                        "but you feel hollow inside. Victory, yet emptiness."
                    ),
                    "duration": 5.0
                },
                {
                    "type": "text",
                    "speaker": "Narrator",
                    "text": (
                        "You look to the night sky. Yin and Yang shine as twin stars—"
                        "forever watching, forever distant."
                    ),
                    "duration": 4.0
                },
                {
                    "type": "dialogue",
                    "speaker": "Hollowed Ninja",
                    "text": (
                        "I avenged what was taken... but you're still gone. "
                        "Will this pain ever truly end?"
                    ),
                    "duration": 5.0
                },
                {
                    "type": "dialogue",
                    "speaker": "Elder Guardian",
                    "text": (
                        "The pain doesn't end, young one. But it changes. "
                        "And we're here to carry it with you."
                    ),
                    "duration": 5.0
                },
                {
                    "type": "text",
                    "speaker": "Narrator",
                    "text": (
                        "Justice was served. The loss remains. "
                        "But you are not alone in bearing it.\n\n"
                        "And that is enough."
                    ),
                    "duration": 5.0
                },
                {
                    "type": "credits",
                    "text": "THE END - The Path of Justice",
                    "duration": 3.0
                }
            ]
        }

    def complete_ending(self):
        """Mark ending as complete"""
        self.state = EndingState.COMPLETED

        if self.on_ending_complete_callback:
            self.on_ending_complete_callback(self.choice_made, self.ending_data)

    def get_hub_final_state(self) -> Optional[Dict]:
        """Get final hub state after ending"""
        if self.ending_data:
            return self.ending_data.hub_final_state
        return None

    def get_constellation_position(self) -> Dict[str, float]:
        """
        Get Yin & Yang star constellation position.

        Returns:
            Dictionary with star positions for rendering
        """
        # Position in night sky (normalized 0.0-1.0)
        return {
            "yin": {
                "x": 0.45,  # Left of center
                "y": 0.25,  # Upper sky
                "brightness": 0.9,
                "pulse_speed": 0.5  # Slow, steady pulse
            },
            "yang": {
                "x": 0.55,  # Right of center
                "y": 0.25,  # Upper sky
                "brightness": 0.85,
                "pulse_speed": 1.2  # Faster, flickering pulse
            }
        }

    def is_ending_complete(self) -> bool:
        """Check if ending has been completed"""
        return self.state == EndingState.COMPLETED

    def get_ending_achievement_data(self) -> Optional[Dict]:
        """Get achievement/unlock data for ending"""
        if not self.ending_data:
            return None

        base_achievements = [
            {
                "id": "complete_campaign",
                "name": "The Hollowed Journey",
                "description": "Complete the campaign"
            },
            {
                "id": "final_boss_defeated",
                "name": "Veil Broken",
                "description": "Defeat The Veil Maiden"
            }
        ]

        if self.choice_made == EndingChoice.SAVE:
            base_achievements.append({
                "id": "mercy_ending",
                "name": "Path of Mercy",
                "description": "Choose to save The Veil Maiden"
            })
        elif self.choice_made == EndingChoice.DESTROY:
            base_achievements.append({
                "id": "justice_ending",
                "name": "Path of Justice",
                "description": "Choose to destroy The Veil Maiden"
            })

        return {
            "achievements": base_achievements,
            "unlocks": [
                {
                    "id": "constellation_visible",
                    "name": "Yin & Yang Constellation",
                    "description": "Visible in hub night sky"
                },
                {
                    "id": "ng_plus",
                    "name": "New Game+",
                    "description": "Replay with enhanced difficulty"
                }
            ]
        }

    def to_dict(self) -> Dict:
        """Serialize ending state to dictionary"""
        return {
            "state": self.state.value,
            "choice_made": self.choice_made.value,
            "ending_data": {
                "ending_id": self.ending_data.ending_id,
                "choice": self.ending_data.choice.value,
                "veil_maiden_fate": self.ending_data.veil_maiden_fate
            } if self.ending_data else None
        }

    @staticmethod
    def from_dict(data: Dict) -> 'EndingManager':
        """Load ending state from dictionary"""
        manager = EndingManager()
        manager.state = EndingState(data.get("state", "not_started"))
        manager.choice_made = EndingChoice(data.get("choice_made", "not_chosen"))

        if data.get("ending_data"):
            ending_data = data["ending_data"]
            choice = EndingChoice(ending_data["choice"])
            manager.ending_data = manager.endings.get(choice)

        return manager


# ============================================================
# Helper Functions
# ============================================================

def create_ending_manager() -> EndingManager:
    """Create a new ending manager instance"""
    return EndingManager()


def get_ending_summary(choice: EndingChoice) -> str:
    """Get text summary of an ending"""
    summaries = {
        EndingChoice.SAVE: (
            "You extended mercy to The Veil Maiden, offering her redemption. "
            "Though Yin and Yang remain as distant stars, you found that "
            "healing others helped heal yourself. The hub glows with warm light "
            "as The Lanterns—and your former enemy—sit together in community."
        ),
        EndingChoice.DESTROY: (
            "You ended The Veil Maiden's threat, bringing justice for what was taken. "
            "Though Yin and Yang remain as distant stars, and emptiness lingers, "
            "The Lanterns stand with you in your grief. Victory came at a cost, "
            "but you are not alone in bearing it."
        )
    }
    return summaries.get(choice, "")
