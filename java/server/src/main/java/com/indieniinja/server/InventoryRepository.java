package com.indieniinja.server;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.indieniinja.sim.ItemDatabase;
import com.indieniinja.sim.ItemDatabase.ItemDef;
import com.indieniinja.sim.RecipeBook;
import com.indieniinja.sim.CraftingRecipe;
import com.indieniinja.sim.SimInventory;
import com.zaxxer.hikari.HikariDataSource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.sql.*;
import java.util.*;

/**
 * PostgreSQL persistence for inventory subsystem (INV-1, INV-2, INV-3).
 *
 * Tables managed here:
 * <pre>
 *   item_defs        — one row per ItemDef (loaded into ItemDatabase at startup)
 *   recipe_defs      — one row per CraftingRecipe (loaded into RecipeBook at startup)
 *   player_inventory — one row per player_id (SimInventory JSONB + currency + equipment)
 * </pre>
 *
 * Call {@link #ensureSchema()} once at server startup, then:
 *   {@link #loadItemDefs()}   → passes rows to {@link ItemDatabase#reload}
 *   {@link #loadRecipeDefs()} → passes rows to {@link RecipeBook#reload}
 *   {@link #saveInventory}    → persists player inventory on zone leave / flush
 *   {@link #loadInventory}    → restores player inventory on connect
 */
public final class InventoryRepository {

    private static final Logger log = LoggerFactory.getLogger(InventoryRepository.class);
    private static final ObjectMapper JSON = new ObjectMapper();

    private final HikariDataSource ds;

    public InventoryRepository(HikariDataSource dataSource) {
        this.ds = dataSource;
    }

    // ── Schema ────────────────────────────────────────────────────────────────

    public void ensureSchema() {
        String ddl = """
                CREATE TABLE IF NOT EXISTS item_defs (
                    id            TEXT    NOT NULL PRIMARY KEY,
                    type          TEXT    NOT NULL,
                    rarity        TEXT    NOT NULL,
                    name          TEXT    NOT NULL,
                    description   TEXT    NOT NULL DEFAULT '',
                    max_stack     INT     NOT NULL DEFAULT 1,
                    value         INT     NOT NULL DEFAULT 0,
                    consumable    BOOLEAN NOT NULL DEFAULT FALSE,
                    attack_bonus  INT     NOT NULL DEFAULT 0,
                    defense_bonus INT     NOT NULL DEFAULT 0,
                    speed_bonus   FLOAT   NOT NULL DEFAULT 0,
                    health_bonus  INT     NOT NULL DEFAULT 0,
                    health_restore INT    NOT NULL DEFAULT 0,
                    ability_id    TEXT
                );

                CREATE TABLE IF NOT EXISTS recipe_defs (
                    recipe_id     TEXT    NOT NULL PRIMARY KEY,
                    output_item   TEXT    NOT NULL,
                    output_count  INT     NOT NULL DEFAULT 1,
                    ingredients   JSONB   NOT NULL,
                    category      TEXT    NOT NULL DEFAULT '',
                    description   TEXT    NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS player_inventory (
                    player_id        TEXT    NOT NULL PRIMARY KEY,
                    currency         INT     NOT NULL DEFAULT 0,
                    equipped_weapon  TEXT,
                    equipped_armor   TEXT,
                    slots            JSONB   NOT NULL DEFAULT '[]'
                );
                """;
        try (Connection conn = ds.getConnection();
             Statement st = conn.createStatement()) {
            st.execute(ddl);
            log.info("Inventory schema ready (item_defs, recipe_defs, player_inventory)");
        } catch (SQLException e) {
            log.error("Failed to create inventory schema", e);
            throw new RuntimeException("DB schema init failed", e);
        }
    }

    // ── Item definitions ──────────────────────────────────────────────────────

