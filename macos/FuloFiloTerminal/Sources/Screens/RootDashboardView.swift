import SwiftUI

struct RootDashboardView: View {
    @State private var navSelection: NavItem = .executive
    @State private var tabSelection: TerminalTab = .inventoryMatrix

    var body: some View {
        HStack(spacing: 0) {
            SidebarView(selection: $navSelection)

            VStack(spacing: 0) {
                HeaderStatusView(status: MockData.headerStatus)
                TerminalTabStrip(selection: $tabSelection)

                Divider()
                    .overlay(TerminalColors.border)

                content
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(TerminalColors.bg)
            }
        }
        .background(TerminalColors.bg)
    }

    @ViewBuilder
    private var content: some View {
        switch navSelection {
        case .cashflow:
            CashflowView(selectedTab: $tabSelection)
        default:
            ExecutiveOverviewView(selectedTab: $tabSelection)
        }
    }
}

