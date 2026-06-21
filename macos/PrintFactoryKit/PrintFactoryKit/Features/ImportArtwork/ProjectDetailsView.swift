import SwiftUI

struct ProjectDetailsView: View {
    @ObservedObject var vm: ProjectViewModel

    var body: some View {
        GroupBox("2. Project Details") {
            VStack(alignment: .leading, spacing: 10) {
                smartFillButton

                field("Project Name *", text: $vm.projectName, placeholder: "e.g. Caju Cacto")
                field("Collection Name", text: $vm.collectionName, placeholder: "e.g. Summer 2026")
                field("Factory Name", text: $vm.factoryName, placeholder: "Optional")

                picker("Product Type *", selection: $vm.productType, items: ProductType.allCases)
                    .onChange(of: vm.productType) { vm.applyProductionDefaults() }
                picker("Material *", selection: $vm.material, items: Material.allCases)
                    .onChange(of: vm.material) { vm.applyProductionDefaults() }
                picker("Print Method *", selection: $vm.printMethod, items: PrintMethod.allCases)

                VStack(alignment: .leading, spacing: 4) {
                    Text("Notes").font(.caption).foregroundStyle(.secondary)
                    TextEditor(text: $vm.notes)
                        .font(.body)
                        .frame(height: 60)
                        .overlay(RoundedRectangle(cornerRadius: 6).stroke(Color.secondary.opacity(0.3)))
                }
            }
            .padding(8)
        }
    }

    private var smartFillButton: some View {
        VStack(alignment: .leading, spacing: 6) {
            Button {
                vm.smartFill()
            } label: {
                HStack(spacing: 6) {
                    if vm.isSmartFilling {
                        ProgressView().controlSize(.mini)
                        Text("Analyzing with Apple Intelligence…")
                    } else {
                        Image(systemName: "sparkles")
                        Text("Auto-fill from Image")
                    }
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 5)
            }
            .buttonStyle(.bordered)
            .disabled(vm.selectedImagePath == nil || vm.isSmartFilling)
            .help(vm.selectedImagePath == nil
                ? "Select an image first"
                : "Use Apple Intelligence to suggest project name, collection, motifs, and mood")

            if let s = vm.smartFillSuggestions {
                VStack(alignment: .leading, spacing: 3) {
                    Label("Suggested by Apple Intelligence", systemImage: "sparkles")
                        .font(.caption2.bold())
                        .foregroundStyle(.purple)
                    Text("Motifs: \(s.motifs)")
                        .font(.caption2).foregroundStyle(.secondary)
                    Text("Mood: \(s.colorMood)")
                        .font(.caption2).foregroundStyle(.secondary)
                }
                .padding(6)
                .background(Color.purple.opacity(0.07))
                .clipShape(RoundedRectangle(cornerRadius: 6))
            }

            Divider()
        }
    }

    private func field(_ label: String, text: Binding<String>, placeholder: String) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(label).font(.caption).foregroundStyle(.secondary)
            TextField(placeholder, text: text)
                .textFieldStyle(.roundedBorder)
        }
    }

    private func picker<T: RawRepresentable & CaseIterable & Hashable>(
        _ label: String, selection: Binding<T>, items: T.AllCases
    ) -> some View where T.RawValue == String, T.AllCases: RandomAccessCollection {
        HStack {
            Text(label).font(.caption).foregroundStyle(.secondary)
            Spacer()
            Picker("", selection: selection) {
                ForEach(Array(items), id: \.self) { item in
                    Text(item.rawValue).tag(item)
                }
            }
            .frame(width: 200)
        }
    }
}
