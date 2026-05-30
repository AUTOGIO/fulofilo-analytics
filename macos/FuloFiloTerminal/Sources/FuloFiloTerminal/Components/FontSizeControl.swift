import SwiftUI

/// Compact font size control component for toolbar or sidebar
struct FontSizeControl: View {
    @Environment(SettingsStore.self) var settings
    
    var body: some View {
        HStack(spacing: 8) {
            Button(action: { settings.decreaseFontSize() }) {
                Image(systemName: "minus.circle.fill")
                    .font(.system(size: 14))
                    .foregroundColor(TerminalColors.muted)
            }
            .buttonStyle(.plain)
            .help("Decrease font size (⌘−)")
            
            VStack(spacing: 2) {
                Text("SIZE")
                    .font(.system(size: 8, weight: .semibold, design: .rounded))
                    .foregroundColor(TerminalColors.dim)
                Text("\(Int(settings.baseFontSize))")
                    .font(.system(size: 12, weight: .bold, design: .monospaced))
                    .foregroundColor(TerminalColors.cyan)
            }
            .frame(width: 30)
            
            Button(action: { settings.increaseFontSize() }) {
                Image(systemName: "plus.circle.fill")
                    .font(.system(size: 14))
                    .foregroundColor(TerminalColors.green)
            }
            .buttonStyle(.plain)
            .help("Increase font size (⌘+)")
        }
        .terminalPanel(padding: 6)
    }
}

/// Extended font size settings panel
struct FontSizePanel: View {
    @Environment(SettingsStore.self) var settings
    @State private var isExpanded = false
    
    var body: some View {
        VStack(spacing: 12) {
            HStack {
                Text("FONT SIZE")
                    .font(.system(size: 11, weight: .semibold, design: .rounded))
                    .foregroundColor(TerminalColors.muted)
                Spacer()
                Text("\(Int(settings.baseFontSize))pt")
                    .font(.system(size: 14, weight: .bold, design: .monospaced))
                    .foregroundColor(TerminalColors.cyan)
            }
            
            Slider(value: Bindable(settings).baseFontSize, in: 8...24, step: 1)
                .tint(TerminalColors.cyan)
            
            HStack(spacing: 10) {
                Button(action: { settings.decreaseFontSize() }) {
                    Label("Smaller", systemImage: "minus.circle.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                
                Button(action: { settings.resetFontSize() }) {
                    Label("Reset", systemImage: "arrow.counterclockwise")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                
                Button(action: { settings.increaseFontSize() }) {
                    Label("Larger", systemImage: "plus.circle.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
            }
        }
        .terminalPanel(padding: 10)
    }
}

#Preview {
    @Previewable @State var settings = SettingsStore()
    
    VStack(spacing: 20) {
        FontSizeControl()
            .environment(settings)
        
        FontSizePanel()
            .environment(settings)
    }
    .padding()
    .background(TerminalColors.bg)
}
