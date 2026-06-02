import SwiftUI

struct ExecutiveOverviewView: View {
    @Binding var selectedTab: TerminalTab
    @Environment(TerminalStore.self) private var store

    private let kpiColumns = [
        GridItem(.adaptive(minimum: 200, maximum: 260), spacing: TerminalSpacing.sm)
    ]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: TerminalSpacing.sm) {
                SectionPanel(
                    title: "EXECUTIVE KPI CLUSTER",
                    subtitle: "FINANCIAL + OPERATIONAL CONTROL",
                    accent: TerminalColors.amber
                ) {
                    LazyVGrid(columns: kpiColumns, alignment: .leading, spacing: TerminalSpacing.sm) {
                        ForEach(kpisForReadModel()) { kpi in
                            KPICard(kpi: kpi)
                        }
                    }
                }

                SectionPanel(
                    title: "PERIOD BREAKDOWN",
                    subtitle: "MONTH + WEEK CONTROL",
                    accent: TerminalColors.cyan
                ) {
                    ExecutivePeriodPanel(periods: periodsForReadModel())
                }

                tabContent
            }
            .padding(TerminalSpacing.sm)
        }
        .background(TerminalColors.bg)
    }

    private func periodsForReadModel() -> TerminalStore.ReadModelSnapshot.ExecutivePeriods {
        store.snapshot?.executive_periods ?? MockData.executivePeriods
    }

    @ViewBuilder
    private var tabContent: some View {
        switch selectedTab {
        case .inventoryMatrix:
            ExecutiveMainGrid(
                inventory: inventoryMatrixForReadModel(),
                sales: salesSeriesForReadModel()
            )
        case .cashflowOps:
            ExecutiveCashOpsPanel()
        case .salesVelocity:
            ExecutiveSalesPanel(points: salesSeriesForReadModel())
        case .reorderActions:
            ExecutiveReorderPanel()
        case .riskAlerts:
            ExecutiveRiskPanel()
        case .exportDesk:
            ExecutiveExportPanel()
        }
    }

    private func kpisForReadModel() -> [KPI] {
        guard let snap = store.snapshot else { return MockData.executiveKPIs }

        let lowCrit = snap.executive.low_critical
        let lowWarn = snap.executive.low_warn
        let lowSubtitle = "\(lowWarn) warn / \(lowCrit) critical"

        return [
            KPI(title: "REVENUE", value: snap.executive.revenue_fmt, subtitle: "gross sales intelligence", accent: TerminalColors.green),
            KPI(title: "MARGIN", value: String(format: "%.1f%%", snap.executive.margin_pct), subtitle: snap.executive.profit_fmt, accent: TerminalColors.amber),
            KPI(title: "INVENTORY TURNOVER", value: String(format: "%.2fx", snap.executive.avg_turnover), subtitle: "sales / live stock", accent: TerminalColors.cyan),
            KPI(title: "SELL-THROUGH", value: String(format: "%.1f%%", snap.executive.sell_through), subtitle: "units sold vs available", accent: TerminalColors.blue),
            KPI(title: "AVG TICKET", value: snap.executive.avg_ticket_fmt, subtitle: "\(Int(snap.executive.units)) units", accent: TerminalColors.green),
            KPI(title: "LOW STOCK ALERTS", value: "\(lowCrit)", subtitle: lowSubtitle, accent: lowCrit > 0 ? TerminalColors.red : TerminalColors.green),
            KPI(title: "OPS EFFICIENCY", value: "\(snap.executive.ops_score)/100", subtitle: snap.executive.readiness.lowercased(), accent: snap.executive.ops_score >= 80 ? TerminalColors.cyan : TerminalColors.amber),
            KPI(title: "FIXED BURN", value: String(format: "%.1f%%", snap.executive.burn_ratio), subtitle: moneyBR(snap.executive.fixed_total), accent: TerminalColors.orange)
        ]
    }

    private func moneyBR(_ v: Double) -> String {
        let iv = Int(v.rounded())
        let nf = NumberFormatter()
        nf.numberStyle = .decimal
        nf.groupingSeparator = "."
        nf.decimalSeparator = ","
        return "R$ \(nf.string(from: NSNumber(value: iv)) ?? "\(iv)")"
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

    private func salesSeriesForReadModel() -> [SalesPoint] {
        guard let snap = store.snapshot, !snap.sales_series.isEmpty else { return MockData.salesSeries }
        return snap.sales_series.map { .init(label: $0.label, revenue: $0.revenue, units: $0.units) }
    }
}

