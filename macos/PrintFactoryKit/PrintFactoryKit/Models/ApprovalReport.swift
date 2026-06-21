import Foundation

enum ApprovalStatus: String, Codable {
    case approved = "APPROVED_FOR_FACTORY_REVIEW"
    case blocked = "BLOCKED_NEEDS_CORRECTION"
}

struct ApprovalReport: Codable {
    var status: ApprovalStatus
    var passedChecks: [String]
    var blockingIssues: [String]
    var warnings: [String]
    var recommendedActions: [String]
    var generatedAt: Date

    var isApproved: Bool { status == .approved }

    static let massProductionDisclaimer = """
    ⚠️ IMPORTANT LIMITATION
    This package is APPROVED FOR FACTORY REVIEW ONLY.
    Mass production approval requires:
    • Physical factory sample validation
    • Client sign-off on physical sample
    • Factory quality control confirmation
    • Final color approval via physical print or Pantone/CMYK matching
    This AI-generated report cannot approve mass production.
    """
}
