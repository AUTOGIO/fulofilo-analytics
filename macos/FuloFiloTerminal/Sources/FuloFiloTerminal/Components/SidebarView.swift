import SwiftUI

struct SidebarView: View {
    @Binding var selection: NavItem
    @Environment(TerminalStore.self) private var store
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

            AutomationControls()

            RedeDownloads()

            Spacer(minLength: 0)

            VStack(alignment: .leading, spacing: 6) {
                Text("RUNTIME")
                    .font(TerminalType.label(10, weight: .bold))
                    .foregroundStyle(TerminalColors.muted)
                HStack(spacing: 8) {
                    Circle().fill(TerminalColors.green).frame(width: 7, height: 7)
                    Text(store.readModelState.uppercased())
                        .font(TerminalType.mono(10))
                        .foregroundStyle(TerminalColors.dim)
                }
                if let msg = store.lastActionMessage, !msg.isEmpty {
                    Text(msg.uppercased())
                        .font(TerminalType.mono(9, weight: .regular))
                        .foregroundStyle(TerminalColors.muted)
                        .lineLimit(3)
                }
                if let err = store.lastSyncError, !err.isEmpty {
                    Text("LAST ERROR: \(err)".uppercased())
                        .font(TerminalType.mono(9, weight: .regular))
                        .foregroundStyle(TerminalColors.red.opacity(0.9))
                        .lineLimit(3)
                }
            }
            .terminalPanel()
        }
        .padding(TerminalSpacing.sm)
        .frame(minWidth: 292, maxWidth: 292, maxHeight: .infinity, alignment: .topLeading)
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
    @Environment(TerminalStore.self) private var store
    @State private var hovering = false

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("COMMAND")
                .font(TerminalType.label(10, weight: .bold))
                .foregroundStyle(TerminalColors.muted)
            TextField("SYNC, SKU, ALERT, RI", text: Bindable(store).commandText)
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
                .onSubmit {
                    Task {
                        let cmd = store.commandText
                        store.commandText = ""
                        await store.runCommand(cmd)
                    }
                }
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

private struct AutomationControls: View {
    @Environment(TerminalStore.self) private var store

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("AUTOMATION CONTROLS")
                .font(TerminalType.label(10, weight: .bold))
                .foregroundStyle(TerminalColors.muted)
            Text("Use a rotina automática após atualizar vendas e dados operacionais na planilha Excel.".uppercased())
                .font(TerminalType.mono(9, weight: .regular))
                .foregroundStyle(TerminalColors.dim)
                .lineLimit(3)

            Button {
                Task { await store.runDailyAutomation() }
            } label: {
                Text("EXECUTAR ROTINA AUTOMÁTICA")
                    .font(TerminalType.mono(11, weight: .bold))
                    .foregroundStyle(Color.black.opacity(0.85))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .background(TerminalColors.green)
                    .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
            }
            .buttonStyle(.plain)

            Button {
                Task { await store.runValidate(skipTests: false) }
            } label: {
                Text("✓ VALIDAR DADOS")
                    .font(TerminalType.mono(11, weight: .bold))
                    .foregroundStyle(TerminalColors.text)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .background(TerminalColors.panel2.opacity(0.65))
                    .overlay(
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .stroke(TerminalColors.border, lineWidth: 1)
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
            }
            .buttonStyle(.plain)

            Button {
                Task { await store.runValidate(skipTests: true) }
            } label: {
                Text("✓ VALIDAR (FAST)")
                    .font(TerminalType.mono(10, weight: .semibold))
                    .foregroundStyle(TerminalColors.muted)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 9)
                    .background(TerminalColors.panel.opacity(0.35))
                    .overlay(
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .stroke(TerminalColors.border.opacity(0.7), lineWidth: 1)
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
            }
            .buttonStyle(.plain)
        }
        .terminalPanel()
    }
}

