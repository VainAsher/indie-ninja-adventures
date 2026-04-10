package com.indieniinja.server;

import com.indieniinja.sim.ItemDatabase;
import com.indieniinja.sim.RecipeBook;
import com.zaxxer.hikari.HikariDataSource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Server-startup helper that loads {@link ItemDatabase} and {@link RecipeBook}
 * from PostgreSQL, falling back to hardcoded defaults when the tables are empty.
 *
 * Call sequence (from NinjaGameServer / integration point):
 * <pre>
 *   InventoryDatabaseLoader loader = new InventoryDatabaseLoader(ds, itemCache);
 *   loader.initOrSeed();   // ensures schema + populates tables on first run
 * </pre>
 *
 * On first run (empty item_defs / recipe_defs tables):
 *   1. ensureSchema() creates the three tables.
 *   2. seedItemDefs() + seedRecipeDefs() write the hardcoded defaults to DB.
 *   3. ItemCache is primed with the current item list.
 *
 * On subsequent runs:
 *   1. loadItemDefs() + loadRecipeDefs() replace the in-memory registries.
 *   2. ItemCache is primed from the freshly loaded data.
 */
public final class InventoryDatabaseLoader {

    private static final Logger log = LoggerFactory.getLogger(InventoryDatabaseLoader.class);

    private final InventoryRepository repo;
    private final ItemCache           itemCache;

    public InventoryDatabaseLoader(HikariDataSource ds, ItemCache itemCache) {
        this.repo      = new InventoryRepository(ds);
        this.itemCache = itemCache;
    }

    /** Also accessible for injection (e.g. tests that pre-build the repo). */
    public InventoryDatabaseLoader(InventoryRepository repo, ItemCache itemCache) {
        this.repo      = repo;
        this.itemCache = itemCache;
    }

    /**
     * Ensure schema exists, then load or seed item/recipe data.
     * Safe to call at every server start.
     */
    public void initOrSeed() {
        repo.ensureSchema();

        int items   = repo.loadItemDefs();
        int recipes = repo.loadRecipeDefs();

        if (items == 0) {
            log.info("item_defs table is empty — seeding from hardcoded defaults");
            repo.seedItemDefs();
        }
        if (recipes == 0) {
            log.info("recipe_defs table is empty — seeding from hardcoded defaults");
            repo.seedRecipeDefs();
        }

        // Prime Redis cache with whatever is now in ItemDatabase
        if (itemCache != null) {
            itemCache.putAll(ItemDatabase.allDefs());
            log.info("ItemCache primed with {} items", ItemDatabase.allDefs().size());
        }
    }

    /** Expose the repository for inventory save/load calls elsewhere. */
    public InventoryRepository repository() {
        return repo;
    }
}
