package com.indieniinja.network;

/**
 * Wire protocol message type strings.
 *
 * Must stay byte-for-byte identical to Python's network/protocol.py MessageType class.
 * PROTOCOL_VERSION = "2" (msgpack, length-prefixed 4-byte big-endian uint32 frames).
 */
public final class MessageType {
    private MessageType() {}

    // Client → Server
    public static final String CLIENT_HELLO   = "client_hello";
    public static final String INPUT          = "input";
    public static final String ENTITY_EVENT   = "entity_event";
    public static final String PORTAL_TRAVEL  = "portal_travel";
    public static final String TRADE_REQUEST  = "trade_request";   // buy/sell from NPC shop
    public static final String CRAFT_REQUEST = "craft_request";   // craft item from materials
    public static final String USE_ITEM      = "use_item";         // use consumable from inventory
    public static final String EQUIP_ITEM    = "equip_item";       // equip weapon or armor

    // Server → Client
    public static final String SERVER_HELLO     = "server_hello";
    public static final String SERVER_STATE     = "server_state";
    public static final String WORLD_STATE      = "world_state";
    public static final String PLAYER_JOIN      = "player_join";
    public static final String PLAYER_LEAVE     = "player_leave";
    public static final String LOBBY_UPDATE     = "lobby_update";
    public static final String GAME_START       = "game_start";
    public static final String ERROR            = "error";
    public static final String WORLD_TRANSITION = "world_transition";
    public static final String ZONE_PRESENCE    = "zone_presence";

    // Shadow Ascent M5 — narrative boss events
    /** Server → Client: Siren's scripted loss sequence is complete.
     *  Payload: { "player_id": int } — client plays collapse animation;
     *  server has already zeroed Yin/Yang and transitioned hub to EMPTY. */
    public static final String SCRIPTED_LOSS   = "scripted_loss";

    public static final String PROTOCOL_VERSION = "2";
}
