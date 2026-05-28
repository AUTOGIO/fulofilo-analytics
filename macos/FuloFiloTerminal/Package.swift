// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "FuloFiloTerminal",
    defaultLocalization: "en",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(name: "FuloFiloTerminal", targets: ["FuloFiloTerminal"])
    ],
    dependencies: [],
    targets: [
        .executableTarget(
            name: "FuloFiloTerminal",
            dependencies: [],
            path: "Sources/FuloFiloTerminal"
        )
    ]
)
