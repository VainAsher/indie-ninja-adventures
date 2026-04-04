// :core — shared data types, physics engine, ECS, event bus
// No rendering or networking dependencies here.
plugins {
    id("java")
}

dependencies {
    // msgpack for protocol DTOs (encoding/decoding shared by server + client)
    implementation("org.msgpack:msgpack-core:0.9.8")
    implementation("com.fasterxml.jackson.core:jackson-databind:2.17.1")
    implementation("com.fasterxml.jackson.dataformat:jackson-dataformat-msgpack:0.9.8")

    // Logging
    implementation("org.slf4j:slf4j-api:2.0.13")

    // Testing
    testImplementation("org.junit.jupiter:junit-jupiter:5.10.2")
    testImplementation("org.assertj:assertj-core:3.25.3")
    testRuntimeOnly("org.slf4j:slf4j-simple:2.0.13")
}
