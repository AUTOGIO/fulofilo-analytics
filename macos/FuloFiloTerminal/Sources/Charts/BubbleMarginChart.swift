import SwiftUI

struct BubbleMarginChart: View {
    let points: [BubblePoint]
    let category: String?

    var filtered: [BubblePoint] {
        guard let category, category != "Todas" else { return points }
        return points.filter { $0.category == category }
    }

    var body: some View {
        GeometryReader { geo in
            let padL: CGFloat = 54
            let padR: CGFloat = 44
            let padT: CGFloat = 18
            let padB: CGFloat = 46
            let plot = CGRect(x: padL, y: padT, width: geo.size.width - padL - padR, height: geo.size.height - padT - padB)

            let maxVol = max(filtered.map(\.volume).max() ?? 100, 100)
            let maxMargin = max(filtered.map(\.margin).max() ?? 60, 60)
            let minMargin = min(filtered.map(\.margin).min() ?? 0, 0)

            let maxRev = max(filtered.map(\.revenue).max() ?? 1, 1)

            ZStack(alignment: .topLeading) {
                ScatterGrid(plot: plot)
                Quadrants(plot: plot)
                ThresholdLines(plot: plot, volX: volToX(50, plot: plot, maxVol: maxVol), marginY: marginToY(35, plot: plot, minMargin: minMargin, maxMargin: maxMargin))

                ForEach(filtered) { p in
                    Bubble(
                        p: p,
                        plot: plot,
                        x: volToX(p.volume, plot: plot, maxVol: maxVol),
                        y: marginToY(p.margin, plot: plot, minMargin: minMargin, maxMargin: maxMargin),
                        r: bubbleRadius(revenue: p.revenue, maxRev: maxRev)
                    )
                }

                AxisTitles(plot: plot)
                MarginLegend(plot: plot, minMargin: minMargin, maxMargin: maxMargin)
            }
        }
        .frame(minHeight: 420)
    }

    private func volToX(_ v: Double, plot: CGRect, maxVol: Double) -> CGFloat {
        plot.minX + plot.width * CGFloat(min(max(v / maxVol, 0), 1))
    }

    private func marginToY(_ m: Double, plot: CGRect, minMargin: Double, maxMargin: Double) -> CGFloat {
        let denom = max(maxMargin - minMargin, 0.0001)
        let t = (m - minMargin) / denom
        return plot.maxY - plot.height * CGFloat(min(max(t, 0), 1))
    }

    private func bubbleRadius(revenue: Double, maxRev: Double) -> CGFloat {
        let t = sqrt(revenue / maxRev)
        return 7 + 18 * CGFloat(min(max(t, 0), 1))
    }
}

private struct ScatterGrid: View {
    let plot: CGRect

    var body: some View {
        Path { p in
            p.addRect(plot)
            let cols = 5
            let rows = 5
            for i in 1..<cols {
                let x = plot.minX + (plot.width / CGFloat(cols)) * CGFloat(i)
                p.move(to: CGPoint(x: x, y: plot.minY))
                p.addLine(to: CGPoint(x: x, y: plot.maxY))
            }
            for i in 1..<rows {
                let y = plot.minY + (plot.height / CGFloat(rows)) * CGFloat(i)
                p.move(to: CGPoint(x: plot.minX, y: y))
                p.addLine(to: CGPoint(x: plot.maxX, y: y))
            }
        }
        .stroke(TerminalColors.border.opacity(0.55), style: StrokeStyle(lineWidth: 1, dash: [3, 5]))
    }
}

private struct ThresholdLines: View {
    let plot: CGRect
    let volX: CGFloat
    let marginY: CGFloat

    var body: some View {
        Path { p in
            p.move(to: CGPoint(x: plot.minX, y: marginY))
            p.addLine(to: CGPoint(x: plot.maxX, y: marginY))
            p.move(to: CGPoint(x: volX, y: plot.minY))
            p.addLine(to: CGPoint(x: volX, y: plot.maxY))
        }
        .stroke(TerminalColors.amber.opacity(0.8), style: StrokeStyle(lineWidth: 1.25, dash: [8, 6]))
    }
}

private struct Quadrants: View {
    let plot: CGRect

