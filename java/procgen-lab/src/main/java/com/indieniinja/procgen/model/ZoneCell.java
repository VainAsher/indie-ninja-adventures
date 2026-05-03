package com.indieniinja.procgen.model;

public final class ZoneCell {
    public ZoneBase    base         = ZoneBase.SOLID_FILL;
    public ZoneSurface surface      = ZoneSurface.NONE;
    public FillVariant variant      = FillVariant.SOLID_8X8;
    public boolean     criticalPath = false;
}
