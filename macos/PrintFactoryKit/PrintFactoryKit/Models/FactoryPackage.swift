import Foundation

struct FactoryPackage: Codable {
    var project: FactoryProject
    var analysis: ArtworkAnalysis
    var approvalReport: ApprovalReport
    var projectFolderURL: URL
    var zipURL: URL?
    var generatedAt: Date

    var readinessLabel: String {
        approvalReport.isApproved ? "✅ Approved for Factory Review" : "🚫 Blocked — Needs Correction"
    }
}
