import SwiftUI

struct KPICard: View {
    let kpi: KPI
    @State private var hovering = false

    var body: some View {
        VStack(alignment: .leading, spacing: TerminalSpacing.xs) {
            HStack {
                Text(kpi.title.uppercased())
                    .font(TerminalType.label(10))
                    .foregroundStyle(TerminalColors.muted)
                Spacer()
                Circle()
                    .fill(kpi.accent)
                    .frame(width: 7, height: 7)
            }
            Text(kpi.value)
                .font(TerminalType.value(18))
                .foregroundStyle(TerminalColors.text)
                .lineLimit(1)
                .minimumScaleFactor(0.75)
            Text(kpi.subtitle.uppercased())
                .font(TerminalType.mono(10, weight: .regular))
                .foregroundStyle(TerminalColors.dim)
                .lineLimit(1)
        }
        .padding(TerminalSpacing.sm)
        .background(hovering ? TerminalColors.panel2 : TerminalColors.panel)
        .overlay(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .stroke(hovering ? kpi.accent.opacity(0.65) : TerminalColors.border, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        .shadow(color: hovering ? Color.black.opacity(0.35) : .clear, radius: hovering ? 10 : 0, x: 0, y: hovering ? 6 : 0)
        .scaleEffect(hovering ? 1.01 : 1.0)
        .animation(.easeOut(duration: 0.12), value: hovering)
        .onHover { hovering = $0 }
    }
}

