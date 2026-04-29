package com.indieniinja.world.progression;

import java.util.List;
import java.util.Set;

public record ProgressionValidationResult(
        boolean valid,
        String message,
        Set<String> reachableNodeIds,
        Set<String> collectedGrants,
        List<String> blockedNodeIds) {
    public ProgressionValidationResult {
        reachableNodeIds = Set.copyOf(reachableNodeIds);
        collectedGrants = Set.copyOf(collectedGrants);
        blockedNodeIds = List.copyOf(blockedNodeIds);
    }
}
