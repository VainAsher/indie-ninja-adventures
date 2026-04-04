package com.indieniinja.client.network;

import com.indieniinja.client.GameStateBuffer;
import com.indieniinja.network.InputCommand;
import com.indieniinja.network.MessageType;
import com.indieniinja.network.WireCodec;
import com.indieniinja.network.WireMessage;
import com.indieniinja.network.WorldSnapshot;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.net.Socket;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Background thread that maintains a persistent TCP connection to the Java server.
 *
 * Protocol: 4-byte big-endian length-prefix + msgpack body (same as server side).
 * Uses plain Java Socket (not Netty) — a single client connection doesn't need
 * the full pipeline overhead.
 *
 * Thread model:
 *   - This thread: receive loop (blocks on DataInputStream.readInt())
 *   - Render thread: calls sendInput() which writes to the socket under a lock
 *
 * sendInput() is designed to be lightweight (non-blocking for small writes that
 * fit in the OS socket buffer) so the render thread is not stalled.
 *
 * Reconnect policy: exponential back-off, max 30s between attempts.
 */
public final class NetworkClientThread extends Thread {

    private static final Logger log = LoggerFactory.getLogger(NetworkClientThread.class);

    private static final int    RECONNECT_BASE_MS  = 1_000;
    private static final int    RECONNECT_MAX_MS   = 30_000;

    private final String          host;
    private final int             port;
    private final String          playerId;
    private final GameStateBuffer buffer;

    /** Latest input command for the next send cycle — written by render thread. */
    private final AtomicReference<InputCommand> pendingInput = new AtomicReference<>();

    /** Output stream guarded for thread safety between render thread and this thread. */
    private volatile DataOutputStream out;
    private final Object writeLock = new Object();

    private volatile boolean running = true;

    public NetworkClientThread(String host, int port, GameStateBuffer buffer) {
        super("ninja-net-client");
        setDaemon(true);  // don't block JVM shutdown
        this.host      = host;
        this.port      = port;
        this.playerId  = UUID.randomUUID().toString();
        this.buffer    = buffer;
    }

    // ── Public API (render thread) ────────────────────────────────────────────

    /**
     * Queue an input command to be sent on the next write opportunity.
     * Non-blocking — stores the command and returns immediately.
     * Called from the libGDX render thread every frame.
     */
    public void sendInput(InputCommand cmd) {
        pendingInput.set(cmd);
        flushInput();
    }

    public void shutdown() {
        running = false;
        interrupt();
    }

    // ── Receive loop ──────────────────────────────────────────────────────────

    @Override
    public void run() {
        int backoff = RECONNECT_BASE_MS;

        while (running && !isInterrupted()) {
            try {
                log.info("[Net] Connecting to {}:{}…", host, port);
                try (Socket socket = new Socket(host, port)) {
                    socket.setTcpNoDelay(true);
                    socket.setSoTimeout(60_000);  // 60s idle timeout

                    DataInputStream  in  = new DataInputStream(socket.getInputStream());
                    DataOutputStream os  = new DataOutputStream(socket.getOutputStream());

                    synchronized (writeLock) { this.out = os; }
                    buffer.markDisconnected();

                    sendHello(os);
                    log.info("[Net] Connected — player_id={}", playerId);
                    backoff = RECONNECT_BASE_MS;  // reset on success

                    // Receive loop
                    while (running && !isInterrupted()) {
                        int len = in.readInt();
                        if (len <= 0 || len > WireCodec.MAX_MESSAGE_BYTES)
                            throw new IOException("Invalid frame length: " + len);

                        byte[] body = new byte[len];
                        in.readFully(body);

                        handleMessage(WireCodec.decodeBody(body));
                    }
                }
            } catch (IOException | InterruptedException ex) {
                synchronized (writeLock) { this.out = null; }
                buffer.markDisconnected();
                if (!running) break;
                log.warn("[Net] Disconnected: {} — reconnecting in {}ms", ex.getMessage(), backoff);
                try { Thread.sleep(backoff); } catch (InterruptedException ie) { break; }
                backoff = Math.min(backoff * 2, RECONNECT_MAX_MS);
            }
        }
        log.info("[Net] Client thread stopped.");
    }

    // ── Message handling ──────────────────────────────────────────────────────

    private void handleMessage(WireMessage msg) {
        switch (msg.type()) {
            case MessageType.WORLD_STATE -> {
                WorldSnapshot snap = WorldSnapshot.fromMap(msg.payload());
                buffer.update(snap);
            }
            case MessageType.SERVER_HELLO -> {
                String ver = msg.getString("version", "?");
                log.info("[Net] SERVER_HELLO version={}", ver);
            }
            default -> log.debug("[Net] Ignored message type: {}", msg.type());
        }
    }

    // ── Wire helpers ──────────────────────────────────────────────────────────

    private void sendHello(DataOutputStream os) throws IOException {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("player_id", playerId);
        payload.put("version",   "2.0.0");
        payload.put("protocol",  MessageType.PROTOCOL_VERSION);
        sendRaw(os, MessageType.CLIENT_HELLO, payload);
    }

    /** Drain the pending input reference and send it if non-null. */
    private void flushInput() {
        InputCommand cmd = pendingInput.getAndSet(null);
        if (cmd == null) return;
        DataOutputStream os;
        synchronized (writeLock) { os = this.out; }
        if (os == null) return;
        try {
            sendRaw(os, MessageType.INPUT, cmd.toMap());
        } catch (IOException ignored) {
            // Connection will be re-established by the receive loop
        }
    }

    private static void sendRaw(DataOutputStream os, String msgType,
                                 Map<String, Object> payload) throws IOException {
        byte[] body = WireCodec.encodeBody(msgType, payload);
        synchronized (os) {
            os.writeInt(body.length);
            os.write(body);
            os.flush();
        }
    }
}
