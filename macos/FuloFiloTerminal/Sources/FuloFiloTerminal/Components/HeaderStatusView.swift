import SwiftUI

struct HeaderStatusView: View {
    let status: [StatusMetric]

    var body: some View {
        HStack(alignment: .top, spacing: TerminalSpacing.sm) {
            BrandBlock()
                .frame(minWidth: 320, alignment: .leading)

            ForEach(status) { metric in
                StatusBlock(metric: metric)
            }
        }
        .padding(TerminalSpacing.sm)
        .background(TerminalColors.bg)
    }
}

private struct BrandBlock: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("FULÔFILÓ")
                .font(TerminalType.value(22))
                .foregroundStyle(TerminalColors.text)
            Text("RETAIL OPERATIONS TERMINAL")
                .font(TerminalType.mono(12, weight: .bold))
                .foregroundStyle(TerminalColors.amber)
            Text("Excel master → sync → parquet/DuckDB → executive intelligence".uppercased())
                .font(TerminalType.mono(10, weight: .regular))
                .foregroundStyle(TerminalColors.dim)
                .lineLimit(2)
        }
        .terminalPanel()
    }
}

private struct StatusBlock: View {
    let metric: StatusMetric
    @State private var hovering = false

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(metric.title.uppercased())
                    .font(TerminalType.label(10))
                    .foregroundStyle(TerminalColors.muted)
                Spacer()
                Rectangle()
                    .fill(metric.accent)
                    .frame(width: 18, height: 3)
                    .cornerRadius(2)
            }
            Text(metric.value)
                .font(TerminalType.value(16))
                .foregroundStyle(TerminalColors.text)
                .lineLimit(1)
            Text(metric.subtitle.uppercased())
                .font(TerminalType.mono(10, weight: .regular))
                .foregroundStyle(TerminalColors.dim)
                .lineLimit(1)
        }
        .padding(TerminalSpacing.sm)
        .background(hovering ? TerminalColors.panel2 : TerminalColors.panel)
        .overlay(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .stroke(hovering ? metric.accent.opacity(0.55) : TerminalColors.border, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        .onHover { hovering = $0 }
    }
}
