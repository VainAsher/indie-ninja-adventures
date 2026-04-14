// Root build — shared config for all sub-modules

// Copy fat JARs to repo root so the launcher always picks up the latest build.
// The launcher looks for ninja-server-all.jar and ninja-client-all.jar at the repo root.
tasks.register("copyJars") {
    dependsOn(":server:shadowJar", ":client:shadowJar")
    doLast {
        val repoRoot = rootProject.projectDir.parentFile
        copy {
            from(project(":server").layout.buildDirectory.file("libs/ninja-server-all.jar"))
            from(project(":client").layout.buildDirectory.file("libs/ninja-client-all.jar"))
            into(repoRoot)
        }
        println("Copied JARs to ${repoRoot.absolutePath}")
    }
}

tasks.register("buildAll") {
    dependsOn("copyJars")
    group = "build"
    description = "Build fat JARs and copy them to the repo root for the launcher."
}

subprojects {
    apply(plugin = "java")

    group   = "com.indieniinja"
    version = "0.11.30"

    repositories {
        mavenCentral()
    }

    configure<JavaPluginExtension> {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }

    tasks.withType<JavaCompile> {
        options.encoding = "UTF-8"
    }

    tasks.withType<Test> {
        useJUnitPlatform()
        testLogging {
            events("passed", "failed", "skipped")
        }
    }
}
