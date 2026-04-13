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
