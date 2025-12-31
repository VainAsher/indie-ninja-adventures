"""
Entity System - Flexible entity management with component-based architecture

This system allows:
- NPCs, enemies, and players to share common mechanics
- Extensible entity types via composition
- Modding support through component registration
- Entity pooling for performance
"""

from typing import Dict, List, Optional, Set, Type, Any
from dataclasses import dataclass, field
from enum import Enum
from core.event_bus import EventBus, Event
from core.state import PhysicsState
import logging


# ============================================================================
# Entity Types
# ============================================================================

class EntityType(Enum):
    """Entity type enumeration"""
    PLAYER = "player"
    NPC = "npc"
    ENEMY = "enemy"
    PROJECTILE = "projectile"
    PICKUP = "pickup"
    HAZARD = "hazard"
    CUSTOM = "custom"  # For mods


# ============================================================================
# Entity Events
# ============================================================================

@dataclass
class EntitySpawnedEvent(Event):
    """Entity was spawned"""
    entity_id: int
    entity_type: EntityType

    def __init__(self, entity_id: int, entity_type: EntityType):
        super().__init__()
        self.entity_id = entity_id
        self.entity_type = entity_type


@dataclass
class EntityDestroyedEvent(Event):
    """Entity was destroyed"""
    entity_id: int
    entity_type: EntityType
    reason: str  # 'death', 'despawn', 'timeout', etc.

    def __init__(self, entity_id: int, entity_type: EntityType, reason: str):
        super().__init__()
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.reason = reason


# ============================================================================
# Component Base
# ============================================================================

class Component:
    """
    Base component class

    Components add functionality to entities through composition.
    Examples: MovementComponent, HealthComponent, AIComponent, etc.
    """

    def __init__(self, entity_id: int):
        self.entity_id = entity_id
        self.enabled = True

    def initialize(self, entity_manager: 'EntityManager'):
        """Called when component is attached to entity"""
        pass

    def update(self, dt: float, entity_manager: 'EntityManager'):
        """Called every physics tick"""
        pass

    def cleanup(self):
        """Called when component is removed or entity destroyed"""
        pass


# ============================================================================
# Entity Definition
# ============================================================================

@dataclass
class Entity:
    """
    Entity definition

    Entities are composed of:
    - Unique ID
    - Entity type
    - Physics state (optional)
    - Components (behavior, AI, health, etc.)
    - Custom data (for mods)
    """
    entity_id: int
    entity_type: EntityType
    physics: Optional[PhysicsState] = None
    components: Dict[Type[Component], Component] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)  # For queries (e.g., "enemy", "flying")
    custom_data: Dict[str, Any] = field(default_factory=dict)  # For mods
    active: bool = True

    def add_component(self, component: Component):
        """Add component to entity"""
        component_type = type(component)
        self.components[component_type] = component

    def get_component(self, component_type: Type[Component]) -> Optional[Component]:
        """Get component by type"""
        return self.components.get(component_type)

    def has_component(self, component_type: Type[Component]) -> bool:
        """Check if entity has component"""
        return component_type in self.components

    def remove_component(self, component_type: Type[Component]):
        """Remove component from entity"""
        if component_type in self.components:
            component = self.components.pop(component_type)
            component.cleanup()

    def has_tag(self, tag: str) -> bool:
        """Check if entity has tag"""
        return tag in self.tags

    def add_tag(self, tag: str):
        """Add tag to entity"""
        self.tags.add(tag)

    def remove_tag(self, tag: str):
        """Remove tag from entity"""
        self.tags.discard(tag)


# ============================================================================
# Entity Manager
# ============================================================================

