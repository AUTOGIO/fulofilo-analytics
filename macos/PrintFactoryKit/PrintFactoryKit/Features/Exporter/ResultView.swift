import SwiftUI

struct ResultView: View {
    let package: FactoryPackage

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            statusBanner

            GroupBox("Project") {
                VStack(alignment: .leading, spacing: 6) {
                    infoRow("Code", package.project.projectCode)
                    infoRow("Name", package.project.projectName)
                    infoRow("Collection", package.project.displayCollectionName)
                    infoRow("Product", package.project.productType.rawValue)
                    infoRow("Material", package.project.material.rawValue)
                    infoRow("Print Method", package.project.printMethod.rawValue)
                }
                .padding(8)
            }

            GroupBox("Generated Paths") {
                VStack(alignment: .leading, spacing: 8) {
                    pathRow("Project Folder", package.projectFolderURL.path)
                    if let zip = package.zipURL {
                        pathRow("Factory Package ZIP", zip.path)
                    }
                }
                .padding(8)
            }

            if !package.approvalReport.blockingIssues.isEmpty {
                GroupBox("Blocking Issues") {
                    VStack(alignment: .leading, spacing: 4) {
                        ForEach(package.approvalReport.blockingIssues, id: \.self) { issue in
                            Label(issue, systemImage: "xmark.circle.fill")
                                .font(.caption)
                                .foregroundStyle(.red)
                        }
                    }
                    .padding(8)
                }
            }

            if !package.approvalReport.warnings.isEmpty {
                GroupBox("Warnings — Action Required") {
                    VStack(alignment: .leading, spacing: 4) {
                        ForEach(package.approvalReport.warnings, id: \.self) { w in
                            Label(w, systemImage: "exclamationmark.triangle.fill")
                                .font(.caption)
                                .foregroundStyle(.orange)
                        }
                    }
                    .padding(8)
                }
            }

            if !package.approvalReport.recommendedActions.isEmpty {
                GroupBox("Next Steps Before Factory") {
                    VStack(alignment: .leading, spacing: 5) {
                        ForEach(Array(package.approvalReport.recommendedActions.enumerated()), id: \.offset) { i, action in
                            HStack(alignment: .top, spacing: 6) {
                                Text("\(i + 1).")
                                    .font(.caption.monospacedDigit())
                                    .foregroundStyle(.secondary)
                                    .frame(width: 18, alignment: .trailing)
                                Text(action)
                                    .font(.caption)
                                    .foregroundStyle(.primary)
                            }
                        }
                    }
                    .padding(8)
                }
            }

            HStack(spacing: 12) {
                Button("Open Project Folder") {
                    NSWorkspace.shared.open(package.projectFolderURL)
                }
                if let zip = package.zipURL {
                    Button("Reveal ZIP in Finder") {
                        NSWorkspace.shared.activateFileViewerSelecting([zip])
                    }
                    .buttonStyle(.borderedProminent)
                }
            }

            Text("⚠️ Approved for factory review only — not for mass production.")
                .font(.caption2)
                .foregroundStyle(.secondary)
                .padding(.top, 4)
        }
        .padding(20)
    }

    private var statusBanner: some View {
        let approved = package.approvalReport.isApproved
        return HStack(spacing: 10) {
            Image(systemName: approved ? "checkmark.seal.fill" : "xmark.seal.fill")
                .font(.system(size: 28))
                .foregroundStyle(approved ? .green : .red)
            VStack(alignment: .leading, spacing: 2) {
                Text(package.approvalReport.status.rawValue)
                    .font(.headline)
                    .foregroundStyle(approved ? .green : .red)
                Text(approved
                    ? "Package is ready for factory review."
                    : "Fix blocking issues before sending to factory.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background((approved ? Color.green : Color.red).opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }

    private func infoRow(_ label: String, _ value: String) -> some View {
        HStack(alignment: .top) {
            Text(label).font(.caption).foregroundStyle(.secondary).frame(width: 100, alignment: .leading)
            Text(value.isEmpty ? "—" : value).font(.caption)
        }
    }

    private func pathRow(_ label: String, _ path: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label).font(.caption.bold())
            Text(path)
                .font(.caption)
                .foregroundStyle(.secondary)
                .textSelection(.enabled)
                .lineLimit(3)
        }
    }
}
