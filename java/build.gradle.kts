// Root build — shared config for all sub-modules
plugins {
    java apply false
}

subprojects {
    apply(plugin = "java")

    group   = "com.indieniinja"
    version = "0.10.0"

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
