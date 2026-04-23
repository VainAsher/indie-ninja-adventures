package com.indieniinja.server;

import org.junit.jupiter.api.Test;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;

import static org.assertj.core.api.Assertions.assertThat;

class GameSessionSlotReservationTest {

    @Test
    void reconnectGraceReservesSlotForSamePlayer() {
        MutableClock clock = new MutableClock(0L);
        GameSession session = new GameSession(123L, clock);

        assertThat(session.claimSlot("player_a")).isEqualTo(0);
        assertThat(session.claimSlot("player_b")).isEqualTo(1);

        session.releaseSlot("player_a", 0);

        // Reserved slot 0 must not be stolen during the reconnect grace window.
        assertThat(session.claimSlot("player_c")).isEqualTo(2);
        assertThat(session.claimSlot("player_a")).isEqualTo(0);
    }

    @Test
    void expiredReservationReturnsSlotToFreePool() {
        MutableClock clock = new MutableClock(0L);
        GameSession session = new GameSession(456L, clock);

        assertThat(session.claimSlot("player_a")).isEqualTo(0);
        session.releaseSlot("player_a", 0);

        assertThat(session.claimSlot("player_b")).isEqualTo(1);
        assertThat(session.claimSlot("player_c")).isEqualTo(2);
        assertThat(session.claimSlot("player_d")).isEqualTo(3);
        assertThat(session.claimSlot("player_e")).isEqualTo(-1);

        clock.advanceMs(GameSession.RECONNECT_GRACE_SECONDS * 1000L + 1L);

        assertThat(session.claimSlot("player_e")).isEqualTo(0);
    }

    @Test
    void reconnectAfterGraceUsesCurrentFreeSlotInsteadOfExpiredReservation() {
        MutableClock clock = new MutableClock(0L);
        GameSession session = new GameSession(789L, clock);

        assertThat(session.claimSlot("player_a")).isEqualTo(0);
        session.releaseSlot("player_a", 0);

        clock.advanceMs(GameSession.RECONNECT_GRACE_SECONDS * 1000L + 1L);

        assertThat(session.claimSlot("player_b")).isEqualTo(0);
        assertThat(session.claimSlot("player_a")).isEqualTo(1);
    }

    private static final class MutableClock extends Clock {
        private long nowMs;

        MutableClock(long initialMs) {
            this.nowMs = initialMs;
        }

        void advanceMs(long deltaMs) {
            nowMs += deltaMs;
        }

        @Override
        public ZoneId getZone() {
            return ZoneId.of("UTC");
        }

        @Override
        public Clock withZone(ZoneId zone) {
            return this;
        }

        @Override
        public Instant instant() {
            return Instant.ofEpochMilli(nowMs);
        }

        @Override
        public long millis() {
            return nowMs;
        }
    }
}
