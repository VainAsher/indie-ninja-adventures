// :core — shared data types, physics engine, ECS, event bus
// No rendering or networking dependencies here.
plugins {
    id("java-library")
    id("maven-publish")
}

dependencies {
    // msgpack for protocol DTOs (encoding/decoding shared by server + client)
    implementation("org.msgpack:msgpack-core:0.9.8")

    // JSON parsing and schema validation for ContentLoader
    implementation("com.fasterxml.jackson.core:jackson-databind:2.17.1")
    implementation("com.networknt:json-schema-validator:1.4.3")

    // Logging
    implementation("org.slf4j:slf4j-api:2.0.13")

    // Testing
    testImplementation("org.junit.jupiter:junit-jupiter:5.10.2")
    testImplementation("org.assertj:assertj-core:3.25.3")
    testRuntimeOnly("org.slf4j:slf4j-simple:2.0.13")
}

// ── Maven publication to GitHub Packages ─────────────────────────────────────
//
// Publish command:  ./gradlew :core:publish
// Credentials:     GITHUB_ACTOR + GITHUB_TOKEN env vars (set in CI and locally)
// Artifact coords: com.indieniinja:engine-core:<version>
// Registry URL:    https://maven.pkg.github.com/VainAsher/indie-ninja-adventures
//
publishing {
    publications {
        create<MavenPublication>("engineCore") {
            from(components["java"])
            groupId    = "com.indieniinja"
            artifactId = "engine-core"
            // version inherited from subprojects block in root build.gradle.kts
            pom {
                name.set("Shadow Ascent Engine Core")
                description.set("Reusable 2D game engine core: ECS, physics, content system, network protocol.")
                url.set("https://github.com/VainAsher/indie-ninja-adventures")
                licenses {
                    license {
                        name.set("MIT License")
                        url.set("https://opensource.org/licenses/MIT")
                    }
                }
            }
        }
    }
    repositories {
        maven {
            name = "GitHubPackages"
            url  = uri("https://maven.pkg.github.com/VainAsher/indie-ninja-adventures")
            credentials {
                username = System.getenv("GITHUB_ACTOR")  ?: project.findProperty("gpr.user") as String?
                password = System.getenv("GITHUB_TOKEN")  ?: project.findProperty("gpr.key")  as String?
            }
        }
    }
}
