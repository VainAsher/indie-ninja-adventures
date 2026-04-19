package com.indieniinja.server;

import com.indieniinja.content.ContentLoadException;
import com.indieniinja.content.ContentLoader;
import com.indieniinja.content.ContentRegistry;
import com.indieniinja.network.WireCodec;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.JedisPoolConfig;
import io.netty.bootstrap.ServerBootstrap;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import io.netty.channel.Channel;
import io.netty.channel.ChannelFuture;
import io.netty.channel.ChannelHandler;
import io.netty.channel.ChannelHandlerContext;
import io.netty.channel.ChannelInitializer;
import io.netty.channel.ChannelOption;
import io.netty.channel.EventLoopGroup;
import io.netty.channel.nio.NioEventLoopGroup;
import io.netty.channel.socket.SocketChannel;
import io.netty.channel.socket.nio.NioServerSocketChannel;
import io.netty.handler.codec.ByteToMessageDecoder;
import io.netty.handler.codec.MessageToByteEncoder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;

/**
 * Netty authoritative game server — entry point.
 *
 * Java equivalent of Python's network/server.py run_server() / GameServer.
 *
 * Wire format: [4-byte big-endian uint32 length][msgpack body]
 * Decoded by LengthFieldDecoder → MsgpackBodyDecoder → ServerProtocolHandler.
 *
 * Usage:
 *   java -jar ninja-server-all.jar [port] [seed]
 *
 * Or from launcher: replaces "python demo_game.py --host <port>"
 *
 * Protocol parity:
 *   - TCP_NODELAY enabled (matches Python setsockopt TCP_NODELAY)
 *   - PROTOCOL_VERSION = "2" (msgpack)
 *   - Same MessageType string constants as Python network/protocol.py
 */
public final class NinjaGameServer {

    private static final Logger log = LoggerFactory.getLogger(NinjaGameServer.class);

    public static final int DEFAULT_PORT = 7777;
    public static final long DEFAULT_SEED = 42L;

    public static void main(String[] args) throws Exception {
        int  port = args.length > 0 ? Integer.parseInt(args[0]) : DEFAULT_PORT;
        long seed = args.length > 1 ? Long.parseLong(args[1])   : DEFAULT_SEED;

        log.info("Indie Ninja Adventures — Java Server v0.10.0");
        log.info("Listening on port {} | world seed {}", port, seed);

        run(port, seed);
    }

    public static void run(int port, long seed) throws Exception {
        // Load all content definitions from data/ directory at startup.
        // Server does not start if any definition file fails schema validation.
        ContentRegistry contentRegistry = loadContent();

        GameSession session = new GameSession(seed);
        session.contentRegistry = contentRegistry;

        // Optional Redis — enable with -Dredis.host=<host> (default port 6379)
        String redisHost = System.getProperty("redis.host");
        if (redisHost != null && !redisHost.isBlank()) {
            int redisPort = Integer.getInteger("redis.port", 6379);
            JedisPoolConfig cfg = new JedisPoolConfig();
            cfg.setMaxTotal(8);
            cfg.setMaxIdle(4);
            JedisPool pool = new JedisPool(cfg, redisHost, redisPort);
            session.zoneStateCache = new ZoneStateCache(pool);
            log.info("Redis zone-state cache enabled — {}:{}", redisHost, redisPort);
        }

        ServerProtocolHandler  handler = new ServerProtocolHandler(session);

        EventLoopGroup bossGroup   = new NioEventLoopGroup(1);
        EventLoopGroup workerGroup = new NioEventLoopGroup();   // # = 2 × CPU cores

        try {
            ServerBootstrap b = new ServerBootstrap()
                .group(bossGroup, workerGroup)
                .channel(NioServerSocketChannel.class)
                // Allow immediate port reuse after server stop — avoids TIME_WAIT
                // blocking restart within ~60s on Windows/Linux.
                .option(ChannelOption.SO_REUSEADDR, true)
                // Disable Nagle's algorithm — send small packets immediately
                // Matches Python: _sock.setsockopt(TCP, TCP_NODELAY, 1)
                .childOption(ChannelOption.TCP_NODELAY, true)
                .childOption(ChannelOption.SO_KEEPALIVE, true)
                .childHandler(new ChannelInitializer<SocketChannel>() {
                    @Override
                    protected void initChannel(SocketChannel ch) {
                        ch.pipeline()
                            // Inbound: decode 4-byte-prefixed frames → strip header
                            .addLast("frameDecoder", new LengthFieldDecoder())
                            // Outbound: prepend 4-byte length before sending
                            .addLast("frameEncoder", new LengthFieldEncoder())
                            // Business logic
                            .addLast("handler", handler);
                    }
                });

            ChannelFuture f = b.bind(port).sync();
            log.info("Server ready — waiting for connections");
            f.channel().closeFuture().sync();
        } finally {
            bossGroup.shutdownGracefully();
            workerGroup.shutdownGracefully();
        }
    }

    // ── Frame decoder: reads [4-byte length][body], emits body as ByteBuf ─────

    static final class LengthFieldDecoder extends ByteToMessageDecoder {
        @Override
        protected void decode(ChannelHandlerContext ctx, ByteBuf in, List<Object> out) {
            if (in.readableBytes() < WireCodec.HEADER_SIZE) return;
            in.markReaderIndex();
            int length = in.readInt();   // big-endian uint32
            if (length > WireCodec.MAX_MESSAGE_BYTES) {
                log.warn("Incoming message too large ({} bytes) — closing channel", length);
                ctx.close();
                return;
            }
            if (in.readableBytes() < length) {
                in.resetReaderIndex();
                return;  // wait for more data
            }
            out.add(in.readRetainedSlice(length));
        }
    }

    // ── Frame encoder: prepends 4-byte big-endian length to outgoing ByteBuf ──

    static final class LengthFieldEncoder extends MessageToByteEncoder<ByteBuf> {
        @Override
        protected void encode(ChannelHandlerContext ctx, ByteBuf msg, ByteBuf out) {
            out.writeInt(msg.readableBytes());  // big-endian uint32
            out.writeBytes(msg);
        }
    }

    private static ContentRegistry loadContent() throws Exception {
        java.nio.file.Path dataRoot = java.nio.file.Paths.get("data");
        if (!java.nio.file.Files.isDirectory(dataRoot)) {
            log.warn("[Content] data/ directory not found at {}; starting with empty registry", dataRoot.toAbsolutePath());
            return new ContentRegistry();
        }
        try {
            ContentRegistry registry = new ContentLoader(dataRoot).loadAll();
            log.info("[Content] Registry ready ({} enemies, {} npcs, {} roomTypes)",
                registry.enemyCount(), registry.npcCount(), registry.roomTypeCount());
            return registry;
        } catch (ContentLoadException e) {
            log.error("[Content] Failed to load content definitions — server cannot start: {}", e.getMessage());
            throw e;
        }
    }
}