private struct RedeDownloads: View {
    @Environment(TerminalStore.self) private var store
    @State private var targetDate: Date = Date()
    @State private var endDate: Date = Date()
    @State private var mode: String = "day"
    @State private var format: String = "csv"
    @State private var force: Bool = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("REDE DOWNLOADS")
                .font(TerminalType.label(10, weight: .bold))
                .foregroundStyle(TerminalColors.muted)
            Text("Baixa Loyverse, importa no Excel master e atualiza dashboard/app.".uppercased())
                .font(TerminalType.mono(9, weight: .regular))
                .foregroundStyle(TerminalColors.dim)
                .lineLimit(3)

            Picker("", selection: $mode) {
                Text("UM DIA").tag("day")
                Text("PERÍODO").tag("period")
            }
            .pickerStyle(.segmented)
            .tint(TerminalColors.cyan)

            VStack(alignment: .leading, spacing: 6) {
                Text(mode == "day" ? "DIA REDE" : "DE")
                    .font(TerminalType.label(10, weight: .bold))
                    .foregroundStyle(TerminalColors.muted)
                DatePicker("", selection: $targetDate, displayedComponents: [.date])
                    .labelsHidden()
                    .datePickerStyle(.field)
                    .font(TerminalType.mono(12, weight: .semibold))
                    .tint(TerminalColors.cyan)
            }

            if mode == "period" {
                VStack(alignment: .leading, spacing: 6) {
                    Text("ATÉ")
                        .font(TerminalType.label(10, weight: .bold))
                        .foregroundStyle(TerminalColors.muted)
                    DatePicker("", selection: $endDate, displayedComponents: [.date])
                        .labelsHidden()
                        .datePickerStyle(.field)
                        .font(TerminalType.mono(12, weight: .semibold))
                        .tint(TerminalColors.cyan)
                }
            }

            VStack(alignment: .leading, spacing: 6) {
                Text("FORMATO")
                    .font(TerminalType.label(10, weight: .bold))
                    .foregroundStyle(TerminalColors.muted)
                FormatChips(selection: $format)
            }

            Toggle("FORÇAR NOVO DOWNLOAD", isOn: $force)
                .font(TerminalType.mono(9, weight: .semibold))
                .foregroundStyle(TerminalColors.muted)
                .toggleStyle(.checkbox)

            if let message = store.lastActionMessage, !message.isEmpty {
                Text(message.uppercased())
                    .font(TerminalType.mono(9, weight: .regular))
                    .foregroundStyle(TerminalColors.green)
                    .lineLimit(4)
            }

            Button {
                Task { await store.launchRedeDownload(mode: mode, targetDate: targetDate, endDate: endDate, format: format, force: force) }
            } label: {
                Text("BAIXAR + IMPORTAR VENDAS")
                    .font(TerminalType.mono(11, weight: .bold))
                    .foregroundStyle(TerminalColors.text)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .background(TerminalColors.panel2.opacity(0.65))
                    .overlay(
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .stroke(TerminalColors.border, lineWidth: 1)
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
            }
            .buttonStyle(.plain)
        }
        .terminalPanel()
    }
}

private struct FormatChips: View {
    @Binding var selection: String
    private let all = ["csv", "xlsx", "pdf"]

    var body: some View {
        HStack(spacing: 8) {
            ForEach(all, id: \.self) { fmt in
                let selected = selection == fmt
                Button {
                    selection = fmt
                } label: {
                    HStack(spacing: 6) {
                        Text(fmt.uppercased())
                            .font(TerminalType.mono(10, weight: .bold))
                    }
                    .foregroundStyle(selected ? Color.black.opacity(0.85) : TerminalColors.text)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 8)
                    .background(selected ? TerminalColors.green : TerminalColors.panel.opacity(0.35))
                    .overlay(
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .stroke(TerminalColors.border.opacity(selected ? 0.0 : 0.7), lineWidth: 1)
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                }
                .buttonStyle(.plain)
            }
            Spacer(minLength: 0)
        }
    }
}
