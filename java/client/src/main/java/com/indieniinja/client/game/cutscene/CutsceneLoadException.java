package com.indieniinja.client.game.cutscene;

/** Thrown when a cutscene definition file fails validation at load time. */
public final class CutsceneLoadException extends RuntimeException {
    public CutsceneLoadException(String message) {
        super(message);
    }
    public CutsceneLoadException(String message, Throwable cause) {
        super(message, cause);
    }
}
