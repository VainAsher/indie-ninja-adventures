"""
Dialogue System - NPC Conversation Trees

This module provides branching dialogue functionality for NPCs:
- Dialogue tree data structures
- Choice-based navigation
- Conditional requirements (including act-based conditions)
- Event emission on dialogue events
- Act-conditional dialogue selection

Version: v0.7.0
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import json

from core import EventBus


@dataclass
class DialogueChoice:
    """
    A choice option in a dialogue node.

    Represents a player response option with potential conditions and events.
    """
    choice_text: str  # Choice label (max 60 chars recommended)
    next_node_id: Optional[str]  # Where this choice leads (None = end dialogue)
    requires: Optional[str] = None  # Condition (e.g., "has_item:forest_key")
    on_select_event: Optional[str] = None  # Event to emit when selected


@dataclass
class DialogueNode:
    """
    A single node in a dialogue tree.

    Represents one piece of dialogue with optional choices or auto-advance.
    """
    node_id: str
    speaker: str  # NPC name
    text: str  # Dialogue content (max 180 chars recommended)
    choices: List[DialogueChoice] = field(default_factory=list)
    next_node_id: Optional[str] = None  # Auto-advance if no choices
    on_exit_event: Optional[str] = None  # Event to emit when leaving node


@dataclass
class DialogueTree:
    """
    A complete dialogue conversation tree.

    Contains all nodes and choices for a single NPC dialogue.
    """
    dialogue_id: str
    root_node_id: str  # Starting node
    nodes: Dict[str, DialogueNode]


class DialogueManager:
    """
    Manages dialogue trees and conversation state.

    Handles loading dialogue data, tracking current conversation state,
    and emitting events based on dialogue progression.
    """

    def __init__(self, event_bus: EventBus):
        """
        Initialize dialogue manager.

        Args:
            event_bus: Event bus for emitting dialogue events
        """
        self.event_bus = event_bus
        self.dialogues: Dict[str, DialogueTree] = {}
        self.current_dialogue: Optional[DialogueTree] = None
        self.current_node: Optional[DialogueNode] = None
        self.history: List[str] = []  # Node IDs visited in current dialogue

        # Story state for conditional dialogue (set externally)
        self.story_state: Dict[str, Any] = {}  # e.g., {"act": 0, "companions_present": True}

    def load_dialogues(self, filepath: str):
        """
        Load dialogue trees from JSON file.

        Args:
            filepath: Path to dialogues.json file
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for dialogue_id, dialogue_data in data.items():
                # Parse nodes
                nodes = {}
                for node_id, node_data in dialogue_data.get('nodes', {}).items():
                    # Parse choices
                    choices = []
                    for choice_data in node_data.get('choices', []):
                        choice = DialogueChoice(
                            choice_text=choice_data['choice_text'],
                            next_node_id=choice_data.get('next_node_id'),
                            requires=choice_data.get('requires'),
                            on_select_event=choice_data.get('on_select_event')
                        )
                        choices.append(choice)

                    # Create node
                    node = DialogueNode(
                        node_id=node_data['node_id'],
                        speaker=node_data['speaker'],
                        text=node_data['text'],
                        choices=choices,
                        next_node_id=node_data.get('next_node_id'),
                        on_exit_event=node_data.get('on_exit_event')
                    )
                    nodes[node_id] = node

                # Create dialogue tree
                dialogue_tree = DialogueTree(
                    dialogue_id=dialogue_data['dialogue_id'],
                    root_node_id=dialogue_data['root_node_id'],
                    nodes=nodes
                )

                self.dialogues[dialogue_id] = dialogue_tree
                print(f"[DIALOGUE] Loaded dialogue tree: {dialogue_id} ({len(nodes)} nodes)")

        except FileNotFoundError:
            print(f"[WARNING] Dialogue file not found: {filepath}")
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse dialogue JSON: {e}")
        except Exception as e:
            print(f"[ERROR] Failed to load dialogues: {e}")

    def start_dialogue(self, dialogue_id: str) -> bool:
        """
        Start a dialogue conversation.

        Args:
            dialogue_id: ID of dialogue tree to start

        Returns:
            True if dialogue started successfully, False otherwise
        """
        if dialogue_id not in self.dialogues:
            print(f"[WARNING] Dialogue not found: {dialogue_id}")
            return False

        self.current_dialogue = self.dialogues[dialogue_id]
        root_node_id = self.current_dialogue.root_node_id

        if root_node_id not in self.current_dialogue.nodes:
            print(f"[ERROR] Root node not found: {root_node_id}")
            self.current_dialogue = None
            return False

        self.current_node = self.current_dialogue.nodes[root_node_id]
        self.history = [root_node_id]

        print(f"[DIALOGUE] Started dialogue: {dialogue_id} at node '{root_node_id}'")
        return True

    def get_current_node(self) -> Optional[DialogueNode]:
        """Get the current dialogue node."""
        return self.current_node

    def get_available_choices(self) -> List[DialogueChoice]:
        """
        Get available choices for current node.

        Filters out choices with unmet requirements.

        Returns:
            List of available choices
        """
        if not self.current_node:
            return []

        # For now, return all choices (requirement checking can be added later)
        return self.current_node.choices

    def select_choice(self, choice_index: int) -> bool:
        """
        Select a dialogue choice and navigate to next node.

        Args:
            choice_index: Index of choice to select

        Returns:
            True if choice was valid and navigation succeeded
        """
        if not self.current_node or not self.current_dialogue:
            return False

        available_choices = self.get_available_choices()

        if choice_index < 0 or choice_index >= len(available_choices):
            print(f"[WARNING] Invalid choice index: {choice_index}")
            return False

        choice = available_choices[choice_index]

        # Emit selection event if specified
        if choice.on_select_event:
            # TODO: Emit custom event based on event string
            print(f"[DIALOGUE] Choice event: {choice.on_select_event}")

        # Navigate to next node
        next_node_id = choice.next_node_id

        if next_node_id is None:
            # Choice ends dialogue
            self.end_dialogue()
            return True

        if next_node_id not in self.current_dialogue.nodes:
            print(f"[ERROR] Next node not found: {next_node_id}")
            self.end_dialogue()
            return False

        self.current_node = self.current_dialogue.nodes[next_node_id]
        self.history.append(next_node_id)

        print(f"[DIALOGUE] Navigated to node: {next_node_id}")
        return True

    def advance(self) -> bool:
        """
        Auto-advance to next node (for nodes without choices).

        Returns:
            True if advanced successfully
        """
        if not self.current_node or not self.current_dialogue:
            return False

        # Can't auto-advance if there are choices
        if self.current_node.choices:
            print("[WARNING] Cannot auto-advance: node has choices")
            return False

        next_node_id = self.current_node.next_node_id

        if next_node_id is None:
            # No next node, end dialogue
            self.end_dialogue()
            return True

        if next_node_id not in self.current_dialogue.nodes:
            print(f"[ERROR] Next node not found: {next_node_id}")
            self.end_dialogue()
            return False

        self.current_node = self.current_dialogue.nodes[next_node_id]
        self.history.append(next_node_id)

        print(f"[DIALOGUE] Advanced to node: {next_node_id}")
        return True

    def end_dialogue(self):
        """End current dialogue and emit exit event."""
        if self.current_node and self.current_node.on_exit_event:
            # TODO: Emit custom event based on event string
            print(f"[DIALOGUE] Exit event: {self.current_node.on_exit_event}")

        print(f"[DIALOGUE] Ended dialogue (visited {len(self.history)} nodes)")

        self.current_dialogue = None
        self.current_node = None
        self.history.clear()

    def is_active(self) -> bool:
        """Check if a dialogue is currently active."""
        return self.current_node is not None

    def set_story_state(self, story_state: Dict[str, Any]):
        """
        Set current story state for conditional dialogue.

        Args:
            story_state: Dictionary with story flags (e.g., {"act": 0, "companions_present": True})
        """
        self.story_state = story_state

    def check_condition(self, condition: Optional[str]) -> bool:
        """
        Check if a condition is met based on current story state.

        Args:
            condition: Condition string (e.g., "act:0", "act:>=2", "has_item:forest_key")

        Returns:
            True if condition is met or no condition specified
        """
        if not condition:
            return True  # No condition means always available

        # Parse condition format: "key:value" or "key:operator:value"
        parts = condition.split(':')

        if len(parts) < 2:
            print(f"[WARNING] Invalid condition format: {condition}")
            return False

        key = parts[0]

        # Check for comparison operators
        if len(parts) == 3:
            operator = parts[1]
            value_str = parts[2]
        else:
            operator = "=="
            value_str = parts[1]

        # Get current value from story state
        current_value = self.story_state.get(key)

        if current_value is None:
            return False  # Key not in story state

        # Convert value to appropriate type
        try:
            # Try to convert to int first
            target_value = int(value_str)
            if not isinstance(current_value, int):
                current_value = int(current_value)
        except ValueError:
            # If not int, compare as strings
            target_value = value_str

        # Evaluate condition based on operator
        if operator == "==":
            return current_value == target_value
        elif operator == "!=":
            return current_value != target_value
        elif operator == ">":
            return current_value > target_value
        elif operator == ">=":
            return current_value >= target_value
        elif operator == "<":
            return current_value < target_value
        elif operator == "<=":
            return current_value <= target_value
        else:
            print(f"[WARNING] Unknown operator in condition: {operator}")
            return False

    def select_dialogue_by_conditions(self, dialogue_ids: List[str]) -> Optional[str]:
        """
        Select the best matching dialogue ID based on story conditions.

        Dialogue IDs should be in format "npc_name_act0", "npc_name_act2", etc.
        The system will look for a matching condition in the dialogue tree metadata.

        Args:
            dialogue_ids: List of dialogue IDs to choose from

        Returns:
            Best matching dialogue ID, or None if none match
        """
        # For each dialogue, check if it has act requirements
        # and return the first one that matches current state
        for dialogue_id in dialogue_ids:
            if dialogue_id in self.dialogues:
                # Check if dialogue ID contains act number (simple heuristic)
                # Format: "npc_name_act0", "npc_name_act2", etc.
                if "_act" in dialogue_id:
                    try:
                        # Extract act number from ID
                        act_part = dialogue_id.split("_act")[-1]
                        # Get just the number (e.g., "0" from "0_intro" or "2")
                        act_num = int(act_part.split("_")[0])

                        # Check if this matches current act
                        if self.story_state.get("act") == act_num:
                            return dialogue_id
                    except (ValueError, IndexError):
                        # If parsing fails, skip this dialogue
                        continue
                else:
                    # No act requirement, this is a fallback dialogue
                    # Check if no act-specific dialogue matched yet
                    return dialogue_id

        # If no dialogue matched, return first available or None
        return dialogue_ids[0] if dialogue_ids else None

    def get_npc_dialogue_id(self, npc_id: str, fallback_id: Optional[str] = None) -> Optional[str]:
        """
        Get the appropriate dialogue ID for an NPC based on current story state.

        This method looks for act-conditional dialogues in the format:
        - "npc_id_act0" for Act 0
        - "npc_id_act2" for Act 2
        - etc.

        Args:
            npc_id: Base NPC identifier (e.g., "elder", "shopkeeper")
            fallback_id: Fallback dialogue ID if no act-specific dialogue found

        Returns:
            Dialogue ID to use, or None if no dialogue found
        """
        current_act = self.story_state.get("act", 0)

        # Build list of dialogue IDs to try, in priority order
        dialogue_ids_to_try = [
            f"{npc_id}_act{current_act}",  # Act-specific dialogue
            f"{npc_id}",  # Base dialogue
        ]

        if fallback_id:
            dialogue_ids_to_try.append(fallback_id)

        # Try each dialogue ID in order
        for dialogue_id in dialogue_ids_to_try:
            if dialogue_id in self.dialogues:
                return dialogue_id

        return None