    /**
     * Upsert all current {@link ItemDatabase} entries into {@code item_defs}.
     * Call once after hardcoded data is loaded so the table is populated for
     * future loadItemDefs() calls.
     */
    public void seedItemDefs() {
        String sql = """
                INSERT INTO item_defs
                    (id, type, rarity, name, description, max_stack, value, consumable,
                     attack_bonus, defense_bonus, speed_bonus, health_bonus, health_restore, ability_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT (id) DO UPDATE SET
                    type=EXCLUDED.type, rarity=EXCLUDED.rarity, name=EXCLUDED.name,
                    description=EXCLUDED.description, max_stack=EXCLUDED.max_stack,
                    value=EXCLUDED.value, consumable=EXCLUDED.consumable,
                    attack_bonus=EXCLUDED.attack_bonus, defense_bonus=EXCLUDED.defense_bonus,
                    speed_bonus=EXCLUDED.speed_bonus, health_bonus=EXCLUDED.health_bonus,
                    health_restore=EXCLUDED.health_restore, ability_id=EXCLUDED.ability_id
                """;
        try (Connection conn = ds.getConnection();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            for (ItemDef d : ItemDatabase.allDefs()) {
                ps.setString(1,  d.id());
                ps.setString(2,  d.type());
                ps.setString(3,  d.rarity());
                ps.setString(4,  d.name());
                ps.setString(5,  d.desc());
                ps.setInt(6,     d.maxStack());
                ps.setInt(7,     d.value());
                ps.setBoolean(8, d.consumable());
                ps.setInt(9,     d.attackBonus());
                ps.setInt(10,    d.defenseBonus());
                ps.setFloat(11,  d.speedBonus());
                ps.setInt(12,    d.healthBonus());
                ps.setInt(13,    d.healthRestore());
                if (d.abilityId() != null) ps.setString(14, d.abilityId());
                else ps.setNull(14, Types.VARCHAR);
                ps.addBatch();
            }
            ps.executeBatch();
            log.info("Seeded {} item_defs", ItemDatabase.allDefs().size());
        } catch (Exception e) {
            log.error("Failed to seed item_defs", e);
            throw new RuntimeException("item_defs seed failed", e);
        }
    }

    /**
     * Load all rows from {@code item_defs} and replace {@link ItemDatabase}
     * in-memory map via {@link ItemDatabase#reload}.
     *
     * @return number of items loaded
     */
    public int loadItemDefs() {
        String sql = "SELECT id,type,rarity,name,description,max_stack,value,consumable,"
                   + "attack_bonus,defense_bonus,speed_bonus,health_bonus,health_restore,ability_id"
                   + " FROM item_defs";
        List<ItemDef> defs = new ArrayList<>();
        try (Connection conn = ds.getConnection();
             PreparedStatement ps = conn.prepareStatement(sql);
             ResultSet rs = ps.executeQuery()) {
            while (rs.next()) {
                defs.add(new ItemDef(
                    rs.getString("id"),
                    rs.getString("type"),
                    rs.getString("rarity"),
                    rs.getString("name"),
                    rs.getString("description"),
                    rs.getInt("max_stack"),
                    rs.getInt("value"),
                    rs.getBoolean("consumable"),
                    rs.getInt("attack_bonus"),
                    rs.getInt("defense_bonus"),
                    rs.getFloat("speed_bonus"),
                    rs.getInt("health_bonus"),
                    rs.getInt("health_restore"),
                    rs.getString("ability_id")   // null for non-ability items
                ));
            }
        } catch (Exception e) {
            log.error("Failed to load item_defs from DB", e);
            return 0;
        }
        if (!defs.isEmpty()) {
            ItemDatabase.reload(defs);
            log.info("Loaded {} item_defs from DB into ItemDatabase", defs.size());
        }
        return defs.size();
    }

    // ── Recipe definitions ────────────────────────────────────────────────────

    /**
     * Upsert all current {@link RecipeBook} entries into {@code recipe_defs}.
     */
    public void seedRecipeDefs() {
        String sql = """
                INSERT INTO recipe_defs (recipe_id, output_item, output_count, ingredients, category, description)
                VALUES (?,?,?,?::jsonb,?,?)
                ON CONFLICT (recipe_id) DO UPDATE SET
                    output_item=EXCLUDED.output_item, output_count=EXCLUDED.output_count,
                    ingredients=EXCLUDED.ingredients, category=EXCLUDED.category,
                    description=EXCLUDED.description
                """;
        try (Connection conn = ds.getConnection();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            for (CraftingRecipe r : RecipeBook.all()) {
                ps.setString(1, r.recipeId);
                ps.setString(2, r.outputItemId);
                ps.setInt(3,    r.outputCount);
                ps.setString(4, serializeIngredients(r.ingredients));
                ps.setString(5, r.category);
                ps.setString(6, r.description);
                ps.addBatch();
            }
            ps.executeBatch();
            log.info("Seeded {} recipe_defs", RecipeBook.all().size());
        } catch (Exception e) {
            log.error("Failed to seed recipe_defs", e);
            throw new RuntimeException("recipe_defs seed failed", e);
        }
    }

