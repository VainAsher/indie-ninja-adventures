"""
Mod System - Plugin architecture for extensibility

Allows users to create mods that:
- Add custom entities with behaviors
- Register custom components
- Add custom mechanics
- Modify game rules
- Load custom assets
"""

import importlib.util
import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from core.entity_system import ComponentRegistry
from core.event_bus import EventBus

# ============================================================================
# Mod Metadata
# ============================================================================


@dataclass
class ModMetadata:
    """Mod metadata from manifest"""

    mod_id: str
    name: str
    version: str
    author: str
    description: str
    dependencies: list[str]
    entry_point: str  # Python module to load


# ============================================================================
# Mod Lifecycle
# ============================================================================


class ModInterface:
    """
    Base interface for mods

    Mods should implement this interface to hook into the game.
    """

    def __init__(self, mod_id: str):
        self.mod_id = mod_id

    def on_load(self, game_context: "GameContext"):
        """Called when mod is loaded (before game starts)"""
        pass

    def on_enable(self, game_context: "GameContext"):
        """Called when mod is enabled (game running)"""
        pass

    def on_disable(self, game_context: "GameContext"):
        """Called when mod is disabled"""
        pass

    def on_unload(self, game_context: "GameContext"):
        """Called when mod is unloaded (cleanup)"""
        pass


# ============================================================================
# Game Context (for mods)
# ============================================================================


@dataclass
class GameContext:
    """
    Game context provided to mods

    Gives mods access to core systems without tight coupling.
    """

    event_bus: EventBus
    component_registry: ComponentRegistry
    logger: logging.Logger

    # Hook registries
    custom_hooks: dict[str, list[Callable]] = None

    def __post_init__(self):
        if self.custom_hooks is None:
            self.custom_hooks = {}

    def register_hook(self, hook_name: str, callback: Callable):
        """
        Register custom hook

        Args:
            hook_name: Hook name (e.g., "on_player_spawn", "on_level_complete")
            callback: Callback function
        """
        if hook_name not in self.custom_hooks:
            self.custom_hooks[hook_name] = []
        self.custom_hooks[hook_name].append(callback)
        self.logger.info(f"Registered hook: {hook_name}")

    def trigger_hook(self, hook_name: str, *args, **kwargs):
        """
        Trigger custom hook

        Args:
            hook_name: Hook name
            *args, **kwargs: Arguments to pass to callbacks
        """
        if hook_name not in self.custom_hooks:
            return

        for callback in self.custom_hooks[hook_name]:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Error in hook '{hook_name}': {e}", exc_info=True)


# ============================================================================
# Mod Loader
# ============================================================================


