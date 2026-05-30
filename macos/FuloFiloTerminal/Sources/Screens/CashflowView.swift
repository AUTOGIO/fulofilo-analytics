import SwiftUI

struct CashflowView: View {
    @Binding var selectedTab: TerminalTab
    @State private var category = "Todas"

    private var categories: [String] {
        let base = Set(MockData.bubblePoints.map(\.category))
        return ["Todas"] + base.sorted()
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: TerminalSpacing.sm) {
                CashflowHeader()

                FilterBar(category: $category, options: categories)

                SectionPanel(
                    title: "MARGIN MATRIX SCATTER",
                    subtitle: "MATRIZ DE MARGEM — TAMANHO DA BOLHA = RECEITA",
                    accent: TerminalColors.amber
                ) {
                    BubbleMarginChart(points: MockData.bubblePoints, category: category)
                        .frame(maxWidth: .infinity)
                }
            }
            .padding(TerminalSpacing.sm)
        }
        .background(TerminalColors.bg)
    }
}

private struct CashflowHeader: View {
    var body: some View {
        HStack(alignment: .top, spacing: TerminalSpacing.sm) {
            VStack(alignment: .leading, spacing: 6) {
                Text("CASHFLOW + MARGIN MATRIX")
                    .font(TerminalType.value(20))
                    .foregroundStyle(TerminalColors.text)
                Text("MARGIN SIGNAL → PRODUCT CLASSIFICATION → CASH DISCIPLINE".uppercased())
                    .font(TerminalType.mono(11, weight: .semibold))
                    .foregroundStyle(TerminalColors.amber)
                HStack(spacing: 10) {
                    Badge(label: "RUNTIME STATE", value: "READ MODEL", accent: TerminalColors.cyan)
                    Badge(label: "CANONICAL SOURCE", value: "data/excel/FuloFilo_Master.xlsx", accent: TerminalColors.green)
                }
            }
            Spacer(minLength: 0)
        }
        .terminalPanel()
    }
}

private struct Badge: View {
    let label: String
    let value: String
    let accent: Color

    var body: some View {
        HStack(spacing: 8) {
            Rectangle().fill(accent).frame(width: 6, height: 12).cornerRadius(2)
            Text(label.uppercased())
                .font(TerminalType.mono(10, weight: .semibold))
                .foregroundStyle(TerminalColors.muted)
            Text(value)
                .font(TerminalType.mono(10, weight: .regular))
                .foregroundStyle(TerminalColors.text)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(TerminalColors.panel.opacity(0.75))
        .overlay(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .stroke(TerminalColors.border.opacity(0.8), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
    }
}

private struct FilterBar: View {
    @Binding var category: String
    let options: [String]

    var body: some View {
        HStack(spacing: TerminalSpacing.sm) {
            Text("FILTRAR POR CATEGORIA")
                .font(TerminalType.mono(11, weight: .bold))
                .foregroundStyle(TerminalColors.amber)
            Spacer(minLength: 0)
            Picker("", selection: $category) {
                ForEach(options, id: \.self) { o in
                    Text(o.uppercased()).tag(o)
                }
            }
            .pickerStyle(.menu)
            .font(TerminalType.mono(11))
            .tint(TerminalColors.cyan)
        }
        .terminalPanel()
    }
}

