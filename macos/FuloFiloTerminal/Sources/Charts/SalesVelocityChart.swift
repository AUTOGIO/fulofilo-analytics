import SwiftUI

struct SalesVelocityChart: View {
    let points: [SalesPoint]

    var body: some View {
        GeometryReader { geo in
            let padding: CGFloat = 26
            let plot = CGRect(x: padding, y: 16, width: geo.size.width - padding - 44, height: geo.size.height - 56)

            let maxRevenue = max(points.map(\.revenue).max() ?? 1, 1)
            let maxUnits = max(points.map(\.units).max() ?? 1, 1)

            ZStack(alignment: .topLeading) {
                ChartGrid(plot: plot)

                RevenueBars(points: points, plot: plot, maxRevenue: maxRevenue)
                UnitsLine(points: points, plot: plot, maxUnits: maxUnits)

                AxisLabels(points: points, plot: plot)
                UnitsAxis(maxUnits: maxUnits, plot: plot)

                Legend()
                    .position(x: plot.maxX - 65, y: plot.minY + 14)
            }
        }
        .frame(minHeight: 260)
    }
}

private struct ChartGrid: View {
    let plot: CGRect

    var body: some View {
        Path { p in
            p.addRect(plot)
            let rows = 4
            for i in 1..<rows {
                let y = plot.minY + (plot.height / CGFloat(rows)) * CGFloat(i)
                p.move(to: CGPoint(x: plot.minX, y: y))
                p.addLine(to: CGPoint(x: plot.maxX, y: y))
            }
        }
        .stroke(TerminalColors.border.opacity(0.7), style: StrokeStyle(lineWidth: 1, dash: [4, 4]))
    }
}

private struct RevenueBars: View {
    let points: [SalesPoint]
    let plot: CGRect
    let maxRevenue: Double

    var body: some View {
        let count = max(points.count, 1)
        let step = plot.width / CGFloat(count)
        let barWidth = step * 0.55

        ForEach(Array(points.enumerated()), id: \.offset) { idx, pt in
            let x = plot.minX + step * CGFloat(idx) + (step - barWidth) / 2
            let h = plot.height * CGFloat(pt.revenue / maxRevenue)
            let y = plot.maxY - h
            RoundedRectangle(cornerRadius: 3, style: .continuous)
                .fill(TerminalColors.green.opacity(0.85))
                .frame(width: barWidth, height: h)
                .position(x: x + barWidth / 2, y: y + h / 2)
        }
    }
}

private struct UnitsLine: View {
    let points: [SalesPoint]
    let plot: CGRect
    let maxUnits: Double

    var body: some View {
        let count = max(points.count, 1)
        let step = plot.width / CGFloat(count)

        Path { p in
            for (idx, pt) in points.enumerated() {
                let x = plot.minX + step * CGFloat(idx) + step / 2
                let y = plot.maxY - plot.height * CGFloat(pt.units / maxUnits)
                if idx == 0 { p.move(to: CGPoint(x: x, y: y)) }
                else { p.addLine(to: CGPoint(x: x, y: y)) }
            }
        }
        .stroke(TerminalColors.cyan, lineWidth: 2)

        ForEach(Array(points.enumerated()), id: \.offset) { idx, pt in
            let x = plot.minX + step * CGFloat(idx) + step / 2
            let y = plot.maxY - plot.height * CGFloat(pt.units / maxUnits)
            Circle()
                .fill(TerminalColors.cyan)
                .frame(width: 6, height: 6)
                .position(x: x, y: y)
        }
    }
}

private struct AxisLabels: View {
    let points: [SalesPoint]
    let plot: CGRect

    var body: some View {
        let count = max(points.count, 1)
        let step = plot.width / CGFloat(count)
        ForEach(Array(points.enumerated()), id: \.offset) { idx, pt in
            let x = plot.minX + step * CGFloat(idx) + step / 2
            Text(pt.label.uppercased())
                .font(TerminalType.mono(9, weight: .regular))
                .foregroundStyle(TerminalColors.dim)
                .position(x: x, y: plot.maxY + 18)
        }
    }
}

private struct UnitsAxis: View {
    let maxUnits: Double
    let plot: CGRect

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("\(Int(maxUnits))")
            Spacer()
            Text("\(Int(maxUnits * 0.66))")
            Spacer()
            Text("\(Int(maxUnits * 0.33))")
            Spacer()
            Text("0")
        }
        .font(TerminalType.mono(9, weight: .regular))
        .foregroundStyle(TerminalColors.dim)
        .frame(height: plot.height)
        .position(x: plot.maxX + 22, y: plot.midY)
    }
}

private struct Legend: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 8) {
                Rectangle().fill(TerminalColors.green).frame(width: 10, height: 6).cornerRadius(2)
                Text("REVENUE")
                    .font(TerminalType.mono(10, weight: .semibold))
                    .foregroundStyle(TerminalColors.dim)
            }
            HStack(spacing: 8) {
                Rectangle().fill(TerminalColors.cyan).frame(width: 10, height: 2).cornerRadius(2)
                Text("UNITS")
                    .font(TerminalType.mono(10, weight: .semibold))
                    .foregroundStyle(TerminalColors.dim)
            }
        }
        .padding(8)
        .background(TerminalColors.panel.opacity(0.85))
        .overlay(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .stroke(TerminalColors.border.opacity(0.8), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
    }
}

