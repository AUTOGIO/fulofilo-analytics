import SwiftUI

@main
struct PrintFactoryKitApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .windowStyle(.titleBar)
        .windowToolbarStyle(.unified)
        .commands {
            CommandGroup(replacing: .newItem) {}
        }
        .defaultSize(width: 800, height: 700)
    }
}