class ModLoader:
    """
    Mod loader and manager

    Features:
    - Load mods from directories
    - Manage mod lifecycle
    - Handle dependencies
    - Sandbox mods (future: security)
    """

    def __init__(
        self,
        mods_directory: Path,
        game_context: GameContext,
        logger: logging.Logger | None = None,
    ):
        self.mods_directory = mods_directory
        self.game_context = game_context
        self.logger = logger or logging.getLogger("ninja_dash.mods")

        self.loaded_mods: dict[str, ModInterface] = {}
        self.mod_metadata: dict[str, ModMetadata] = {}

        # Ensure mods directory exists
        self.mods_directory.mkdir(parents=True, exist_ok=True)

    def discover_mods(self) -> list[Path]:
        """
        Discover mods in mods directory

        Returns:
            List of mod directories
        """
        if not self.mods_directory.exists():
            self.logger.warning(f"Mods directory not found: {self.mods_directory}")
            return []

        mod_dirs = []
        for item in self.mods_directory.iterdir():
            if item.is_dir() and (item / "mod.json").exists():
                mod_dirs.append(item)

        self.logger.info(f"Discovered {len(mod_dirs)} mods")
        return mod_dirs

    def load_mod(self, mod_path: Path) -> bool:
        """
        Load mod from directory

        Args:
            mod_path: Path to mod directory

        Returns:
            True if loaded successfully
        """
        try:
            # Load metadata
            import json

            metadata_path = mod_path / "mod.json"
            with open(metadata_path) as f:
                metadata_dict = json.load(f)

            metadata = ModMetadata(
                mod_id=metadata_dict["mod_id"],
                name=metadata_dict["name"],
                version=metadata_dict["version"],
                author=metadata_dict["author"],
                description=metadata_dict.get("description", ""),
                dependencies=metadata_dict.get("dependencies", []),
                entry_point=metadata_dict.get("entry_point", "main.py"),
            )

            # Check if already loaded
            if metadata.mod_id in self.loaded_mods:
                self.logger.warning(f"Mod '{metadata.mod_id}' already loaded")
                return False

            # Load Python module
            entry_path = mod_path / metadata.entry_point
            if not entry_path.exists():
                self.logger.error(f"Entry point not found: {entry_path}")
                return False

            spec = importlib.util.spec_from_file_location(f"mods.{metadata.mod_id}", entry_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            # Get mod instance
            if not hasattr(module, "get_mod"):
                self.logger.error(f"Mod '{metadata.mod_id}' missing get_mod() function")
                return False

            mod_instance = module.get_mod()
            if not isinstance(mod_instance, ModInterface):
                self.logger.error(f"Mod '{metadata.mod_id}' does not implement ModInterface")
                return False

            # Store mod
            self.loaded_mods[metadata.mod_id] = mod_instance
            self.mod_metadata[metadata.mod_id] = metadata

            # Call lifecycle hook
            mod_instance.on_load(self.game_context)

            self.logger.info(
                f"Loaded mod: {metadata.name} v{metadata.version} by {metadata.author}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to load mod from {mod_path}: {e}", exc_info=True)
            return False

    def load_all_mods(self):
        """Discover and load all mods"""
        mod_dirs = self.discover_mods()

        for mod_dir in mod_dirs:
            self.load_mod(mod_dir)

        self.logger.info(f"Loaded {len(self.loaded_mods)}/{len(mod_dirs)} mods")

    def enable_mod(self, mod_id: str):
        """Enable mod (call on_enable)"""
        mod = self.loaded_mods.get(mod_id)
        if not mod:
            self.logger.warning(f"Mod '{mod_id}' not loaded")
            return

        mod.on_enable(self.game_context)
        self.logger.info(f"Enabled mod: {mod_id}")

    def disable_mod(self, mod_id: str):
        """Disable mod (call on_disable)"""
        mod = self.loaded_mods.get(mod_id)
        if not mod:
            self.logger.warning(f"Mod '{mod_id}' not loaded")
            return

        mod.on_disable(self.game_context)
        self.logger.info(f"Disabled mod: {mod_id}")

    def enable_all_mods(self):
        """Enable all loaded mods"""
        for mod_id in self.loaded_mods:
            self.enable_mod(mod_id)

    def get_loaded_mods(self) -> list[ModMetadata]:
        """Get list of loaded mod metadata"""
        return list(self.mod_metadata.values())


# ============================================================================
# Example Mod Template (for documentation)
# ============================================================================

EXAMPLE_MOD_TEMPLATE = '''
# Example Mod for Vain Asher Gaming's: Indie Ninja Adventures
# Place this in: user_data/mods/example_mod/main.py

from core.mod_system import ModInterface, GameContext
from core.entity_system import Component, EntityType
from core.event_bus import TickEvent

class ExampleComponent(Component):
    """Example custom component"""

    def __init__(self, entity_id: int, custom_value: int = 0):
        super().__init__(entity_id)
        self.custom_value = custom_value

    def update(self, dt: float, entity_manager):
        # Custom logic here
        pass

class ExampleMod(ModInterface):
    """Example mod implementation"""

    def __init__(self):
        super().__init__("example_mod")

    def on_load(self, game_context: GameContext):
        # Register custom component
        game_context.component_registry.register_component(
            "example_component",
            ExampleComponent
        )

        # Subscribe to events
        def on_tick(event: TickEvent):
            # Do something every tick
            pass

        game_context.event_bus.subscribe(TickEvent, on_tick)

        # Register custom hook
        def on_player_spawn(player_entity):
            game_context.logger.info("Player spawned!")

        game_context.register_hook("on_player_spawn", on_player_spawn)

        game_context.logger.info("Example mod loaded!")

    def on_enable(self, game_context: GameContext):
        game_context.logger.info("Example mod enabled!")

    def on_disable(self, game_context: GameContext):
        game_context.logger.info("Example mod disabled!")

    def on_unload(self, game_context: GameContext):
        game_context.logger.info("Example mod unloaded!")

# Required: Return mod instance
def get_mod():
    return ExampleMod()
'''

EXAMPLE_MOD_MANIFEST = """
{
  "mod_id": "example_mod",
  "name": "Example Mod",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "An example mod for Vain Asher Gaming's: Indie Ninja Adventures",
  "dependencies": [],
  "entry_point": "main.py"
}
"""
