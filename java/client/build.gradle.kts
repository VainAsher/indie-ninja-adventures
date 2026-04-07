// :client — libGDX desktop client (Phase C)
plugins {
    id("java")
    id("com.github.johnrengelman.shadow") version "8.1.1"
    application
}

val gdxVersion = "1.12.1"

dependencies {
    implementation(project(":core"))

    // libGDX — desktop backend
    implementation("com.badlogicgames.gdx:gdx:$gdxVersion")
    implementation("com.badlogicgames.gdx:gdx-backend-lwjgl3:$gdxVersion")
    implementation("com.badlogicgames.gdx:gdx-platform:$gdxVersion:natives-desktop")

    // Logging
    implementation("org.slf4j:slf4j-api:2.0.13")
    runtimeOnly("ch.qos.logback:logback-classic:1.5.6")

    // Testing
    testImplementation("org.junit.jupiter:junit-jupiter:5.10.2")
    testImplementation("org.assertj:assertj-core:3.25.3")
}

application {
    mainClass.set("com.indieniinja.client.DesktopLauncher")
}

// Bundle game assets into the JAR so it works standalone when downloaded.
// Assets live in the repo root assets/ directory; Gdx.files.internal("assets/...")
// resolves from the classpath root, so we include them with their "assets/" prefix intact.
val repoRoot = projectDir.parentFile.parentFile  // java/client/ -> java/ -> repo root
sourceSets.main {
    resources {
        srcDir(repoRoot)
        include("assets/**")
    }
}

// Fat JAR: stable name ninja-client-all.jar (no version suffix — launcher uses fixed filename)
tasks.shadowJar {
    archiveBaseName.set("ninja-client")
    archiveVersion.set("")
    archiveClassifier.set("all")
    mergeServiceFiles()

    // libGDX LWJGL3 natives must be excluded from shadow and extracted at runtime
    // via LWJGL's built-in loader — no special handling needed here.
}

// 'build' also produces the shadow jar
tasks.build {
    dependsOn(tasks.shadowJar)
}
