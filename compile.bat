@echo off
set GC=C:\Users\asher\.gradle\caches\modules-2\files-2.1
set CP=java\core\bin\main
set CP=%CP%;%GC%\com.badlogicgames.gdx\gdx\1.12.1\a2d066c09329c457045c284c42d6f37122840aa\gdx-1.12.1.jar
set CP=%CP%;%GC%\io.netty\netty-all\4.1.111.Final\8fba10bb4911517eb1bdcc05ef392499dda4d5ac\netty-all-4.1.111.Final.jar
set CP=%CP%;%GC%\org.msgpack\msgpack-core\0.9.8\6ea511f551465a0c9670e1bfb403c15d3315b540\msgpack-core-0.9.8.jar
set CP=%CP%;%GC%\com.fasterxml.jackson.core\jackson-databind\2.17.1\524dcbcccdde7d45a679dfc333e4763feb09079\jackson-databind-2.17.1.jar
set CP=%CP%;%GC%\com.fasterxml.jackson.core\jackson-core\2.17.1\5e52a11644cd59a28ef79f02bddc2cc3bab45edb\jackson-core-2.17.1.jar
set CP=%CP%;%GC%\com.fasterxml.jackson.core\jackson-annotations\2.17.1\fca7ef6192c9ad05d07bc50da991bf937a84af3a\jackson-annotations-2.17.1.jar
set CP=%CP%;%GC%\org.slf4j\slf4j-api\2.0.13\80229737f704b121a318bba5d5deacbcf395bc77\slf4j-api-2.0.13.jar
set CP=%CP%;%GC%\ch.qos.logback\logback-classic\1.5.6\afc75d260d838a3bddfb8f207c2805ed7d1b34f9\logback-classic-1.5.6.jar
set CP=%CP%;%GC%\ch.qos.logback\logback-core\1.5.6\41cbe874701200c5624c19e0ab50d1b88dfcc77d\logback-core-1.5.6.jar
set CP=%CP%;%GC%\org.lwjgl\lwjgl\3.3.3\29589b5f87ed335a6c7e7ee6a5775f81f97ecb84\lwjgl-3.3.3.jar
set CP=%CP%;%GC%\com.badlogicgames.gdx\gdx-backend-lwjgl3\1.12.1\12a144cacb34f0392cd8354f798d99e4836a51a8\gdx-backend-lwjgl3-1.12.1.jar

echo === Compiling server ===
javac -cp "%CP%" -d java\server\bin\main java\server\src\main\java\com\indieniinja\server\*.java
echo Server exit: %ERRORLEVEL%

echo === Compiling client ===
javac -cp "%CP%;java\server\bin\main" -d java\client\bin\main java\client\src\main\java\com\indieniinja\client\*.java java\client\src\main\java\com\indieniinja\client\rendering\*.java java\client\src\main\java\com\indieniinja\client\ui\*.java
echo Client exit: %ERRORLEVEL%
