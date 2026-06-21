import SwiftUI

/// First-launch setup sheet — shown once until user confirms.
struct SetupView: View {
    @ObservedObject var settings: AppSettings
    @State private var prefix: String = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 24) {

            // Header
            VStack(alignment: .leading, spacing: 6) {
                Text("Welcome to PrintFactoryKit")
                    .font(.title.bold())
                Text("Configure where your factory projects will be saved.")
                    .font(.body)
                    .foregroundStyle(.secondary)
            }

            Divider()

            // Output folder
            VStack(alignment: .leading, spacing: 8) {
                Label("Output Folder", systemImage: "folder")
                    .font(.headline)
                Text("All project folders will be created here.")
                    .font(.caption)
                    .foregroundStyle(.secondary)

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

                    Button("Change…") {
                        settings.browseForFolder()
                    }
                    .buttonStyle(.bordered)
                }
            }

            // Project prefix
            VStack(alignment: .leading, spacing: 8) {
                Label("Project Code Prefix", systemImage: "tag")
                    .font(.headline)
                Text("Used to name project folders and files, e.g. \(prefix.isEmpty ? "PRINT" : prefix)_2026_001_PROJECT_NAME")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                TextField("e.g. PRINT or FF or STUDIO", text: $prefix)
                    .textFieldStyle(.roundedBorder)
                    .onChange(of: prefix) {
                        let clean = prefix
                            .uppercased()
                            .replacingOccurrences(of: " ", with: "_")
                            .filter { $0.isLetter || $0.isNumber || $0 == "_" }
                        if clean != prefix { prefix = clean }
                        settings.projectPrefix = clean.isEmpty ? "PRINT" : clean
                    }
            }

            Divider()

            // Preview
            VStack(alignment: .leading, spacing: 4) {
                Text("Preview")
                    .font(.caption.bold())
                    .foregroundStyle(.secondary)
                Text("\(settings.outputFolder.path)/\(settings.projectPrefix)_2026_001_MY_DESIGN/")
                    .font(.caption.monospaced())
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
                    .truncationMode(.middle)
            }
            .padding(10)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.green.opacity(0.06))
            .clipShape(RoundedRectangle(cornerRadius: 8))

            // Confirm
            Button {
                settings.isConfigured = true
            } label: {
                Text("Start Using PrintFactoryKit")
                    .fontWeight(.semibold)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 6)
            }
            .buttonStyle(.borderedProminent)
        }
        .padding(32)
        .frame(width: 520)
        .onAppear { prefix = settings.projectPrefix }
    }
}
