import SwiftUI

struct RootDashboardView: View {
    @State private var navSelection: NavItem = .executive
    @State private var tabSelection: TerminalTab = .inventoryMatrix
    @State private var store = TerminalStore()

    var body: some View {
        HStack(spacing: 0) {
            SidebarView(selection: $navSelection)
                .environment(store)

            VStack(spacing: 0) {
                HeaderStatusView(status: store.headerStatus)
                    .environment(store)
                TerminalTabStrip(selection: $tabSelection)

                Divider()
                    .overlay(TerminalColors.border)

                content
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(TerminalColors.bg)
            }
        }
        .background(TerminalColors.bg)
        .task {
            await store.refreshReadModel()
        }
        .onChange(of: navSelection) { _, newValue in
            if newValue == .cashflow {
                tabSelection = .cashflowOps
            }
        }
    }

    @ViewBuilder
    private var content: some View {
        switch navSelection {
        case .inventory:
            InventoryIntelligenceScreen()
                .environment(store)
        case .sales:
            SalesAnalyticsScreen()
                .environment(store)
        case .cashflow:
            CashflowView(selectedTab: $tabSelection)
                .environment(store)
        case .alerts:
            AlertsScreen()
                .environment(store)
        case .health:
            SystemHealthScreen()
                .environment(store)
        case .reports:
            TerminalPlaceholderScreen(title: "REPORTS", subtitle: "EXPORT DESK", accent: TerminalColors.violet, bodyText: "GENERATE REPORTS FROM READ MODELS (EXCEL/PDF) — LOCAL-FIRST.")
                .environment(store)
        case .ai:
            TerminalPlaceholderScreen(title: "AI INSIGHTS", subtitle: "RULES ENGINE + WATCH", accent: TerminalColors.cyan, bodyText: "INSIGHTS ARE CURRENTLY GENERATED FROM READ MODEL HEURISTICS; ADD RULE SETS AS NEEDED.")
                .environment(store)
        case .dailyOps:
            TerminalPlaceholderScreen(title: "DAILY OPERATIONS", subtitle: "OPERATOR CONSOLE", accent: TerminalColors.blue, bodyText: "USE COMMAND WINDOW: SYNC • SKU • ALERT.")
                .environment(store)
        case .category:
            CategoryIntelligenceScreen()
                .environment(store)
        case .executive:
            ExecutiveOverviewView(selectedTab: $tabSelection)
                .environment(store)
        }
    }
}
