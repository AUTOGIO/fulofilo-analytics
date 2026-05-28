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
