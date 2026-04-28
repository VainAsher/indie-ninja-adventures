package com.indieniinja.client.game.cutscene;

import com.indieniinja.client.game.StoryManager;

import java.util.List;
import java.util.Map;

/**
 * Immutable data object representing one authored cutscene.
 *
 * Loaded from data/cutscenes/&lt;id&gt;.json by {@link CutsceneLoader}.
 */
public final class CutsceneDefinition {

    public final String            id;
    public final int               version;
    public final int               act;
    public final boolean           blocking;
    public final SkipPolicy        skipPolicy;
    public final List<StartCondition> startConditions;
    public final List<String>      completionFlags;
    public final List<CutsceneStep> steps;

    private CutsceneDefinition(Builder b) {
        this.id              = b.id;
        this.version         = b.version;
        this.act             = b.act;
        this.blocking        = b.blocking;
        this.skipPolicy      = b.skipPolicy;
        this.startConditions = List.copyOf(b.startConditions);
        this.completionFlags = List.copyOf(b.completionFlags);
        this.steps           = List.copyOf(b.steps);
    }

    /** Returns true when all start conditions pass for the given story state. */
    public boolean conditionsMet(StoryManager story) {
        for (StartCondition c : startConditions) {
            if (!c.isMet(story)) return false;
        }
        return true;
    }

    @SuppressWarnings("unchecked")
    public static CutsceneDefinition fromMap(Map<String, Object> m) {
        String id = (String) m.get("id");
        if (id == null || id.isBlank())
            throw new CutsceneLoadException("cutscene definition missing required 'id' field");

        int version = intVal(m, "version", 1);
        int act     = intVal(m, "act", 1);
        boolean blocking = boolVal(m, "blocking", true);

        SkipPolicy skipPolicy = SkipPolicy.ALLOW_AFTER_FIRST_VIEW;
        String spStr = (String) m.get("skip_policy");
        if (spStr != null) {
            try {
                skipPolicy = SkipPolicy.valueOf(spStr.toUpperCase());
            } catch (IllegalArgumentException e) {
                throw new CutsceneLoadException(id + ": unknown skip_policy '" + spStr + "'");
            }
        }

        List<Map<String, Object>> condMaps =
                (List<Map<String, Object>>) m.getOrDefault("start_conditions", List.of());
        List<StartCondition> conditions = condMaps.stream()
                .map(StartCondition::fromMap)
                .toList();

        List<String> flags = (List<String>) m.getOrDefault("completion_flags", List.of());

        List<Map<String, Object>> stepMaps =
                (List<Map<String, Object>>) m.getOrDefault("steps", List.of());
        List<CutsceneStep> steps = new java.util.ArrayList<>();
        for (int i = 0; i < stepMaps.size(); i++) {
            steps.add(CutsceneStep.fromMap(stepMaps.get(i), id, i));
        }

        return new Builder(id)
                .version(version).act(act).blocking(blocking).skipPolicy(skipPolicy)
                .startConditions(conditions).completionFlags(flags).steps(steps)
                .build();
    }

    private static int intVal(Map<String, Object> m, String key, int def) {
        Object v = m.get(key);
        return v instanceof Number n ? n.intValue() : def;
    }

    private static boolean boolVal(Map<String, Object> m, String key, boolean def) {
        Object v = m.get(key);
        if (v instanceof Boolean b) return b;
        if (v instanceof String s)  return "true".equalsIgnoreCase(s);
        return def;
    }

    // ── Builder ───────────────────────────────────────────────────────────────

    public static final class Builder {
        private final String id;
        private int       version    = 1;
        private int       act        = 1;
        private boolean   blocking   = true;
        private SkipPolicy skipPolicy = SkipPolicy.ALLOW_AFTER_FIRST_VIEW;
        private List<StartCondition> startConditions = List.of();
        private List<String>         completionFlags = List.of();
        private List<CutsceneStep>   steps           = List.of();

        public Builder(String id)                               { this.id = id; }
        public Builder version(int v)                           { this.version = v;         return this; }
        public Builder act(int v)                               { this.act = v;             return this; }
        public Builder blocking(boolean v)                      { this.blocking = v;        return this; }
        public Builder skipPolicy(SkipPolicy v)                 { this.skipPolicy = v;      return this; }
        public Builder startConditions(List<StartCondition> v)  { this.startConditions = v; return this; }
        public Builder completionFlags(List<String> v)          { this.completionFlags = v; return this; }
        public Builder steps(List<CutsceneStep> v)              { this.steps = v;           return this; }
        public CutsceneDefinition build()                       { return new CutsceneDefinition(this); }
    }
}
