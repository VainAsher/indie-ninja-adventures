// :client — libGDX desktop client (Phase C)
plugins {
    id("java")
    id("com.github.johnrengelman.shadow") version "8.1.1"
    application
}

val gdxVersion = "1.12.1"

dependencies {
    implementation(project(":shadowascent"))

    // libGDX — desktop backend
    implementation("com.badlogicgames.gdx:gdx:$gdxVersion")
    implementation("com.badlogicgames.gdx:gdx-backend-lwjgl3:$gdxVersion")
    runtimeOnly("com.badlogicgames.gdx:gdx-platform:$gdxVersion:natives-desktop")

    // Logging
    implementation("org.slf4j:slf4j-api:2.0.13")
    runtimeOnly("ch.qos.logback:logback-classic:1.5.6")

    // Testing
    testImplementation("org.junit.jupiter:junit-jupiter:5.10.2")
}

configurations {
    // Keep JVM unit tests independent from desktop runtime-native artifacts. Tests under
    // src/test exercise save/mission/story logic and do not initialize the LWJGL backend.
    // This avoids intermittent OneDrive/AV file-lock contention on native jars.
    testCompileClasspath {
        exclude(group = "com.badlogicgames.gdx", module = "gdx-jnigen-loader")
        exclude(group = "com.badlogicgames.gdx", module = "gdx-backend-lwjgl3")
        exclude(group = "org.lwjgl")
    }
    testRuntimeClasspath {
        exclude(group = "com.badlogicgames.gdx", module = "gdx-jnigen-loader")
        exclude(group = "com.badlogicgames.gdx", module = "gdx-backend-lwjgl3")
        exclude(group = "org.lwjgl")
    }
}

application {
    mainClass.set("com.indieniinja.client.DesktopLauncher")
}

val repoRoot = projectDir.parentFile.parentFile  // java/client/ -> java/ -> repo root

// Fat JAR: stable name ninja-client-all.jar (no version suffix — launcher uses fixed filename)
//
// Assets are bundled via shadowJar's from() instead of sourceSets.main.resources.include()
// because a global include() filter on the SourceDirectorySet would strip src/main/resources/
// files (e.g. logback.xml) from the JAR — a subtle Gradle gotcha.
tasks.shadowJar {
    archiveBaseName.set("ninja-client")
    archiveVersion.set("")
    archiveClassifier.set("all")
    mergeServiceFiles()

    // Bundle game assets and data from repo root so the fat JAR works standalone.
    // Gdx.files.internal("assets/...") and Gdx.files.internal("data/...") both
    // resolve from the classpath root when running from a fat JAR.
    from(repoRoot) {
        include("assets/**")
        include("data/**")
    }
}

// 'build' also produces the shadow jar
tasks.build {
    dependsOn(tasks.shadowJar)
}

// Copy the fat JAR to the repo root so the launcher always picks up the latest local build.
// Running ':client:shadowJar' or ':client:build' automatically refreshes the launcher JAR.
// doNotTrackState: repo root may contain OneDrive-locked files that break MD5 state tracking.
tasks.register<Copy>("copyJarToRoot") {
    doNotTrackState("repo root may have OneDrive-locked files that break incremental MD5 hashing")
    from(tasks.shadowJar)
    into(repoRoot)
    dependsOn(tasks.shadowJar)
}
tasks.shadowJar {
    finalizedBy("copyJarToRoot")
}
