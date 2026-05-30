import SwiftUI

struct SectionPanel<Content: View>: View {
    let title: String
    let subtitle: String
    let accent: Color
    @ViewBuilder var content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: TerminalSpacing.sm) {
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: TerminalSpacing.xs) {
                    Rectangle()
                        .fill(accent)
                        .frame(width: 6, height: 14)
                        .cornerRadius(2)
                    Text(title.uppercased())
                        .font(TerminalType.label(11, weight: .bold))
                        .foregroundStyle(TerminalColors.text)
                }
                Text(subtitle.uppercased())
                    .font(TerminalType.mono(10, weight: .regular))
                    .foregroundStyle(TerminalColors.dim)
            }
            content
        }
        .terminalPanel()
    }
}

