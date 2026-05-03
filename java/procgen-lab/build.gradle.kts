// :procgen-lab — Standalone procedural generation lab and Swing debug UI.
// No dependency on live game modules. Java Swing + stdlib only.

dependencies {
    testImplementation("org.junit.jupiter:junit-jupiter:5.10.2")
    testImplementation("org.assertj:assertj-core:3.25.3")
}

tasks.register<JavaExec>("runLab") {
    group = "application"
    description = "Launch the procedural generation lab UI."
    classpath = sourceSets["main"].runtimeClasspath
    mainClass.set("com.indieniinja.procgen.Main")
}
