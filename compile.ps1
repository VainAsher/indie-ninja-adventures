$GC = "C:\Users\asher\.gradle\caches\modules-2\files-2.1"
$PROJ = "C:\Users\asher\OneDrive\Documents\GitHub\indie-ninja-adventures\java"

$jars = @(
    "$GC\com.badlogicgames.gdx\gdx\1.12.1\a2d066c09329c457045c284c42d6f37122840aa\gdx-1.12.1.jar",
    "$GC\com.badlogicgames.gdx\gdx-backend-lwjgl3\1.12.1\12a144cacb34f0392cd8354f798d99e4836a51a8\gdx-backend-lwjgl3-1.12.1.jar",
    "$GC\io.netty\netty-common\4.1.111.Final\58210befcb31adbcadd5724966a061444db91863\netty-common-4.1.111.Final.jar",
    "$GC\io.netty\netty-buffer\4.1.111.Final\b54863f578939e135d3b3aea610284ae57c188cf\netty-buffer-4.1.111.Final.jar",
    "$GC\io.netty\netty-transport\4.1.111.Final\24e97cf14ea9d80afe4c5ab69066b587fccc154a\netty-transport-4.1.111.Final.jar",
    "$GC\io.netty\netty-codec\4.1.111.Final\a6762ec00a6d268f9980741f5b755838bcd658bf\netty-codec-4.1.111.Final.jar",
    "$GC\io.netty\netty-handler\4.1.111.Final\2bc6a58ad2e9e279634b6e55022e8dcd3c175cc4\netty-handler-4.1.111.Final.jar",
    "$GC\io.netty\netty-resolver\4.1.111.Final\3493179999f211dc49714319f81da2be86523a3b\netty-resolver-4.1.111.Final.jar",
    "$GC\org.msgpack\msgpack-core\0.9.8\6ea511f551465a0c9670e1bfb403c15d3315b540\msgpack-core-0.9.8.jar",
    "$GC\com.fasterxml.jackson.core\jackson-databind\2.17.1\524dcbcccdde7d45a679dfc333e4763feb09079\jackson-databind-2.17.1.jar",
    "$GC\com.fasterxml.jackson.core\jackson-core\2.17.1\5e52a11644cd59a28ef79f02bddc2cc3bab45edb\jackson-core-2.17.1.jar",
    "$GC\com.fasterxml.jackson.core\jackson-annotations\2.17.1\fca7ef6192c9ad05d07bc50da991bf937a84af3a\jackson-annotations-2.17.1.jar",
    "$GC\org.slf4j\slf4j-api\2.0.13\80229737f704b121a318bba5d5deacbcf395bc77\slf4j-api-2.0.13.jar",
    "$GC\ch.qos.logback\logback-classic\1.5.6\afc75d260d838a3bddfb8f207c2805ed7d1b34f9\logback-classic-1.5.6.jar",
    "$GC\ch.qos.logback\logback-core\1.5.6\41cbe874701200c5624c19e0ab50d1b88dfcc77d\logback-core-1.5.6.jar",
    "$GC\org.lwjgl\lwjgl\3.3.3\29589b5f87ed335a6c7e7ee6a5775f81f97ecb84\lwjgl-3.3.3.jar"
)

$coreOut   = "$PROJ\core\bin\main"
$serverOut = "$PROJ\server\bin\main"
$clientOut = "$PROJ\client\bin\main"

Write-Host "=== Compiling core ==="
$coreSrcs = Get-ChildItem "$PROJ\core\src\main\java" -Recurse -Filter "*.java" | Select-Object -ExpandProperty FullName
$coreCP = ($jars -join ";")
& javac -cp $coreCP -d $coreOut @coreSrcs
Write-Host "Core exit: $LASTEXITCODE"

Write-Host "=== Compiling server ==="
$serverSrcs = Get-ChildItem "$PROJ\server\src\main\java" -Recurse -Filter "*.java" | Select-Object -ExpandProperty FullName
$serverCP = ($jars + $coreOut) -join ";"
& javac -cp $serverCP -d $serverOut @serverSrcs
Write-Host "Server exit: $LASTEXITCODE"

Write-Host "=== Compiling client ==="
$clientSrcs = Get-ChildItem "$PROJ\client\src\main\java" -Recurse -Filter "*.java" | Select-Object -ExpandProperty FullName
$clientCP = ($jars + $coreOut + $serverOut) -join ";"
& javac -cp $clientCP -d $clientOut @clientSrcs
Write-Host "Client exit: $LASTEXITCODE"
