import SwiftUI

struct TerminalTabStrip: View {
    @Binding var selection: TerminalTab

    var body: some View {
        HStack(spacing: TerminalSpacing.xs) {
            ForEach(TerminalTab.allCases) { tab in
                TerminalTabButton(tab: tab, isSelected: tab == selection) {
                    selection = tab
                }
            }
            Spacer(minLength: 0)
        }
        .padding(.horizontal, TerminalSpacing.sm)
        .padding(.vertical, TerminalSpacing.xs)
        .background(TerminalColors.bg)
    }
}

private struct TerminalTabButton: View {
    let tab: TerminalTab
    let isSelected: Bool
    let onClick: () -> Void
    @State private var hovering = false

    var body: some View {
        Button(action: onClick) {
            HStack(spacing: 8) {
                Rectangle()
                    .fill(tab.accent)
                    .frame(width: 8, height: 16)
                    .cornerRadius(2)
                Text(tab.rawValue)
                    .font(TerminalType.mono(11, weight: .semibold))
                    .foregroundStyle(TerminalColors.text)
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 8)
            .background(background)
            .overlay(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .stroke(isSelected ? tab.accent.opacity(0.75) : TerminalColors.border, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        }
        .buttonStyle(.plain)
        .onHover { hovering = $0 }
    }

    private var background: Color {
        if isSelected { return TerminalColors.panel2 }
        if hovering { return TerminalColors.panel2.opacity(0.8) }
        return TerminalColors.panel
    }
}