private struct ExecutiveMainGrid: View {
    let inventory: [InventoryCategory]
    let sales: [SalesPoint]

    var body: some View {
        HStack(alignment: .top, spacing: TerminalSpacing.sm) {
            VStack(alignment: .leading, spacing: TerminalSpacing.sm) {
                SectionPanel(
                    title: "INVENTORY INTELLIGENCE",
                    subtitle: "STOCK HEALTH MATRIX",
                    accent: TerminalColors.cyan
                ) {
                    InventoryMatrixChart(categories: inventory)
                        .frame(maxWidth: .infinity)
                }

                SectionPanel(
                    title: "SALES INTELLIGENCE",
                    subtitle: "VELOCITY + DEMAND TREND",
                    accent: TerminalColors.green
                ) {
                    SalesVelocityChart(points: sales)
                        .frame(maxWidth: .infinity)
                }
            }

            ExecutiveRightColumn()
                .frame(width: 440)
        }
    }
}

private struct ExecutiveRightColumn: View {
    @Environment(TerminalStore.self) private var store

    var body: some View {
        VStack(alignment: .leading, spacing: TerminalSpacing.sm) {
            InsightPanel(
                title: "AI RETAIL INSIGHTS",
                subtitle: "ASSISTANT WATCHLIST",
                rows: store.insightRows
            )

            AnomalyPanel(
                title: "OPERATIONAL ANOMALIES",
                subtitle: "RISK WARNINGS",
                rows: store.anomalyRows
            )

            SystemContractPanel(
                title: "SYSTEM CONTRACT",
                subtitle: "EXCEL-FIRST ARCHITECTURE",
                rows: store.contractRows
            )
        }
    }
}

private struct ExecutiveSalesPanel: View {
    let points: [SalesPoint]
    var body: some View {
        HStack(alignment: .top, spacing: TerminalSpacing.sm) {
            SectionPanel(title: "SALES INTELLIGENCE", subtitle: "VELOCITY + DEMAND TREND", accent: TerminalColors.green) {
                SalesVelocityChart(points: points)
                    .frame(maxWidth: .infinity)
            }
            ExecutiveRightColumn()
                .frame(width: 440)
        }
    }
}

private struct ExecutiveCashOpsPanel: View {
    var body: some View {
        HStack(alignment: .top, spacing: TerminalSpacing.sm) {
            SectionPanel(title: "CASHFLOW OPS", subtitle: "DISCIPLINE + RUNWAY SIGNAL", accent: TerminalColors.amber) {
                VStack(alignment: .leading, spacing: 10) {
                    Text("NAV: CF CASHFLOW FOR MARGIN MATRIX + SCATTER".uppercased())
                        .font(TerminalType.mono(11, weight: .semibold))
                        .foregroundStyle(TerminalColors.text)
                    Text("THIS TAB REPRESENTS THE CASHFLOW OPERATING CONTEXT; USE SIDEBAR CF FOR FULL SCREEN.".uppercased())
                        .font(TerminalType.mono(10, weight: .regular))
                        .foregroundStyle(TerminalColors.dim)
                }
            }
            ExecutiveRightColumn()
                .frame(width: 440)
        }
    }
}

private struct ExecutiveReorderPanel: View {
    @Environment(TerminalStore.self) private var store
    var body: some View {
        HStack(alignment: .top, spacing: TerminalSpacing.sm) {
            InsightPanel(title: "REORDER ACTIONS", subtitle: "RESTOCK CANDIDATES", rows: store.insightRows)
            ExecutiveRightColumn()
                .frame(width: 440)
        }
    }
}

private struct ExecutiveRiskPanel: View {
    @Environment(TerminalStore.self) private var store
    var body: some View {
        HStack(alignment: .top, spacing: TerminalSpacing.sm) {
            AnomalyPanel(title: "RISK ALERTS", subtitle: "OPERATIONAL WARNINGS", rows: store.anomalyRows)
            SystemContractPanel(title: "SYSTEM CONTRACT", subtitle: "GOVERNANCE", rows: store.contractRows)
                .frame(width: 440)
        }
    }
}

private struct ExecutiveExportPanel: View {
    var body: some View {
        HStack(alignment: .top, spacing: TerminalSpacing.sm) {
            SystemContractPanel(title: "EXPORT DESK", subtitle: "READ MODELS → REPORTS", rows: MockData.contractRows)
            ExecutiveRightColumn()
                .frame(width: 440)
        }
    }
}
