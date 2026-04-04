rootProject.name = "indie-ninja-adventures"

include(":core", ":server", ":client")

project(":core").projectDir   = file("core")
project(":server").projectDir = file("server")
project(":client").projectDir = file("client")
