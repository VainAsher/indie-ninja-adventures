package com.indieniinja.procgen.ui;

import java.util.ArrayList;
import java.util.List;

public final class SelectionModel {

    private int zoneX = -1;
    private int zoneY = -1;
    private final List<Runnable> listeners = new ArrayList<>();

    public void addChangeListener(Runnable listener) {
        listeners.add(listener);
    }

    public void select(int zx, int zy) {
        this.zoneX = zx;
        this.zoneY = zy;
        for (Runnable r : listeners) r.run();
    }

    public void clear() {
        zoneX = -1;
        zoneY = -1;
        for (Runnable r : listeners) r.run();
    }

    public boolean hasSelection() { return zoneX >= 0; }
    public int getZoneX()        { return zoneX; }
    public int getZoneY()        { return zoneY; }
}
