import SwiftUI

@main
struct FuloFiloTerminalApp: App {
    var body: some Scene {
        WindowGroup {
            RootDashboardView()
                .frame(minWidth: 1280, minHeight: 760)
        }
        .windowStyle(.titleBar)
        .windowToolbarStyle(.unifiedCompact)
    }
}

