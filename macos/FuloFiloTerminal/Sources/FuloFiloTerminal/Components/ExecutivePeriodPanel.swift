import SwiftUI

struct ExecutivePeriodPanel: View {
    let periods: TerminalStore.ReadModelSnapshot.ExecutivePeriods

    @State private var grain: PeriodGrain = .month

    enum PeriodGrain: String, CaseIterable, Identifiable {
        case month = "Month"
        case week = "Week"
        var id: String { rawValue }
    }

    private var rows: [TerminalStore.ReadModelSnapshot.ExecutivePeriodRow] {
        grain == .month ? periods.months : periods.weeks
    }

    var body: some View {
        VStack(alignment: .leading, spacing: TerminalSpacing.sm) {
            Picker("Grain", selection: $grain) {
                ForEach(PeriodGrain.allCases) { g in
                    Text(g.rawValue.uppercased()).tag(g)
                }
            }
            .pickerStyle(.segmented)
            .labelsHidden()

            if rows.isEmpty {
                Text("NO PERIOD DATA")
                    .font(TerminalType.mono(10, weight: .regular))
                    .foregroundStyle(TerminalColors.dim)
            } else {
                ScrollView(.horizontal, showsIndicators: false) {
                    VStack(alignment: .leading, spacing: 0) {
                        periodHeader
                        ForEach(rows) { row in
                            periodRow(row)
                            Divider().overlay(TerminalColors.border)
                        }
                    }
                    .frame(minWidth: 920)
                }
            }

            Text(
                "LOW STOCK AND OPS ARE CURRENT-STATE ONLY. TURNOVER AND SELL-THROUGH USE CURRENT INVENTORY."
            )
            .font(TerminalType.mono(9, weight: .regular))
            .foregroundStyle(TerminalColors.dim)
            .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var periodHeader: some View {
        HStack(spacing: TerminalSpacing.xs) {
            headerCell("PERIOD", width: 100)
            headerCell("REVENUE", width: 96)
            headerCell("MARGIN", width: 64)
            headerCell("TURNOVER", width: 72)
            headerCell("SELL-THRU", width: 72)
            headerCell("TICKET", width: 80)
            headerCell("LOW", width: 40)
            headerCell("OPS", width: 48)
            headerCell("BURN", width: 56)
        }
        .padding(.vertical, 6)
        .background(TerminalColors.panel2)
    }

    private func periodRow(_ row: TerminalStore.ReadModelSnapshot.ExecutivePeriodRow) -> some View {
        HStack(spacing: TerminalSpacing.xs) {
            dataCell(row.label, width: 100, accent: TerminalColors.text)
            dataCell(row.revenue_fmt, width: 96, accent: TerminalColors.green)
            dataCell(String(format: "%.1f%%", row.margin_pct), width: 64, accent: TerminalColors.amber)
            dataCell(String(format: "%.2fx", row.avg_turnover), width: 72, accent: TerminalColors.cyan)
            dataCell(String(format: "%.1f%%", row.sell_through), width: 72, accent: TerminalColors.blue)
            dataCell(row.ticket_fmt, width: 80, accent: TerminalColors.text)
            dataCell("—", width: 40, accent: TerminalColors.dim)
            dataCell("—", width: 48, accent: TerminalColors.dim)
            dataCell(String(format: "%.1f%%", row.burn_ratio), width: 56, accent: TerminalColors.orange)
        }
        .padding(.vertical, 5)
    }

    private func headerCell(_ text: String, width: CGFloat) -> some View {
        Text(text)
            .font(TerminalType.label(9))
            .foregroundStyle(TerminalColors.muted)
            .frame(width: width, alignment: .leading)
    }

    private func dataCell(_ text: String, width: CGFloat, accent: Color) -> some View {
        Text(text.uppercased())
            .font(TerminalType.mono(10, weight: .medium))
            .foregroundStyle(accent)
            .lineLimit(1)
            .minimumScaleFactor(0.7)
            .frame(width: width, alignment: .leading)
    }
}
