package com.indieniinja.client.game.cutscene;

import java.util.Locale;
import java.util.Map;

public record CutsceneTrigger(CutsceneTriggerType type, String id) {
    public boolean matches(CutsceneTriggerType type, String id) {
        return this.type == type && this.id != null && this.id.equals(id);
    }

    public static CutsceneTrigger fromMap(Map<String, Object> map, String cutsceneId, int index) {
        String event = str(map, "event");
        String id = str(map, "id");
        if (event == null || event.isBlank()) {
            throw new CutsceneLoadException(cutsceneId + " trigger[" + index + "]: missing 'event'");
        }
        if (id == null || id.isBlank()) {
            throw new CutsceneLoadException(cutsceneId + " trigger[" + index + "]: missing 'id'");
        }
        try {
            return new CutsceneTrigger(CutsceneTriggerType.valueOf(event.toUpperCase(Locale.ROOT)), id);
        } catch (IllegalArgumentException e) {
            throw new CutsceneLoadException(cutsceneId + " trigger[" + index + "]: unknown event '" + event + "'");
        }
    }

    private static String str(Map<String, Object> map, String key) {
        Object value = map.get(key);
        return value instanceof String s ? s : null;
    }
}
