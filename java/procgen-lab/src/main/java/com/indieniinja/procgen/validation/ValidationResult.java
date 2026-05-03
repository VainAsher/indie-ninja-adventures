package com.indieniinja.procgen.validation;

import java.util.ArrayList;
import java.util.List;

public final class ValidationResult {
    public boolean valid = true;
    public final List<String> errors   = new ArrayList<>();
    public final List<String> warnings = new ArrayList<>();
    /** Flood-fill reachability grid [tileX][tileY], populated by TraversalValidator. */
    public boolean[][] reachable;

    public void error(String message) {
        valid = false;
        errors.add(message);
    }

    public void warn(String message) {
        warnings.add(message);
    }
}
