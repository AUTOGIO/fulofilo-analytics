import SwiftUI

struct ProductionSpecsView: View {
    @ObservedObject var vm: ProjectViewModel
    @State private var expanded = true

    var body: some View {
        GroupBox {
            VStack(alignment: .leading, spacing: 0) {
                // Header toggle
                HStack {
                    Button {
                        withAnimation(.easeInOut(duration: 0.15)) { expanded.toggle() }
                    } label: {
                        HStack(spacing: 6) {
                            Label("3. Production Specs", systemImage: "ruler")
                                .font(.headline.weight(.semibold))
                            Image(systemName: expanded ? "chevron.up" : "chevron.down")
                                .foregroundStyle(.secondary)
                                .font(.caption)
                        }
                    }
                    .buttonStyle(.plain)

                    Spacer()

                    Button {
                        vm.applyProductionDefaults()
                    } label: {
                        Label("Apply Defaults", systemImage: "wand.and.stars")
                            .font(.caption2)
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.mini)
                    .help("Reset to industry-standard specs for this product type and material")
                }
                .padding(.bottom, expanded ? 10 : 0)

                if expanded {
                    VStack(alignment: .leading, spacing: 14) {
                        dimensionsSection
                        Divider()
                        hardwareSection
                        Divider()
                        orderSection
                    }
                }
            }
            .padding(8)
        }
    }

    // MARK: - Dimensions

    private var dimensionsSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            sectionLabel("Product Dimensions (cm)")
            HStack(spacing: 8) {
                cmField("W", value: $vm.specsWidthCM)
                cmField("H", value: $vm.specsHeightCM)
                cmField("D", value: $vm.specsDepthCM)
            }

            sectionLabel("Print Area (cm)")
            HStack(spacing: 8) {
                cmField("W", value: $vm.specsPrintWidthCM)
                cmField("H", value: $vm.specsPrintHeightCM)
                HStack(spacing: 4) {
                    Text("DPI").font(.caption).foregroundStyle(.secondary)
                    Picker("", selection: $vm.specsTargetDPI) {
                        Text("150").tag(150)
                        Text("300").tag(300)
                    }
                    .frame(width: 70)
                }
            }

            if vm.specsPrintWidthCM > 0 && vm.specsPrintHeightCM > 0 {
                let pxW = Int((vm.specsPrintWidthCM / 2.54) * Double(vm.specsTargetDPI))
                let pxH = Int((vm.specsPrintHeightCM / 2.54) * Double(vm.specsTargetDPI))
                Text("→ \(pxW) × \(pxH) px at \(vm.specsTargetDPI) DPI")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }

            sectionLabel("Seam Allowance")
            TextField("e.g. 1 cm overlock", text: $vm.specsSeam)
                .textFieldStyle(.roundedBorder)
                .font(.caption)

            sectionLabel("Lining")
            HStack(spacing: 8) {
                TextField("Color", text: $vm.specsLiningColor).textFieldStyle(.roundedBorder).font(.caption)
                TextField("Material", text: $vm.specsLiningMaterial).textFieldStyle(.roundedBorder).font(.caption)
            }
        }
    }

    // MARK: - Hardware

    private var hardwareSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            sectionLabel("Zipper")
            HStack(spacing: 8) {
                TextField("Color", text: $vm.specsZipperColor).textFieldStyle(.roundedBorder).font(.caption)
                TextField("Type (e.g. YKK #5)", text: $vm.specsZipperType).textFieldStyle(.roundedBorder).font(.caption)
                cmField("L", value: $vm.specsZipperLengthCM)
            }

            sectionLabel("Strap / Handle")
            HStack(spacing: 8) {
                TextField("Material", text: $vm.specsStrapMaterial).textFieldStyle(.roundedBorder).font(.caption)
                cmField("W", value: $vm.specsStrapWidthCM)
                cmField("L", value: $vm.specsStrapLengthCM)
            }
        }
    }

    // MARK: - Order

    private var orderSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            sectionLabel("Target Quantity")
            TextField("e.g. 100", value: $vm.specsTargetQty, format: .number)
                .textFieldStyle(.roundedBorder)
                .font(.caption)
                .frame(width: 120)
        }
    }

    // MARK: - Helpers

    private func sectionLabel(_ text: String) -> some View {
        Text(text).font(.caption.bold()).foregroundStyle(.secondary)
    }

    private func cmField(_ label: String, value: Binding<Double>) -> some View {
        HStack(spacing: 3) {
            Text(label).font(.caption2).foregroundStyle(.tertiary).frame(width: 12)
            TextField("0", value: value, format: .number)
                .textFieldStyle(.roundedBorder)
                .font(.caption)
                .frame(width: 60)
        }
    }
}
