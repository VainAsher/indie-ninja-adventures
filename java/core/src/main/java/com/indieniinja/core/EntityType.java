package com.indieniinja.core;

/**
 * Entity type enumeration.
 * Java equivalent of Python core/entity_system.py EntityType.
 */
public enum EntityType {
    PLAYER,
    NPC,
    ENEMY,
    PROJECTILE,
    PICKUP,
    HAZARD,
    CUSTOM   // for mods
}
