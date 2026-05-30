import SwiftUI

struct ExecutiveOverviewView: View {
    @Binding var selectedTab: TerminalTab

    private let columns = [
        GridItem(.flexible(minimum: 180), spacing: TerminalSpacing.sm),
        GridItem(.flexible(minimum: 180), spacing: TerminalSpacing.sm),
        GridItem(.flexible(minimum: 180), spacing: TerminalSpacing.sm),
        GridItem(.flexible(minimum: 180), spacing: TerminalSpacing.sm)
    ]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: TerminalSpacing.sm) {
                SectionPanel(
                    title: "EXECUTIVE KPI CLUSTER",
                    subtitle: "FINANCIAL + OPERATIONAL CONTROL",
                    accent: TerminalColors.amber
                ) {
                    LazyVGrid(columns: columns, alignment: .leading, spacing: TerminalSpacing.sm) {
                        ForEach(MockData.executiveKPIs) { kpi in
                            KPICard(kpi: kpi)
                        }
                    }
                }

                HStack(alignment: .top, spacing: TerminalSpacing.sm) {
                    VStack(alignment: .leading, spacing: TerminalSpacing.sm) {
                        SectionPanel(
                            title: "INVENTORY INTELLIGENCE",
                            subtitle: "STOCK HEALTH MATRIX",
                            accent: TerminalColors.cyan
                        ) {
                            InventoryMatrixChart(categories: MockData.inventoryMatrix)
                                .frame(maxWidth: .infinity)
                        }

                        SectionPanel(
                            title: "SALES INTELLIGENCE",
                            subtitle: "VELOCITY + DEMAND TREND",
                            accent: TerminalColors.green
                        ) {
                            SalesVelocityChart(points: MockData.salesSeries)
                                .frame(maxWidth: .infinity)
                        }
                    }

                    VStack(alignment: .leading, spacing: TerminalSpacing.sm) {
                        InsightPanel(
                            title: "AI RETAIL INSIGHTS",
                            subtitle: "ASSISTANT WATCHLIST",
                            rows: MockData.insights
                        )

                        AnomalyPanel(
                            title: "OPERATIONAL ANOMALIES",
                            subtitle: "RISK WARNINGS",
                            rows: MockData.anomalies
                        )

                        SystemContractPanel(
                            title: "SYSTEM CONTRACT",
                            subtitle: "EXCEL-FIRST ARCHITECTURE",
                            rows: MockData.contractRows
                        )
                    }
                    .frame(width: 420)
                }
            }
            .padding(TerminalSpacing.sm)
        }
        .background(TerminalColors.bg)
    }
}

