package com.indieniinja.client.game.cutscene;

import java.util.Locale;
import java.util.Map;

public record CutsceneTrigger(CutsceneTriggerType type, String id) {
    public boolean matches(CutsceneTriggerType type, String id) {
        if (this.type != type) return false;
        if (type == CutsceneTriggerType.CAMPAIGN_START) return true;
        return this.id != null && this.id.equals(id);
    }

    public static CutsceneTrigger fromMap(Map<String, Object> map, String cutsceneId, int index) {
        String event = str(map, "event");
        String id = str(map, "id");
        if (event == null || event.isBlank()) {
            throw new CutsceneLoadException(cutsceneId + " trigger[" + index + "]: missing 'event'");
        }
        CutsceneTriggerType type;
        try {
            type = CutsceneTriggerType.valueOf(event.toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            throw new CutsceneLoadException(cutsceneId + " trigger[" + index + "]: unknown event '" + event + "'");
        }
        if (type != CutsceneTriggerType.CAMPAIGN_START && (id == null || id.isBlank())) {
            throw new CutsceneLoadException(cutsceneId + " trigger[" + index + "]: missing 'id'");
        }
        return new CutsceneTrigger(type, id != null ? id : "");
    }

    private static String str(Map<String, Object> map, String key) {
        Object value = map.get(key);
        return value instanceof String s ? s : null;
    }
}
