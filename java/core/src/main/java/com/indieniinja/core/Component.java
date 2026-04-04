package com.indieniinja.core;

/**
 * Base component class.
 * Java equivalent of Python core/entity_system.py Component.
 * Components add behaviour to entities through composition.
 */
public abstract class Component {

    public final int entityId;
    public boolean   enabled = true;

    protected Component(int entityId) {
        this.entityId = entityId;
    }

    /** Called once when the component is attached to an entity. */
    public void initialize(EntityManager em) {}

    /** Called every physics tick at 60 Hz. */
    public void update(float dt, EntityManager em) {}

    /** Called on removal or entity destruction. */
    public void cleanup() {}
}