    var body: some View {
        ZStack {
            Text("HIDDEN GEMS")
                .font(TerminalType.mono(10, weight: .semibold))
                .foregroundStyle(TerminalColors.dim)
                .position(x: plot.minX + plot.width * 0.25, y: plot.minY + plot.height * 0.18)
            Text("STARS")
                .font(TerminalType.mono(10, weight: .semibold))
                .foregroundStyle(TerminalColors.dim)
                .position(x: plot.minX + plot.width * 0.75, y: plot.minY + plot.height * 0.18)
            Text("DOGS")
                .font(TerminalType.mono(10, weight: .semibold))
                .foregroundStyle(TerminalColors.dim)
                .position(x: plot.minX + plot.width * 0.25, y: plot.minY + plot.height * 0.85)
            Text("CASH COWS")
                .font(TerminalType.mono(10, weight: .semibold))
                .foregroundStyle(TerminalColors.dim)
                .position(x: plot.minX + plot.width * 0.75, y: plot.minY + plot.height * 0.85)
        }
    }
}

private struct Bubble: View {
    let p: BubblePoint
    let plot: CGRect
    let x: CGFloat
    let y: CGFloat
    let r: CGFloat
    @State private var hovering = false

    var body: some View {
        let c = colorForMargin(p.margin)

        ZStack {
            Circle()
                .fill(c.opacity(hovering ? 0.55 : 0.40))
                .overlay(
                    Circle()
                        .stroke(c.opacity(hovering ? 0.95 : 0.75), lineWidth: hovering ? 2 : 1)
                )
                .frame(width: r * 2, height: r * 2)
                .position(x: x, y: y)

            if hovering {
                VStack(alignment: .leading, spacing: 4) {
                    Text(p.sku.uppercased())
                        .font(TerminalType.mono(10, weight: .bold))
                        .foregroundStyle(TerminalColors.text)
                    Text("VOL \(Int(p.volume))  •  M \(String(format: "%.0f", p.margin))%  •  REV R$ \(Int(p.revenue))".uppercased())
                        .font(TerminalType.mono(9, weight: .regular))
                        .foregroundStyle(TerminalColors.dim)
                }
                .padding(8)
                .background(TerminalColors.panel2)
                .overlay(
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .stroke(TerminalColors.border, lineWidth: 1)
                )
                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                .position(x: min(max(x + 120, plot.minX + 120), plot.maxX - 100), y: max(plot.minY + 24, y - 26))
            }
        }
        .onHover { hovering = $0 }
    }

    private func colorForMargin(_ m: Double) -> Color {
        if m >= 45 { return TerminalColors.green }
        if m >= 35 { return TerminalColors.cyan }
        if m >= 25 { return TerminalColors.amber }
        return TerminalColors.red
    }
}

private struct AxisTitles: View {
    let plot: CGRect

    var body: some View {
        Group {
            Text("MARGEM (%)".uppercased())
                .font(TerminalType.mono(10, weight: .semibold))
                .foregroundStyle(TerminalColors.muted)
                .rotationEffect(.degrees(-90))
                .position(x: 18, y: plot.midY)

            Text("QUANTIDADE VENDIDA".uppercased())
                .font(TerminalType.mono(10, weight: .semibold))
                .foregroundStyle(TerminalColors.muted)
                .position(x: plot.midX, y: plot.maxY + 28)
        }
    }
}

private struct MarginLegend: View {
    let plot: CGRect
    let minMargin: Double
    let maxMargin: Double

    var body: some View {
        VStack(spacing: 8) {
            Text("MARGEM (%)")
                .font(TerminalType.mono(10, weight: .bold))
                .foregroundStyle(TerminalColors.muted)

            LinearGradient(
                colors: [TerminalColors.red, TerminalColors.amber, TerminalColors.cyan, TerminalColors.green],
                startPoint: .bottom,
                endPoint: .top
            )
            .frame(width: 10, height: 160)
            .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 6, style: .continuous)
                    .stroke(TerminalColors.border.opacity(0.8), lineWidth: 1)
            )

            VStack(spacing: 2) {
                Text("\(Int(maxMargin))")
                Text("\(Int((maxMargin + minMargin) / 2))")
                Text("\(Int(minMargin))")
            }
            .font(TerminalType.mono(9, weight: .regular))
            .foregroundStyle(TerminalColors.dim)
        }
        .position(x: plot.maxX + 26, y: plot.midY)
    }
}

