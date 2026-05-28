import SwiftUI

struct InventoryMatrixChart: View {
    let categories: [InventoryCategory]

    var body: some View {
        VStack(alignment: .leading, spacing: TerminalSpacing.sm) {
            Legend()
            GeometryReader { geo in
                let rowHeight: CGFloat = 18
                let gap: CGFloat = 10
                let totalHeight = CGFloat(categories.count) * (rowHeight + gap) - gap

                VStack(alignment: .leading, spacing: gap) {
                    ForEach(categories) { cat in
                        HStack(spacing: 10) {
                            Text(cat.name.uppercased())
                                .font(TerminalType.mono(10, weight: .semibold))
                                .foregroundStyle(TerminalColors.muted)
                                .frame(width: 140, alignment: .leading)

                            StackedBar(segments: cat.segments)
                                .frame(height: rowHeight)

                            Text(percentText(cat))
                                .font(TerminalType.mono(10, weight: .regular))
                                .foregroundStyle(TerminalColors.dim)
                                .frame(width: 72, alignment: .trailing)
                        }
                    }
                }
                .frame(width: geo.size.width, height: totalHeight, alignment: .topLeading)
            }
            .frame(height: CGFloat(categories.count) * 28)
        }
    }

    private func percentText(_ cat: InventoryCategory) -> String {
        let risk = cat.segments.last(where: { $0.label == "RISK" })?.value ?? 0
        return "RISK \(Int(risk * 100))%"
    }
}

private struct StackedBar: View {
    let segments: [InventorySegment]
    @State private var hovering = false

    var body: some View {
        GeometryReader { geo in
            let total = max(segments.reduce(0) { $0 + $1.value }, 0.0001)
            HStack(spacing: 1) {
                ForEach(segments) { seg in
                    Rectangle()
                        .fill(seg.color.opacity(hovering ? 0.95 : 0.85))
                        .frame(width: geo.size.width * CGFloat(seg.value / total))
                }
            }
            .clipShape(RoundedRectangle(cornerRadius: 5, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 5, style: .continuous)
                    .stroke(TerminalColors.border.opacity(0.8), lineWidth: 1)
            )
        }
        .onHover { hovering = $0 }
    }
}

private struct Legend: View {
    var body: some View {
        HStack(spacing: 12) {
            LegendItem(color: TerminalColors.green, text: "HEALTHY")
            LegendItem(color: TerminalColors.cyan, text: "WATCH")
            LegendItem(color: TerminalColors.red, text: "RISK")
            Spacer(minLength: 0)
        }
    }
}

private struct LegendItem: View {
    let color: Color
    let text: String

    var body: some View {
        HStack(spacing: 6) {
            Rectangle().fill(color).frame(width: 10, height: 6).cornerRadius(2)
            Text(text)
                .font(TerminalType.mono(10, weight: .semibold))
                .foregroundStyle(TerminalColors.dim)
        }
    }
}