class EntityManager:
    """
    Entity manager with component-based architecture

    Features:
    - Entity creation/destruction
    - Component management
    - Entity queries (by type, tag, component)
    - Entity pooling (future optimization)
    """

    def __init__(self, event_bus: EventBus, logger: Optional[logging.Logger] = None):
        self.event_bus = event_bus
        self.logger = logger

        self.entities: Dict[int, Entity] = {}
        self.next_entity_id = 0

        # Index for fast queries
        self._entities_by_type: Dict[EntityType, Set[int]] = {}
        self._entities_by_tag: Dict[str, Set[int]] = {}

    def create_entity(self, entity_type: EntityType,
                     physics: Optional[PhysicsState] = None,
                     tags: Optional[Set[str]] = None) -> Entity:
        """
        Create new entity

        Args:
            entity_type: Type of entity
            physics: Optional physics state
            tags: Optional tags for queries

        Returns:
            Created entity
        """
        entity_id = self._allocate_id()
        entity = Entity(
            entity_id=entity_id,
            entity_type=entity_type,
            physics=physics,
            tags=tags or set()
        )

        self.entities[entity_id] = entity

        # Update indices
        if entity_type not in self._entities_by_type:
            self._entities_by_type[entity_type] = set()
        self._entities_by_type[entity_type].add(entity_id)

        for tag in entity.tags:
            if tag not in self._entities_by_tag:
                self._entities_by_tag[tag] = set()
            self._entities_by_tag[tag].add(entity_id)

        # Emit spawn event
        self.event_bus.emit(EntitySpawnedEvent(entity_id, entity_type))

        if self.logger:
            self.logger.info(f"Entity {entity_id} ({entity_type.value}) spawned")

        return entity

    def destroy_entity(self, entity_id: int, reason: str = "destroyed"):
        """
        Destroy entity

        Args:
            entity_id: Entity to destroy
            reason: Reason for destruction
        """
        entity = self.entities.get(entity_id)
        if not entity:
            if self.logger:
                self.logger.warning(f"Attempted to destroy non-existent entity {entity_id}")
            return

        # Cleanup components
        for component in list(entity.components.values()):
            component.cleanup()

        # Remove from indices
        self._entities_by_type[entity.entity_type].discard(entity_id)
        for tag in entity.tags:
            self._entities_by_tag[tag].discard(entity_id)

        # Emit destroy event
        self.event_bus.emit(EntityDestroyedEvent(
            entity_id, entity.entity_type, reason
        ))

        # Remove entity
        del self.entities[entity_id]

        if self.logger:
            self.logger.info(f"Entity {entity_id} destroyed: {reason}")

    def get_entity(self, entity_id: int) -> Optional[Entity]:
        """Get entity by ID"""
        return self.entities.get(entity_id)

    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """Get all entities of a type"""
        entity_ids = self._entities_by_type.get(entity_type, set())
        return [self.entities[eid] for eid in entity_ids if eid in self.entities]

    def get_entities_by_tag(self, tag: str) -> List[Entity]:
        """Get all entities with a tag"""
        entity_ids = self._entities_by_tag.get(tag, set())
        return [self.entities[eid] for eid in entity_ids if eid in self.entities]

    def get_entities_with_component(self, component_type: Type[Component]) -> List[Entity]:
        """Get all entities with a specific component"""
        return [
            entity for entity in self.entities.values()
            if entity.has_component(component_type)
        ]

    def update_all_components(self, dt: float):
        """Update all entity components"""
        for entity in self.entities.values():
            if not entity.active:
                continue

            for component in entity.components.values():
                if component.enabled:
                    component.update(dt, self)

    def get_entity_count(self) -> int:
        """Get total entity count"""
        return len(self.entities)

    def get_entity_count_by_type(self, entity_type: EntityType) -> int:
        """Get entity count by type"""
        return len(self._entities_by_type.get(entity_type, set()))

    def clear_all(self):
        """Destroy all entities (e.g., on level change)"""
        entity_ids = list(self.entities.keys())
        for entity_id in entity_ids:
            self.destroy_entity(entity_id, reason="level_clear")

    def _allocate_id(self) -> int:
        """Allocate new entity ID"""
        entity_id = self.next_entity_id
        self.next_entity_id += 1
        return entity_id


# ============================================================================
# Component Registry (for modding)
# ============================================================================

class ComponentRegistry:
    """
    Component registry for modding support

    Allows mods to register custom components that can be attached to entities.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger
        self.registered_components: Dict[str, Type[Component]] = {}

    def register_component(self, name: str, component_class: Type[Component]):
        """
        Register component type

        Args:
            name: Component name (e.g., "custom_ai")
            component_class: Component class
        """
        if name in self.registered_components:
            if self.logger:
                self.logger.warning(f"Component '{name}' already registered, overwriting")

        self.registered_components[name] = component_class

        if self.logger:
            self.logger.info(f"Registered component: {name}")

    def get_component(self, name: str) -> Optional[Type[Component]]:
        """Get component class by name"""
        return self.registered_components.get(name)

    def create_component(self, name: str, entity_id: int, **kwargs) -> Optional[Component]:
        """
        Create component instance

        Args:
            name: Component name
            entity_id: Entity ID to attach to
            **kwargs: Component constructor arguments

        Returns:
            Component instance or None if not found
        """
        component_class = self.registered_components.get(name)
        if not component_class:
            if self.logger:
                self.logger.error(f"Component '{name}' not found in registry")
            return None

        try:
            return component_class(entity_id, **kwargs)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to create component '{name}': {e}")
            return None

    def list_components(self) -> List[str]:
        """List all registered components"""
        return list(self.registered_components.keys())
