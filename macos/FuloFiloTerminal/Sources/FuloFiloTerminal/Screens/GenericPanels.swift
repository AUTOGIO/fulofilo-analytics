import SwiftUI

struct TerminalPlaceholderScreen: View {
    let title: String
    let subtitle: String
    let accent: Color
    let bodyText: String

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: TerminalSpacing.sm) {
                SectionPanel(title: title, subtitle: subtitle, accent: accent) {
                    VStack(alignment: .leading, spacing: 10) {
                        Text(bodyText.uppercased())
                            .font(TerminalType.mono(11, weight: .semibold))
                            .foregroundStyle(TerminalColors.text)
                        Text("THIS SCREEN IS WIRED INTO THE NAVIGATION SHELL; ADD DOMAIN-SPECIFIC PANELS AS NEEDED.".uppercased())
                            .font(TerminalType.mono(10, weight: .regular))
                            .foregroundStyle(TerminalColors.dim)
                    }
                }
            }
            .padding(TerminalSpacing.sm)
        }
        .background(TerminalColors.bg)
    }
}

struct SystemHealthScreen: View {
    @Environment(TerminalStore.self) private var store

    var body: some View {
        TerminalPlaceholderScreen(
            title: "SYSTEM HEALTH",
            subtitle: "READ MODEL + PIPELINE CONTRACT",
            accent: TerminalColors.green,
            bodyText: "READ MODEL STATE: \(store.readModelState) • LAST GENERATED: \(store.snapshot?.meta.generated_at ?? "—")"
        )
    }
}

struct AlertsScreen: View {
    @Environment(TerminalStore.self) private var store

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: TerminalSpacing.sm) {
                AnomalyPanel(title: "ALERTS", subtitle: "OPERATIONAL WARNING BUS", rows: store.anomalyRows)
            }
            .padding(TerminalSpacing.sm)
        }
        .background(TerminalColors.bg)
    }
}

struct InventoryIntelligenceScreen: View {
    @Environment(TerminalStore.self) private var store

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: TerminalSpacing.sm) {
                SectionPanel(title: "INVENTORY INTELLIGENCE", subtitle: "STOCK HEALTH MATRIX", accent: TerminalColors.cyan) {
                    InventoryMatrixChart(categories: inventoryMatrixForReadModel())
                }
                InsightPanel(title: "RESTOCK", subtitle: "WATCHLIST", rows: store.insightRows)
            }
            .padding(TerminalSpacing.sm)
        }
        .background(TerminalColors.bg)
    }

    private func inventoryMatrixForReadModel() -> [InventoryCategory] {
        guard let snap = store.snapshot, !snap.inventory_matrix.isEmpty else { return MockData.inventoryMatrix }
        return snap.inventory_matrix.map { row in
            InventoryCategory(
                name: row.name,
                segments: [
                    InventorySegment(label: "HEALTHY", value: row.healthy, color: TerminalColors.green),
                    InventorySegment(label: "WATCH", value: row.watch, color: TerminalColors.cyan),
                    InventorySegment(label: "RISK", value: row.risk, color: TerminalColors.red)
                ]
            )
        }
    }
}

struct CategoryIntelligenceScreen: View {
    @Environment(TerminalStore.self) private var store

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: TerminalSpacing.sm) {
                if let abc = store.abcSummary {
                    ABCAnalysisPanel(abc: abc)
                } else {
                    SectionPanel(title: "CATEGORY INTELLIGENCE", subtitle: "ABC ANALYSIS — AWAITING SYNC", accent: TerminalColors.amber) {
                        VStack(alignment: .leading, spacing: 10) {
                            Text("ABC CLASSIFICATION NOT YET AVAILABLE — RUN SYNC TO LOAD.")
                                .font(TerminalType.mono(11, weight: .semibold))
                                .foregroundStyle(TerminalColors.text)
                            Text("CLASS A ≤ 80% CUMULATIVE REVENUE  •  CLASS B ≤ 95%  •  CLASS C > 95%")
                                .font(TerminalType.mono(10, weight: .regular))
                                .foregroundStyle(TerminalColors.dim)
                        }
                    }
                }
            }
            .padding(TerminalSpacing.sm)
        }
        .background(TerminalColors.bg)
    }
}

private struct ABCAnalysisPanel: View {
    let abc: TerminalStore.ReadModelSnapshot.ABCSummary

    var body: some View {
        SectionPanel(
            title: "ABC ANALYSIS",
            subtitle: "REVENUE CLASSIFICATION — A ≤ 80% / B ≤ 95% / C > 95%",
            accent: TerminalColors.amber
        ) {
            HStack(alignment: .top, spacing: TerminalSpacing.sm) {
                ABCClassBlock(
                    cls: "A", count: abc.a_count, pct: abc.a_revenue_pct,
                    items: abc.top_a, accent: TerminalColors.green
                )
                ABCClassBlock(
                    cls: "B", count: abc.b_count, pct: abc.b_revenue_pct,
                    items: abc.top_b, accent: TerminalColors.amber
                )
                ABCClassBlock(
                    cls: "C", count: abc.c_count, pct: abc.c_revenue_pct,
                    items: abc.top_c, accent: TerminalColors.muted
                )
            }
        }
    }
}

private struct ABCClassBlock: View {
    let cls: String
    let count: Int
    let pct: Double
    let items: [TerminalStore.ReadModelSnapshot.ABCItem]
    let accent: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("CLASS \(cls)")
                    .font(TerminalType.mono(12, weight: .bold))
                    .foregroundStyle(accent)
                Spacer(minLength: 0)
                Text(String(format: "%.1f%%", pct))
                    .font(TerminalType.value(14))
                    .foregroundStyle(accent)
            }
            Text("\(count) SKUs")
                .font(TerminalType.mono(10))
                .foregroundStyle(TerminalColors.dim)
            Divider().overlay(TerminalColors.border)
            ForEach(items, id: \.name) { item in
                HStack(spacing: 6) {
                    Text(item.name.uppercased())
                        .font(TerminalType.mono(9))
                        .foregroundStyle(TerminalColors.text)
                        .lineLimit(1)
                    Spacer(minLength: 0)
                    Text(String(format: "%.0f%%", item.margin_pct))
                        .font(TerminalType.mono(9, weight: .semibold))
                        .foregroundStyle(TerminalColors.muted)
                }
            }
        }
        .padding(TerminalSpacing.sm)
        .background(TerminalColors.panel)
        .overlay(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .stroke(accent.opacity(0.35), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
        .frame(maxWidth: .infinity)
    }
}

struct SalesAnalyticsScreen: View {
    @Environment(TerminalStore.self) private var store

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: TerminalSpacing.sm) {
                SectionPanel(title: "SALES ANALYTICS", subtitle: "VELOCITY + DEMAND TREND", accent: TerminalColors.green) {
                    SalesVelocityChart(points: salesSeriesForReadModel())
                }
            }
            .padding(TerminalSpacing.sm)
        }
        .background(TerminalColors.bg)
    }

    private func salesSeriesForReadModel() -> [SalesPoint] {
        guard let snap = store.snapshot, !snap.sales_series.isEmpty else { return MockData.salesSeries }
        return snap.sales_series.map { .init(label: $0.label, revenue: $0.revenue, units: $0.units) }
    }
}
