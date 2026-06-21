import SwiftUI

struct AnalysisPreviewView: View {
    @ObservedObject var vm: ProjectViewModel

    var body: some View {
        GroupBox("4. Analysis Preview") {
            if let analysis = vm.analysis {
                VStack(alignment: .leading, spacing: 10) {
                    infoRow("Dimensions", "\(analysis.pixelWidth) × \(analysis.pixelHeight) px")
                    infoRow("Aspect Ratio", analysis.aspectRatio)
                    infoRow("File Size", analysis.fileSizeFormatted)
                    infoRow("Format", analysis.fileFormat)
                    infoRow("Resolution Note", analysis.dpiEstimateNote)

                    Divider()

                    Text("Extracted Color Palette").font(.caption.bold())
                    LazyVGrid(columns: Array(repeating: GridItem(.fixed(36)), count: 8), spacing: 4) {
                        ForEach(analysis.dominantColors) { color in
                            colorSwatch(color)
                        }
                    }

                    if !analysis.warnings.isEmpty {
                        Divider()
                        Text("Warnings").font(.caption.bold())
                        ForEach(analysis.warnings, id: \.rawValue) { warning in
                            Label(warning.rawValue, systemImage: "exclamationmark.triangle.fill")
                                .font(.caption)
                                .foregroundStyle(.orange)
                        }
                    }
                }
                .padding(8)
            }
        }
    }

    private func infoRow(_ label: String, _ value: String) -> some View {
        HStack(alignment: .top) {
            Text(label).font(.caption).foregroundStyle(.secondary).frame(width: 120, alignment: .leading)
            Text(value).font(.caption)
        }
    }

    private func colorSwatch(_ color: ExtractedColor) -> some View {
        let nsColor = NSColor(
            red: CGFloat(color.r) / 255,
            green: CGFloat(color.g) / 255,
            blue: CGFloat(color.b) / 255,
            alpha: 1.0
        )
        return RoundedRectangle(cornerRadius: 4)
            .fill(Color(nsColor))
            .frame(width: 32, height: 32)
            .overlay(RoundedRectangle(cornerRadius: 4).stroke(Color.secondary.opacity(0.3), lineWidth: 0.5))
            .help(color.hex)
    }
}
