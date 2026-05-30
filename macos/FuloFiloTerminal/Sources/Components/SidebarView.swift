import SwiftUI

struct SidebarView: View {
    @Binding var selection: NavItem
    @State private var hoverItem: NavItem?

    var body: some View {
        VStack(alignment: .leading, spacing: TerminalSpacing.sm) {
            HStack(spacing: TerminalSpacing.sm) {
                ZStack {
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .fill(TerminalColors.panel2)
                        .overlay(
                            RoundedRectangle(cornerRadius: 8, style: .continuous)
                                .stroke(TerminalColors.border, lineWidth: 1)
                        )
                    Text("FF")
                        .font(TerminalType.mono(12, weight: .bold))
                        .foregroundStyle(TerminalColors.amber)
                }
                .frame(width: 34, height: 34)

                VStack(alignment: .leading, spacing: 2) {
                    Text("COMMAND WINDOW")
                        .font(TerminalType.label(10, weight: .bold))
                        .foregroundStyle(TerminalColors.muted)
                    Text("SYNC, SKU, ALERT, RI")
                        .font(TerminalType.mono(10, weight: .regular))
                        .foregroundStyle(TerminalColors.dim)
                }
                Spacer(minLength: 0)
            }
            .padding(.top, TerminalSpacing.xs)

            CommandField()

            PeriodFilterBlock()

            VStack(alignment: .leading, spacing: TerminalSpacing.xs) {
                Text("OPERATIONAL NAVIGATION")
                    .font(TerminalType.label(10, weight: .bold))
                    .foregroundStyle(TerminalColors.amber)
                    .padding(.top, TerminalSpacing.xs)

                ForEach(NavItem.allCases) { item in
                    NavRow(
                        item: item,
                        isSelected: item == selection,
                        isHover: hoverItem == item
                    )
                    .onTapGesture { selection = item }
                    .onHover { isHovering in
                        hoverItem = isHovering ? item : nil
                    }
                }
            }

            Spacer(minLength: 0)

            VStack(alignment: .leading, spacing: 6) {
                Text("RUNTIME")
                    .font(TerminalType.label(10, weight: .bold))
                    .foregroundStyle(TerminalColors.muted)
                HStack(spacing: 8) {
                    Circle().fill(TerminalColors.green).frame(width: 7, height: 7)
                    Text("LOCAL MOCK MODE")
                        .font(TerminalType.mono(10))
                        .foregroundStyle(TerminalColors.dim)
                }
            }
            .terminalPanel()
        }
        .padding(TerminalSpacing.sm)
        .frame(minWidth: 280, maxWidth: 280, maxHeight: .infinity, alignment: .topLeading)
        .background(TerminalColors.bg)
        .overlay(
            Rectangle()
                .fill(TerminalColors.border.opacity(0.8))
                .frame(width: 1),
            alignment: .trailing
        )
    }
}

private struct CommandField: View {
    @State private var text = ""
    @State private var hovering = false

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("COMMAND")
                .font(TerminalType.label(10, weight: .bold))
                .foregroundStyle(TerminalColors.muted)
            TextField("SYNC, SKU, ALERT, RI", text: $text)
                .textFieldStyle(.plain)
                .font(TerminalType.mono(12))
                .foregroundStyle(TerminalColors.text)
                .padding(.horizontal, 10)
                .padding(.vertical, 10)
                .background(hovering ? TerminalColors.panel2 : TerminalColors.panel)
                .overlay(
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .stroke(TerminalColors.border, lineWidth: 1)
                )
                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                .onHover { hovering = $0 }
        }
    }
}

private struct PeriodFilterBlock: View {
    @State private var selection = "Last 30d"
    private let options = ["Today", "Last 7d", "Last 30d", "YTD", "Custom"]

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("PERIOD FILTER")
                .font(TerminalType.label(10, weight: .bold))
                .foregroundStyle(TerminalColors.amber)
            Picker("", selection: $selection) {
                ForEach(options, id: \.self) { o in
                    Text(o.uppercased()).tag(o)
                }
            }
            .pickerStyle(.menu)
            .font(TerminalType.mono(11))
            .tint(TerminalColors.cyan)

            HStack(spacing: 8) {
                Text("WINDOW:")
                    .font(TerminalType.mono(10, weight: .regular))
                    .foregroundStyle(TerminalColors.dim)
                Text(selection.uppercased())
                    .font(TerminalType.mono(10, weight: .semibold))
                    .foregroundStyle(TerminalColors.text)
                Spacer()
            }
        }
        .terminalPanel()
    }
}

private struct NavRow: View {
    let item: NavItem
    let isSelected: Bool
    let isHover: Bool

    var body: some View {
        HStack(spacing: 10) {
            Text(item.shortCode)
                .font(TerminalType.mono(11, weight: .bold))
                .foregroundStyle(isSelected ? TerminalColors.cyan : TerminalColors.dim)
                .frame(width: 24, alignment: .leading)

            Text(item.title.uppercased())
                .font(TerminalType.mono(11, weight: .semibold))
                .foregroundStyle(TerminalColors.text)

            Spacer(minLength: 0)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 10)
        .background(background)
        .overlay(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .stroke(isSelected ? TerminalColors.cyan.opacity(0.55) : TerminalColors.border.opacity(0.0), lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
    }

    private var background: Color {
        if isSelected { return TerminalColors.panel2 }
        if isHover { return TerminalColors.panel2.opacity(0.75) }
        return Color.clear
    }
}

