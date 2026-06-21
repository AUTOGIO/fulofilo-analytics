import SwiftUI

struct ContentView: View {
    @StateObject private var vm = ProjectViewModel()

    var body: some View {
        HSplitView {
            // Left: Input Panel
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    headerView
                    ImportArtworkView(vm: vm)
                    ProjectDetailsView(vm: vm)
                    ProductionSpecsView(vm: vm)
                    if vm.analysis != nil {
                        AnalysisPreviewView(vm: vm)
                    }
                    generateButton
                }
                .padding(20)
            }
            .frame(minWidth: 380, maxWidth: 480)

            // Right: Result Panel
            ScrollView {
                if let pkg = vm.generatedPackage {
                    ResultView(package: pkg)
                } else {
                    emptyState
                }
            }
            .frame(minWidth: 300)
        }
        .frame(minWidth: 700, minHeight: 500)
        .alert("Error", isPresented: $vm.showError) {
            Button("OK") {}
        } message: {
            Text(vm.errorMessage)
        }
    }

    private var headerView: some View {
        HStack(alignment: .top) {
            VStack(alignment: .leading, spacing: 2) {
                Text("PrintFactoryKit")
                    .font(.title.bold())
                Text("Factory Package Generator — Local-first, Apple-native")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Button {
                vm.resetAllFields()
            } label: {
                Label("Refresh", systemImage: "arrow.counterclockwise")
                    .font(.caption)
            }
            .buttonStyle(.bordered)
            .help("Clear all fields and start a new project")
        }
    }

    private var generateButton: some View {
        Button {
            vm.generatePackage()
        } label: {
            HStack {
                if vm.isGenerating {
                    ProgressView().controlSize(.small)
                } else {
                    Image(systemName: "shippingbox.fill")
                }
                Text(vm.isGenerating ? "Generating…" : "Generate Factory Package")
                    .fontWeight(.semibold)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 8)
        }
        .buttonStyle(.borderedProminent)
        .disabled(vm.isGenerating || vm.selectedImagePath == nil || vm.projectName.isEmpty)
        .help(vm.generateButtonTooltip)
    }

    private var emptyState: some View {
        VStack(spacing: 12) {
            Image(systemName: "shippingbox")
                .font(.system(size: 48))
                .foregroundStyle(.secondary)
            Text("No package generated yet")
                .font(.headline)
                .foregroundStyle(.secondary)
            Text("Select an image, fill in project details,\nthen click Generate Factory Package.")
                .font(.caption)
                .foregroundStyle(.tertiary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(40)
    }
}
