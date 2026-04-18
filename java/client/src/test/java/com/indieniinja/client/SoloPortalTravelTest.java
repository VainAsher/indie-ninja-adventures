package com.indieniinja.client;

import com.indieniinja.sim.GameSimulator;
import com.indieniinja.sim.LevelLayout;
import com.indieniinja.sim.SimPlayer;
import com.indieniinja.world.HubRegistry;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.lang.reflect.Method;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Verifies handleSoloPortalTravel() applies the same ability-gate and player-state
 * preservation logic as the server's handlePortalTravel().
 */
class SoloPortalTravelTest {

    // ── helpers ──────────────────────────────────────────────────────────────

    private static GameScreen makeScreen() throws Exception {
        return new GameScreen(null, "localhost", 7777, "solo");
    }

    private static void injectSim(GameScreen screen, String hubId) throws Exception {
        GameSimulator sim = new GameSimulator(42L, hubId, LevelLayout.buildTestLayout(42L));
        SimPlayer p = new SimPlayer("solo_player", 0, 96f, 128f);
        sim.addPlayer(p);
        setField(screen, "localSim", sim);
        setField(screen, "soloSeed", 42L);
        setField(screen, "soloCurrentHubId", hubId);
    }

    private static SimPlayer player(GameScreen screen) throws Exception {
        GameSimulator sim = (GameSimulator) getField(screen, "localSim");
        return sim.getPlayer(0);
    }

    private static String hubId(GameScreen screen) throws Exception {
        return (String) getField(screen, "soloCurrentHubId");
    }

    private static void travel(GameScreen screen, String destId) throws Exception {
        Method m = GameScreen.class.getDeclaredMethod("handleSoloPortalTravel", String.class);
        m.setAccessible(true);
        m.invoke(screen, destId);
    }

    private static void setField(Object target, String name, Object value) throws Exception {
        Field f = target.getClass().getDeclaredField(name);
        f.setAccessible(true);
        f.set(target, value);
    }

    private static Object getField(Object target, String name) throws Exception {
        Field f = target.getClass().getDeclaredField(name);
        f.setAccessible(true);
        return f.get(target);
    }

    // ── tests ─────────────────────────────────────────────────────────────────

    @Test
    void abilityGateDeniesEntryWhenRequiredAbilityMissing() throws Exception {
        // town_hub requires "double_jump" — player starts with no abilities.
        GameScreen screen = makeScreen();
        injectSim(screen, "central_hub");
        SimPlayer sp = player(screen);
        assertTrue(sp.unlockedAbilities.isEmpty(), "precondition: no abilities");

        String before = hubId(screen);
        travel(screen, "town_hub");

        // Hub must not change — player stays in central_hub.
        assertEquals(before, hubId(screen), "hub must remain unchanged after denial");
        assertSame(sp, player(screen), "SimPlayer instance must not change after denial");
    }

    @Test
    void abilityGateAllowsEntryToOpenHub() throws Exception {
        // forest_hub has no required ability — always accessible.
        GameScreen screen = makeScreen();
        injectSim(screen, "central_hub");

        travel(screen, "forest_hub");

        assertEquals("forest_hub", hubId(screen));
        // A new SimPlayer is created by initializeSoloSimulation.
        assertNotNull(player(screen));
    }

    @Test
    void playerStatePreservedAcrossZoneTransition() throws Exception {
        // cave_hub requires "dash" — give the player that ability.
        GameScreen screen = makeScreen();
        injectSim(screen, "central_hub");
        SimPlayer sp = player(screen);
        sp.unlockedAbilities.add("dash");
        sp.health    = 3;
        sp.maxHealth = 5;
        sp.level     = 4;
        sp.experience = 200;
        sp.inventory.currency = 77;
        sp.inventory.addItem("health_potion", 2);

        travel(screen, "cave_hub");

        assertEquals("cave_hub", hubId(screen));
        SimPlayer newSp = player(screen);
        assertNotNull(newSp);

        assertEquals(3,   newSp.health,       "health preserved");
        assertEquals(5,   newSp.maxHealth,    "maxHealth preserved");
        assertEquals(4,   newSp.level,        "level preserved");
        assertEquals(200, newSp.experience,   "experience preserved");
        assertEquals(77,  newSp.inventory.currency, "currency preserved");
        assertTrue(newSp.unlockedAbilities.contains("dash"), "abilities preserved");
        assertEquals(2,   newSp.inventory.countItem("health_potion"), "inventory preserved");
    }

    @Test
    void hubSeedDiffersPerDestination() throws Exception {
        // Verify that different hubs get different seeds from the same session seed —
        // basic sanity on HubRegistry.hubSeed() not returning a constant.
        long sessionSeed = 42L;
        long forestSeed = HubRegistry.hubSeed(sessionSeed, "forest_hub");
        long caveSeed   = HubRegistry.hubSeed(sessionSeed, "cave_hub");
        assertNotEquals(forestSeed, caveSeed, "hub seeds must differ per destination");
        assertNotEquals(sessionSeed, forestSeed, "hub seed must differ from session seed (unless offset=0)");
    }
}
