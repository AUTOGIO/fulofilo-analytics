import SwiftUI

struct InsightPanel: View {
    let title: String
    let subtitle: String
    let rows: [Insight]
    @State private var selectedId: Insight.ID?

    var body: some View {
        SectionPanel(title: title, subtitle: subtitle, accent: TerminalColors.cyan) {
            VStack(alignment: .leading, spacing: 6) {
                ForEach(rows) { row in
                    InsightRow(row: row, isSelected: row.id == selectedId)
                        .onTapGesture { selectedId = row.id }
                }
            }
        }
    }
}

private struct InsightRow: View {
    let row: Insight
    let isSelected: Bool
    @State private var hovering = false

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Text(row.code)
                .font(TerminalType.mono(11, weight: .bold))
                .foregroundStyle(row.accent)
                .frame(width: 54, alignment: .leading)

            VStack(alignment: .leading, spacing: 4) {
                Text(row.text.uppercased())
                    .font(TerminalType.mono(11, weight: .semibold))
                    .foregroundStyle(TerminalColors.text)
                Text(row.detail.uppercased())
                    .font(TerminalType.mono(10, weight: .regular))
                    .foregroundStyle(TerminalColors.dim)
                    .lineLimit(2)
            }
            Spacer(minLength: 0)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 10)
        .background(isSelected ? TerminalColors.panel2 : (hovering ? TerminalColors.panel2.opacity(0.8) : TerminalColors.panel.opacity(0.35)))
        .overlay(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .stroke(isSelected ? row.accent.opacity(0.55) : TerminalColors.border.opacity(hovering ? 0.6 : 0.2), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        .onHover { hovering = $0 }
    }
}

struct AnomalyPanel: View {
    let title: String
    let subtitle: String
    let rows: [Anomaly]

    var body: some View {
        SectionPanel(title: title, subtitle: subtitle, accent: TerminalColors.red) {
            VStack(alignment: .leading, spacing: 6) {
                ForEach(rows) { a in
                    AnomalyRow(a: a)
                }
            }
        }
    }
}

private struct AnomalyRow: View {
    let a: Anomaly
    @State private var hovering = false

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Text(a.code)
                .font(TerminalType.mono(11, weight: .bold))
                .foregroundStyle(a.accent)
                .frame(width: 40, alignment: .leading)

            Text(a.kind.uppercased())
                .font(TerminalType.mono(11, weight: .bold))
                .foregroundStyle(TerminalColors.muted)
                .frame(width: 56, alignment: .leading)

            Text(a.text.uppercased())
                .font(TerminalType.mono(10, weight: .regular))
                .foregroundStyle(TerminalColors.text)
                .lineLimit(2)

            Spacer(minLength: 0)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 10)
        .background(hovering ? TerminalColors.panel2.opacity(0.85) : TerminalColors.panel.opacity(0.35))
        .overlay(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .stroke(TerminalColors.border.opacity(hovering ? 0.7 : 0.25), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        .onHover { hovering = $0 }
    }
}

struct SystemContractPanel: View {
    let title: String
    let subtitle: String
    let rows: [(String, String)]

    var body: some View {
        SectionPanel(title: title, subtitle: subtitle, accent: TerminalColors.amber) {
            VStack(alignment: .leading, spacing: 10) {
                ForEach(Array(rows.enumerated()), id: \.offset) { _, row in
                    HStack(alignment: .top, spacing: 10) {
                        Text(row.0.uppercased())
                            .font(TerminalType.mono(10, weight: .semibold))
                            .foregroundStyle(TerminalColors.muted)
                            .frame(width: 130, alignment: .leading)
                        Text(row.1)
                            .font(TerminalType.mono(10, weight: .regular))
                            .foregroundStyle(TerminalColors.text)
                        Spacer(minLength: 0)
                    }
                }
            }
        }
    }
}
