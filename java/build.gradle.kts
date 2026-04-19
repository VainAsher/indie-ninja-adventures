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

// ── Asset pipeline ─────────────────────────────────────────────────────────

/**
 * Regenerate assets/asset_manifest.json by scanning the assets/ directory.
 *
 * Runs tools/asset_pipeline.py via the system Python 3 interpreter.
 * Called automatically by the client shadowJar task so the manifest is always
 * current when a new fat JAR is produced.
 *
 * To run manually:  ./gradlew buildAssets
 * To only check:    python tools/asset_pipeline.py --check
 */
tasks.register<Exec>("buildAssets") {
    group       = "build"
    description = "Scan assets/ and update assets/asset_manifest.json."
    val repoRoot = rootProject.projectDir.parentFile
    workingDir  = repoRoot
    val python = if (System.getProperty("os.name").lowercase().contains("win")) "python" else "python3"
    commandLine(python, "tools/asset_pipeline.py",
        "--root",  "assets",
        "--out",   "assets/asset_manifest.json")
}

// Hook buildAssets into the client shadow JAR so the manifest is always current.
project(":client").tasks.matching { it.name == "shadowJar" }.configureEach {
    dependsOn(tasks.named("buildAssets"))
}

// ── OneDrive build-dir redirect ─────────────────────────────────────────────
//
// OneDrive syncs java/*/build/ in real-time, holding file handles that block
// Gradle's output-directory cleanup step (IOException: Unable to delete).
// When the repo lives under OneDrive, redirect all subproject build dirs to
// %LOCALAPPDATA%\indie-ninja-builds\<module> — outside the sync boundary.
//
// CI runners (GitHub Actions windows-latest) use paths like D:\a\... which do
// NOT contain "OneDrive", so this block is a no-op on CI and artifact paths
// remain at the standard java/*/build/libs/ locations.
val repoPathNorm = rootDir.canonicalPath.replace('\\', '/')
val onOneDrive   = repoPathNorm.contains("/OneDrive/", ignoreCase = true)
if (onOneDrive) {
    val localRoot = (System.getenv("LOCALAPPDATA") ?: System.getProperty("java.io.tmpdir"))
        .replace('\\', '/')
    val buildRoot = "$localRoot/indie-ninja-builds"
    logger.lifecycle("[OneDrive] Build dirs redirected → $buildRoot/<module>")
    subprojects {
        layout.buildDirectory.set(File("$buildRoot/${project.name}"))
    }
}

subprojects {
    apply(plugin = "java")

    group   = "com.indieniinja"
    version = "0.11.68"

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

