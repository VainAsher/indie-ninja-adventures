package com.indieniinja.content;

public class ContentLoadException extends Exception {
    public ContentLoadException(String message) { super(message); }
    public ContentLoadException(String message, Throwable cause) { super(message, cause); }
}
