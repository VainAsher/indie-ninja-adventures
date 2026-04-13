package com.indieniinja.server;

import com.indieniinja.network.InputCommand;
import com.indieniinja.sim.EchoRecorder;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class EchoRecorderTest {

    @Test
    void snapshotKeepsChronologicalOrder() {
        EchoRecorder r = new EchoRecorder();
        for (int i = 0; i < 5; i++) {
            InputCommand c = new InputCommand(i);
            c.right = (i % 2 == 0);
            r.record(c);
        }

        List<InputCommand> s = r.snapshot();
        assertThat(s).hasSize(5);
        assertThat(s.get(0).frame).isEqualTo(0);
        assertThat(s.get(4).frame).isEqualTo(4);
        assertThat(s.get(0).right).isTrue();
        assertThat(s.get(1).right).isFalse();
    }

    @Test
    void ringBufferDropsOldestBeyond600Ticks() {
        EchoRecorder r = new EchoRecorder();
        for (int i = 0; i < EchoRecorder.BUFFER + 7; i++) {
            InputCommand c = new InputCommand(i);
            c.left = true;
            r.record(c);
        }

        List<InputCommand> s = r.snapshot();
        assertThat(s).hasSize(EchoRecorder.BUFFER);
        assertThat(s.get(0).frame).isEqualTo(7);
        assertThat(s.get(s.size() - 1).frame).isEqualTo(EchoRecorder.BUFFER + 6);
    }

    @Test
    void snapshotReturnsDefensiveCopies() {
        EchoRecorder r = new EchoRecorder();
        InputCommand c = new InputCommand(1);
        c.jump = true;
        r.record(c);

        List<InputCommand> s1 = r.snapshot();
        s1.get(0).jump = false;

        List<InputCommand> s2 = r.snapshot();
        assertThat(s2.get(0).jump).isTrue();
    }
}
