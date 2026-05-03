rootProject.name = "indie-ninja-adventures"

include(":core", ":shadowascent", ":server", ":client", ":procgen-lab")

project(":core").projectDir         = file("core")
project(":shadowascent").projectDir = file("shadowascent")
project(":server").projectDir       = file("server")
project(":client").projectDir       = file("client")
project(":procgen-lab").projectDir  = file("procgen-lab")
