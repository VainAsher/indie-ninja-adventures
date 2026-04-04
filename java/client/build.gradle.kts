// :client — libGDX desktop client (Phase C — scaffold only for now)
// Phase A: client stays as Python/Pygame. This module is a placeholder.
plugins {
    id("java")
}

val gdxVersion = "1.12.1"

dependencies {
    implementation(project(":core"))

    // libGDX — Phase C implementation
    implementation("com.badlogicgames.gdx:gdx:$gdxVersion")
    implementation("com.badlogicgames.gdx:gdx-backend-lwjgl3:$gdxVersion")
    implementation("com.badlogicgames.gdx:gdx-platform:$gdxVersion:natives-desktop")

    // Testing
    testImplementation("org.junit.jupiter:junit-jupiter:5.10.2")
    testImplementation("org.assertj:assertj-core:3.25.3")
}
