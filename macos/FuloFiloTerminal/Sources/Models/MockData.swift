import SwiftUI

enum MockData {
    static let executiveKPIs: [KPI] = [
        KPI(title: "REVENUE", value: "R$ 178,079", subtitle: "gross sales intelligence", accent: TerminalColors.green),
        KPI(title: "MARGIN", value: "57.7%", subtitle: "R$ 102,825", accent: TerminalColors.amber),
        KPI(title: "INVENTORY TURNOVER", value: "0.89x", subtitle: "sales / live stock", accent: TerminalColors.cyan),
        KPI(title: "SELL-THROUGH", value: "41.9%", subtitle: "units sold vs available", accent: TerminalColors.blue),
        KPI(title: "AVG TICKET", value: "R$ 31.71", subtitle: "5,616 units", accent: TerminalColors.green),
        KPI(title: "LOW STOCK ALERTS", value: "0", subtitle: "1 critical", accent: TerminalColors.red),
        KPI(title: "OPS EFFICIENCY", value: "93/100", subtitle: "ready", accent: TerminalColors.cyan),
        KPI(title: "FIXED BURN", value: "7.3%", subtitle: "R$ 12,950", accent: TerminalColors.orange)
    ]

    static let headerStatus: [StatusMetric] = [
        StatusMetric(title: "DAILY REVENUE", value: "R$ 178,079", subtitle: "selected operating window", accent: TerminalColors.green),
        StatusMetric(title: "CASHFLOW STATUS", value: "R$ -25,900", subtitle: "in R$ 0 / out R$ 25,900", accent: TerminalColors.red),
        StatusMetric(title: "INVENTORY VALUATION", value: "R$ 185,407", subtitle: "72 active SKUs", accent: TerminalColors.cyan),
        StatusMetric(title: "OPERATIONAL HEALTH", value: "93/100", subtitle: "READY", accent: TerminalColors.green),
        StatusMetric(title: "SYNC STATUS", value: "SYNCED", subtitle: "2026-05-28 09:41", accent: TerminalColors.green),
        StatusMetric(title: "AI ASSISTANT", value: "WATCH", subtitle: "rules engine online", accent: TerminalColors.cyan)
    ]

    static let inventoryMatrix: [InventoryCategory] = [
        InventoryCategory(
            name: "Bolsas",
            segments: [
                .init(label: "HEALTHY", value: 0.46, color: TerminalColors.green),
                .init(label: "WATCH", value: 0.28, color: TerminalColors.cyan),
                .init(label: "RISK", value: 0.26, color: TerminalColors.red)
            ]
        ),
        InventoryCategory(
            name: "Cangas em Algodão",
            segments: [
                .init(label: "HEALTHY", value: 0.62, color: TerminalColors.green),
                .init(label: "WATCH", value: 0.22, color: TerminalColors.cyan),
                .init(label: "RISK", value: 0.16, color: TerminalColors.red)
            ]
        ),
        InventoryCategory(
            name: "Cangas em Elastano",
            segments: [
                .init(label: "HEALTHY", value: 0.38, color: TerminalColors.green),
                .init(label: "WATCH", value: 0.41, color: TerminalColors.cyan),
                .init(label: "RISK", value: 0.21, color: TerminalColors.red)
            ]
        ),
        InventoryCategory(
            name: "Outros",
            segments: [
                .init(label: "HEALTHY", value: 0.52, color: TerminalColors.green),
                .init(label: "WATCH", value: 0.30, color: TerminalColors.cyan),
                .init(label: "RISK", value: 0.18, color: TerminalColors.red)
            ]
        ),
        InventoryCategory(
            name: "Roupas",
            segments: [
                .init(label: "HEALTHY", value: 0.44, color: TerminalColors.green),
                .init(label: "WATCH", value: 0.36, color: TerminalColors.cyan),
                .init(label: "RISK", value: 0.20, color: TerminalColors.red)
            ]
        ),
        InventoryCategory(
            name: "Sem categoria",
            segments: [
                .init(label: "HEALTHY", value: 0.33, color: TerminalColors.green),
                .init(label: "WATCH", value: 0.39, color: TerminalColors.cyan),
                .init(label: "RISK", value: 0.28, color: TerminalColors.red)
            ]
        )
    ]

    static let salesSeries: [SalesPoint] = [
        .init(label: "Feb 2026", revenue: 82_000, units: 2100),
        .init(label: "Mar 8", revenue: 102_500, units: 2800),
        .init(label: "Mar 22", revenue: 94_800, units: 2550),
        .init(label: "Apr 5", revenue: 121_400, units: 3100),
        .init(label: "Apr 19", revenue: 112_700, units: 2950),
        .init(label: "May 3", revenue: 138_900, units: 3420)
    ]

    static let insights: [Insight] = [
        .init(code: "RESTOC", text: "Chaveirô Imã 10", detail: "5 days remaining. Suggested buy K units.", accent: TerminalColors.amber),
        .init(code: "RESTOC", text: "Regional adulto", detail: "9 days remaining. Suggested buy 571 units.", accent: TerminalColors.amber),
        .init(code: "RESTOC", text: "Placa", detail: "11 days remaining. Suggested buy 445 units.", accent: TerminalColors.amber),
        .init(code: "RESTOC", text: "Necessaire", detail: "12 days remaining. Suggested buy 397 units.", accent: TerminalColors.amber)
    ]

    static let anomalies: [Anomaly] = [
        .init(code: "SKU", kind: "RISK", text: "1 critical SKUs require immediate attention.", accent: TerminalColors.red),
        .init(code: "INV", kind: "SLOW", text: "44 slow-moving SKUs on overstock watch.", accent: TerminalColors.amber),
        .init(code: "SRC", kind: "DATA", text: "Reliability state: READY. Source health governs executive confidence.", accent: TerminalColors.green),
        .init(code: "CF", kind: "CASH", text: "Runway signal NEG at R$ -25,900 net.", accent: TerminalColors.red)
    ]

    static let contractRows: [(String, String)] = [
        ("CANONICAL WRITE", "data/excel/FuloFilo_Master.xlsx"),
        ("SYNC PATH", "bash scripts/sync_excel.sh"),
        ("READ MODELS", "parquet + DuckDB + reports"),
        ("POLICY", "generated layers remain reproducible and read-only")
    ]

    static let bubblePoints: [BubblePoint] = [
        .init(sku: "CANGA-A01", category: "Cangas", volume: 22, margin: 18, revenue: 4_800),
        .init(sku: "CANGA-E04", category: "Cangas", volume: 64, margin: 42, revenue: 13_100),
        .init(sku: "BOLSA-021", category: "Bolsas", volume: 85, margin: 52, revenue: 19_700),
        .init(sku: "ROUPA-110", category: "Roupas", volume: 41, margin: 33, revenue: 8_900),
        .init(sku: "OUT-505", category: "Outros", volume: 12, margin: 61, revenue: 3_200),
        .init(sku: "BOLSA-019", category: "Bolsas", volume: 55, margin: 29, revenue: 11_400),
        .init(sku: "ROUPA-072", category: "Roupas", volume: 98, margin: 39, revenue: 22_300),
        .init(sku: "CANGA-A11", category: "Cangas", volume: 47, margin: 36, revenue: 9_400),
        .init(sku: "OUT-208", category: "Outros", volume: 73, margin: 14, revenue: 6_700),
        .init(sku: "NEC-009", category: "Acessórios", volume: 58, margin: 48, revenue: 12_600)
    ]
}
