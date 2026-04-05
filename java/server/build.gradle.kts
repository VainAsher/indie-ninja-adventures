// :server — Netty authoritative game server (headless, no rendering)
plugins {
    id("java")
    id("com.github.johnrengelman.shadow") version "8.1.1"
    application
}

dependencies {
    implementation(project(":core"))

    // Netty NIO server
    implementation("io.netty:netty-all:4.1.111.Final")

    // Logging implementation for the server binary
    implementation("org.slf4j:slf4j-api:2.0.13")
    runtimeOnly("ch.qos.logback:logback-classic:1.5.6")

    // Testing
    testImplementation("org.junit.jupiter:junit-jupiter:5.10.2")
    testImplementation("org.assertj:assertj-core:3.25.3")
    testImplementation("org.mockito:mockito-core:5.11.0")
    testImplementation("org.mockito:mockito-junit-jupiter:5.11.0")
    testImplementation(project(":core"))
}

application {
    mainClass.set("com.indieniinja.server.NinjaGameServer")
}

// Fat JAR: stable name ninja-server-all.jar (no version suffix — launcher uses fixed filename)
tasks.shadowJar {
    archiveBaseName.set("ninja-server")
    archiveVersion.set("")
    archiveClassifier.set("all")
    mergeServiceFiles()
}

// Make 'build' produce the shadow jar automatically
tasks.build {
    dependsOn(tasks.shadowJar)
}
