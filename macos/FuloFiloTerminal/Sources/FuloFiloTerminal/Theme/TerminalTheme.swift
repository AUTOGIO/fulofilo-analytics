import SwiftUI

enum TerminalColors {
    static let bg = Color(red: 0.03, green: 0.06, blue: 0.10)            // deep navy
    static let panel = Color(red: 0.06, green: 0.10, blue: 0.16)         // lighter navy
    static let panel2 = Color(red: 0.07, green: 0.12, blue: 0.19)        // hover/active
    static let border = Color(red: 0.15, green: 0.22, blue: 0.32)

    static let text = Color(red: 0.88, green: 0.92, blue: 0.98)
    static let muted = Color(red: 0.63, green: 0.70, blue: 0.80)
    static let dim = Color(red: 0.46, green: 0.54, blue: 0.66)

    static let amber = Color(red: 0.98, green: 0.70, blue: 0.22)
    static let orange = Color(red: 0.98, green: 0.55, blue: 0.22)
    static let green = Color(red: 0.18, green: 0.82, blue: 0.45)
    static let red = Color(red: 0.92, green: 0.24, blue: 0.28)
    static let cyan = Color(red: 0.20, green: 0.78, blue: 0.95)
    static let blue = Color(red: 0.25, green: 0.52, blue: 0.98)
    static let violet = Color(red: 0.62, green: 0.42, blue: 0.98)
}

enum TerminalSpacing {
    static let xxs: CGFloat = 4
    static let xs: CGFloat = 6
    static let sm: CGFloat = 10
    static let md: CGFloat = 14
    static let lg: CGFloat = 18
}

enum TerminalType {
    static func label(_ size: CGFloat = 10, weight: Font.Weight = .semibold) -> Font {
        .system(size: size, weight: weight, design: .rounded)
    }

    static func mono(_ size: CGFloat = 11, weight: Font.Weight = .medium) -> Font {
        .system(size: size, weight: weight, design: .monospaced)
    }

    static func value(_ size: CGFloat = 18, weight: Font.Weight = .bold) -> Font {
        .system(size: size, weight: weight, design: .monospaced)
    }
}

extension View {
    func terminalPanel(padding: CGFloat = TerminalSpacing.sm) -> some View {
        self
            .padding(padding)
            .background(TerminalColors.panel)
            .overlay(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .stroke(TerminalColors.border, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
    }

    func terminalPanelActive(padding: CGFloat = TerminalSpacing.sm) -> some View {
        self
            .padding(padding)
            .background(TerminalColors.panel2)
            .overlay(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .stroke(TerminalColors.border.opacity(0.9), lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
    }
}
