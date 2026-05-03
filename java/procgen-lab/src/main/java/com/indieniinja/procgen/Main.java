package com.indieniinja.procgen;

import com.indieniinja.procgen.ui.ProcgenLabFrame;

import javax.swing.*;

public final class Main {
    public static void main(String[] args) {
        long seed = args.length > 0 ? Long.parseLong(args[0]) : System.currentTimeMillis();
        SwingUtilities.invokeLater(() -> new ProcgenLabFrame(seed));
    }
}