    /**
     * Load all rows from {@code recipe_defs} and replace {@link RecipeBook}
     * in-memory map via {@link RecipeBook#reload}.
     *
     * @return number of recipes loaded
     */
    public int loadRecipeDefs() {
        String sql = "SELECT recipe_id,output_item,output_count,ingredients,category,description"
                   + " FROM recipe_defs";
        List<CraftingRecipe> recipes = new ArrayList<>();
        try (Connection conn = ds.getConnection();
             PreparedStatement ps = conn.prepareStatement(sql);
             ResultSet rs = ps.executeQuery()) {
            while (rs.next()) {
                List<CraftingRecipe.Ingredient> ings =
                        deserializeIngredients(rs.getString("ingredients"));
                recipes.add(new CraftingRecipe(
                    rs.getString("recipe_id"),
                    rs.getString("output_item"),
                    rs.getInt("output_count"),
                    ings,
                    rs.getString("category"),
                    rs.getString("description")
                ));
            }
        } catch (Exception e) {
            log.error("Failed to load recipe_defs from DB", e);
            return 0;
        }
        if (!recipes.isEmpty()) {
            RecipeBook.reload(recipes);
            log.info("Loaded {} recipe_defs from DB into RecipeBook", recipes.size());
        }
        return recipes.size();
    }

    // ── Player inventory persistence ──────────────────────────────────────────

    /**
     * Persist a player's inventory (upsert).
     * Call on zone leave or periodic flush.
     */
    public void saveInventory(String playerId, SimInventory inv) {
        String sql = """
                INSERT INTO player_inventory (player_id, currency, equipped_weapon, equipped_armor, slots)
                VALUES (?,?,?,?,?::jsonb)
                ON CONFLICT (player_id) DO UPDATE SET
                    currency=EXCLUDED.currency,
                    equipped_weapon=EXCLUDED.equipped_weapon,
                    equipped_armor=EXCLUDED.equipped_armor,
                    slots=EXCLUDED.slots
                """;
        try (Connection conn = ds.getConnection();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setString(1, playerId);
            ps.setInt(2,    inv.currency);
            if (inv.equippedWeapon != null) ps.setString(3, inv.equippedWeapon);
            else ps.setNull(3, Types.VARCHAR);
            if (inv.equippedArmor != null) ps.setString(4, inv.equippedArmor);
            else ps.setNull(4, Types.VARCHAR);
            ps.setString(5, serializeSlots(inv));
            ps.executeUpdate();
            log.debug("Saved inventory for player {}", playerId);
        } catch (Exception e) {
            log.error("Failed to save inventory for player {}", playerId, e);
            throw new RuntimeException("inventory save failed for " + playerId, e);
        }
    }

    /**
     * Load a player's inventory from DB.
     *
     * @return populated {@link SimInventory}, or a fresh empty one if not found
     */
    public SimInventory loadInventory(String playerId) {
        String sql = "SELECT currency, equipped_weapon, equipped_armor, slots"
                   + " FROM player_inventory WHERE player_id = ?";
        try (Connection conn = ds.getConnection();
             PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setString(1, playerId);
            try (ResultSet rs = ps.executeQuery()) {
                if (!rs.next()) return new SimInventory();
                Map<String, Object> m = new LinkedHashMap<>();
                m.put("currency",        rs.getInt("currency"));
                m.put("equipped_weapon", rs.getString("equipped_weapon"));
                m.put("equipped_armor",  rs.getString("equipped_armor"));
                m.put("slots",           deserializeSlots(rs.getString("slots")));
                return SimInventory.fromMap(m);
            }
        } catch (Exception e) {
            log.error("Failed to load inventory for player {}", playerId, e);
            return new SimInventory();
        }
    }

    // ── Serialization helpers ─────────────────────────────────────────────────

    private static String serializeSlots(SimInventory inv) throws Exception {
        List<Object> list = new ArrayList<>(SimInventory.MAX_SLOTS);
        for (SimInventory.Slot s : inv.slots) {
            list.add(s != null ? s.toMap() : null);
        }
        return JSON.writeValueAsString(list);
    }

    @SuppressWarnings("unchecked")
    private static List<Object> deserializeSlots(String json) throws Exception {
        if (json == null || json.isBlank()) return new ArrayList<>();
        return JSON.readValue(json, new TypeReference<List<Object>>() {});
    }

    private static String serializeIngredients(List<CraftingRecipe.Ingredient> ings) throws Exception {
        List<Map<String, Object>> list = new ArrayList<>(ings.size());
        for (CraftingRecipe.Ingredient i : ings) {
            list.add(Map.of("itemId", i.itemId(), "count", i.count()));
        }
        return JSON.writeValueAsString(list);
    }

    @SuppressWarnings("unchecked")
    private static List<CraftingRecipe.Ingredient> deserializeIngredients(String json) throws Exception {
        List<Map<String, Object>> list = JSON.readValue(json, new TypeReference<>() {});
        List<CraftingRecipe.Ingredient> result = new ArrayList<>(list.size());
        for (Map<String, Object> m : list) {
            result.add(new CraftingRecipe.Ingredient(
                (String) m.get("itemId"),
                ((Number) m.get("count")).intValue()
            ));
        }
        return result;
    }
}
