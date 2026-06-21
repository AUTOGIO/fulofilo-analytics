import SwiftUI

struct ContentView: View {
    @StateObject private var vm = ProjectViewModel()
    @ObservedObject private var settings = AppSettings.shared
    @State private var showSettings = false

    var body: some View {
        HSplitView {
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
        .sheet(isPresented: Binding(
            get: { !settings.isConfigured },
            set: { _ in }
        )) {
            SetupView(settings: settings)
        }
        .sheet(isPresented: $showSettings) {
            settingsSheet
        }
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
                showSettings = true
            } label: {
                Image(systemName: "gearshape")
                    .font(.caption)
            }
            .buttonStyle(.bordered)
            .help("Output folder and project prefix settings")

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

    private var settingsSheet: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text("Settings")
                .font(.title2.bold())

            Divider()

            VStack(alignment: .leading, spacing: 8) {
                Label("Output Folder", systemImage: "folder")
                    .font(.headline)
                HStack(spacing: 10) {
                    Text(settings.outputFolder.path)
                        .font(.caption.monospaced())
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                        .truncationMode(.middle)
                        .padding(8)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color.secondary.opacity(0.08))
                        .clipShape(RoundedRectangle(cornerRadius: 6))
                    Button("Change…") { settings.browseForFolder() }
                        .buttonStyle(.bordered)
                }
            }

            VStack(alignment: .leading, spacing: 8) {
                Label("Project Code Prefix", systemImage: "tag")
                    .font(.headline)
                TextField("e.g. PRINT", text: $settings.projectPrefix)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 180)
                Text("Folders will be named: \(settings.projectPrefix)_2026_001_PROJECT_NAME")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Divider()

            HStack {
                Button("Reset to Defaults") { settings.reset() }
                    .foregroundStyle(.red)
                Spacer()
                Button("Done") { showSettings = false }
                    .buttonStyle(.borderedProminent)
            }
        }
        .padding(28)
        .frame(width: 480)
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
