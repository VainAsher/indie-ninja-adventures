// :shadowascent — Shadow Ascent game-specific simulation and world generation.
// Depends on :core (engine primitives). Consumed by :server and :client.
plugins {
    id("java-library")
}

dependencies {
    api(project(":core"))

    // msgpack carried through for any sim DTOs that encode directly
    implementation("org.msgpack:msgpack-core:0.9.8")
    implementation("com.fasterxml.jackson.core:jackson-databind:2.17.1")
    implementation("org.slf4j:slf4j-api:2.0.13")

    testImplementation("org.junit.jupiter:junit-jupiter:5.10.2")
    testImplementation("org.assertj:assertj-core:3.25.3")
    testRuntimeOnly("org.slf4j:slf4j-simple:2.0.13")
}

tasks.register<JavaExec>("worldgenSnapshot") {
    group = "worldgen"
    description = "Export a deterministic world-generation JSON snapshot."
    classpath = sourceSets["main"].runtimeClasspath
    mainClass.set("com.indieniinja.world.WorldGenerationSnapshotCommand")

    val campaignId = (findProperty("campaignId") as String?)?.takeIf { it.isNotBlank() }
    val baseArgs = mutableListOf(
        "--seed", (findProperty("seed") as String?) ?: "1",
        "--rooms", (findProperty("rooms") as String?) ?: "20",
        "--shape", (findProperty("shape") as String?) ?: "BLOB",
        "--out", (findProperty("out") as String?) ?: "build/worldgen-snapshots/snapshot.json",
    )
    if (campaignId != null) {
        baseArgs += listOf("--campaign-id", campaignId)
    }
    args(baseArgs)
}
