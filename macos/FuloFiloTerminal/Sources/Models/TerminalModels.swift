import SwiftUI

enum NavItem: String, CaseIterable, Identifiable {
    case executive = "EX Executive Overview"
    case inventory = "IN Inventory Intelligence"
    case dailyOps = "DO Daily Operations"
    case sales = "SA Sales Analytics"
    case cashflow = "CF Cashflow"
    case category = "CI Category Intelligence"
    case reports = "RP Reports"
    case ai = "AI AI Insights"
    case alerts = "AL Alerts"
    case health = "SH System Health"

    var id: String { rawValue }

    var shortCode: String {
        rawValue.prefix(2).uppercased()
    }

    var title: String {
        String(rawValue.dropFirst(3))
    }
}

enum TerminalTab: String, CaseIterable, Identifiable {
    case inventoryMatrix = "01) INVENTORY MATRIX"
    case cashflowOps = "02) CASHFLOW OPS"
    case salesVelocity = "03) SALES VELOCITY"
    case reorderActions = "04) REORDER ACTIONS"
    case riskAlerts = "05) RISK ALERTS"
    case exportDesk = "06) EXPORT DESK"

    var id: String { rawValue }

    var accent: Color {
        switch self {
        case .inventoryMatrix: return TerminalColors.cyan
        case .cashflowOps: return TerminalColors.amber
        case .salesVelocity: return TerminalColors.green
        case .reorderActions: return TerminalColors.blue
        case .riskAlerts: return TerminalColors.red
        case .exportDesk: return TerminalColors.violet
        }
    }
}

struct KPI: Identifiable {
    let id = UUID()
    let title: String
    let value: String
    let subtitle: String
    let accent: Color
}

struct StatusMetric: Identifiable {
    let id = UUID()
    let title: String
    let value: String
    let subtitle: String
    let accent: Color
}

struct Insight: Identifiable {
    let id = UUID()
    let code: String
    let text: String
    let detail: String
    let accent: Color
}

struct Anomaly: Identifiable {
    let id = UUID()
    let code: String
    let kind: String
    let text: String
    let accent: Color
}

struct InventoryCategory: Identifiable {
    let id = UUID()
    let name: String
    let segments: [InventorySegment]
}

struct InventorySegment: Identifiable {
    let id = UUID()
    let label: String
    let value: Double
    let color: Color
}

struct SalesPoint: Identifiable {
    let id = UUID()
    let label: String
    let revenue: Double
    let units: Double
}

struct BubblePoint: Identifiable {
    let id = UUID()
    let sku: String
    let category: String
    let volume: Double
    let margin: Double
    let revenue: Double
}

