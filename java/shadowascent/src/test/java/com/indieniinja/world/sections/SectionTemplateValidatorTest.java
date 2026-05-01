package com.indieniinja.world.sections;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.nio.file.Path;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class SectionTemplateValidatorTest {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    @Test
    void validTemplateHasNoIssues() throws Exception {
        JsonNode root = json("""
            {
              "id": "forest_key_trial_a",
              "biome": "forest",
              "kind": "key_trial",
              "footprint": { "gridW": 3, "gridH": 2 },
              "nodeKinds": ["entry", "reward"],
              "edgeRules": [{ "from": "entry", "to": "reward" }],
              "requiredSockets": ["west_low_walk"],
              "anchors": [{ "id": "reward_anchor", "kind": "key_reward" }]
            }
            """);

        List<SectionTemplateValidationIssue> issues = SectionTemplateValidator.validate(
            Path.of("forest_key_trial_a.json"), root);

        assertThat(issues).isEmpty();
    }

    @Test
    void missingRequiredFieldReportsIssue() throws Exception {
        JsonNode root = json("""
            {
              "id": "forest_key_trial_b",
              "biome": "forest",
              "kind": "key_trial",
              "footprint": { "gridW": 3, "gridH": 2 },
              "edgeRules": [{ "from": "entry", "to": "reward" }],
              "requiredSockets": ["west_low_walk"],
              "anchors": [{ "id": "reward_anchor", "kind": "key_reward" }]
            }
            """);

        List<SectionTemplateValidationIssue> issues = SectionTemplateValidator.validate(
            Path.of("forest_key_trial_b.json"), root);

        assertThat(issues).anySatisfy(issue -> {
            assertThat(issue.kind()).isEqualTo("missing_required_field");
            assertThat(issue.field()).isEqualTo("nodeKinds");
        });
    }

    @Test
    void malformedSocketIdReportsIssue() throws Exception {
        JsonNode root = json("""
            {
              "id": "forest_key_trial_c",
              "biome": "forest",
              "kind": "key_trial",
              "footprint": { "gridW": 3, "gridH": 2 },
              "nodeKinds": ["entry", "reward"],
              "edgeRules": [{ "from": "entry", "to": "reward" }],
              "requiredSockets": ["west-low-walk"],
              "anchors": [{ "id": "reward_anchor", "kind": "key_reward" }]
            }
            """);

        List<SectionTemplateValidationIssue> issues = SectionTemplateValidator.validate(
            Path.of("forest_key_trial_c.json"), root);

        assertThat(issues).anySatisfy(issue -> {
            assertThat(issue.kind()).isEqualTo("invalid_socket_id");
            assertThat(issue.field()).isEqualTo("requiredSockets[0]");
        });
    }

    @Test
    void emptyAnchorsReportsIssueForRequiredKinds() throws Exception {
        JsonNode root = json("""
            {
              "id": "forest_key_trial_d",
              "biome": "forest",
              "kind": "key_trial",
              "footprint": { "gridW": 3, "gridH": 2 },
              "nodeKinds": ["entry", "reward"],
              "edgeRules": [{ "from": "entry", "to": "reward" }],
              "requiredSockets": ["west_low_walk"],
              "anchors": []
            }
            """);

        List<SectionTemplateValidationIssue> issues = SectionTemplateValidator.validate(
            Path.of("forest_key_trial_d.json"), root);

        assertThat(issues).anySatisfy(issue -> {
            assertThat(issue.kind()).isEqualTo("empty_required_array");
            assertThat(issue.field()).isEqualTo("anchors");
        });
    }

    @Test
    void hubHomeCanOmitNavigationFields() throws Exception {
        JsonNode root = json("""
            {
              "id": "lantern_heights_hub",
              "biome": "lantern",
              "kind": "hub_home",
              "anchors": [{ "id": "samson_spawn", "kind": "npc" }]
            }
            """);

        List<SectionTemplateValidationIssue> issues = SectionTemplateValidator.validate(
            Path.of("lantern_heights_hub.json"), root);

        assertThat(issues).isEmpty();
    }

    private static JsonNode json(String raw) throws Exception {
        return MAPPER.readTree(raw);
    }
}
