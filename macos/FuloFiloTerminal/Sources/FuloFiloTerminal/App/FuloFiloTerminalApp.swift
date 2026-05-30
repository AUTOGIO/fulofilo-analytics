import SwiftUI

@main
struct FuloFiloTerminalApp: App {
    @State private var settings = SettingsStore()
    
    var body: some Scene {
        WindowGroup {
            RootDashboardView()
                .environment(settings)
                .frame(minWidth: 860, minHeight: 540)
                .onAppear {
                    if let window = NSApplication.shared.windows.first {
                        // Restore persisted window size
                        let frame = NSRect(
                            x: window.frame.origin.x,
                            y: window.frame.origin.y,
                            width: settings.windowWidth,
                            height: settings.windowHeight
                        )
                        window.setFrame(frame, display: true)
                        // Allow free resize — no max constraint
                        window.minSize = NSSize(width: 860, height: 540)
                        window.maxSize = NSSize(width: 99999, height: 99999)
                        // Persist size on every resize
                        NotificationCenter.default.addObserver(
                            forName: NSWindow.didResizeNotification,
                            object: window,
                            queue: .main
                        ) { _ in
                            settings.windowWidth  = window.frame.width
                            settings.windowHeight = window.frame.height
                        }
                    }
                }
        }
        .windowStyle(.titleBar)
        .windowToolbarStyle(.unifiedCompact)
        .commands {
            CommandGroup(replacing: .appSettings) {
                Button("Settings...") {
                    showSettings()
                }
                .keyboardShortcut(",", modifiers: .command)
            }
            
            CommandGroup(after: .appSettings) {
                Menu("View") {
                    Button("Increase Font Size") {
                        settings.increaseFontSize()
                    }
                    .keyboardShortcut("+", modifiers: .command)
                    
                    Button("Decrease Font Size") {
                        settings.decreaseFontSize()
                    }
                    .keyboardShortcut("-", modifiers: .command)
                    
                    Divider()
                    
                    Button("Reset Font Size") {
                        settings.resetFontSize()
                    }
                    
                    Button("Reset Window Size") {
                        settings.resetWindowSize()
                    }
                }
            }
        }
    }
    
    private func showSettings() {
        // Placeholder for future settings window
        NSApp.sendAction(Selector(("orderFrontStandardAboutPanel:")), to: nil, from: nil)
    }
}
