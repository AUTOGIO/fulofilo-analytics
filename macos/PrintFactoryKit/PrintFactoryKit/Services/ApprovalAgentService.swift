import Foundation

final class ApprovalAgentService {

    static let shared = ApprovalAgentService()
    private init() {}

    func evaluate(project: FactoryProject, analysis: ArtworkAnalysis, generatedFiles: [String]) -> ApprovalReport {
        var blockingIssues: [String] = []
        var warnings: [String] = []
        var passedChecks: [String] = []
        var recommendedActions: [String] = []

        // --- Blocking checks ---
        if project.artworkImagePath == nil || project.artworkImagePath?.isEmpty == true {
            blockingIssues.append("No artwork image provided")
        } else {
            passedChecks.append("Artwork image present")
        }

        if analysis.pixelWidth < 1500 || analysis.pixelHeight < 1500 {
            blockingIssues.append("Image resolution too low (\(analysis.pixelWidth)×\(analysis.pixelHeight)px) — minimum ~1500px per side recommended")
        } else {
            passedChecks.append("Image resolution acceptable (\(analysis.pixelWidth)×\(analysis.pixelHeight)px)")
        }

        if project.displayName.trimmingCharacters(in: .whitespaces).isEmpty {
            blockingIssues.append("Project name is missing")
        } else {
            passedChecks.append("Project name provided: \(project.displayName)")
        }

        if project.productType == .other && project.productType.rawValue == "Other" {
            // Allow other but note
            passedChecks.append("Product type specified: \(project.productType.rawValue)")
        } else {
            passedChecks.append("Product type specified: \(project.productType.rawValue)")
        }

        if project.material.rawValue.isEmpty {
            blockingIssues.append("Material not specified")
        } else {
            passedChecks.append("Material specified: \(project.material.rawValue)")
        }

        if project.printMethod.rawValue.isEmpty {
            blockingIssues.append("Print method not specified")
        } else {
            passedChecks.append("Print method specified: \(project.printMethod.rawValue)")
        }

        if analysis.dominantColors.isEmpty {
            blockingIssues.append("Color palette could not be extracted")
        } else {
            passedChecks.append("Color palette extracted: \(analysis.dominantColors.count) colors")
        }

        let hasTechPack = generatedFiles.contains { $0.contains("TECH_PACK") }
        let hasChecklist = generatedFiles.contains { $0.contains("CHECKLIST") }

        if !hasTechPack {
            blockingIssues.append("Product tech pack not generated")
        } else {
            passedChecks.append("Product tech pack generated")
        }

        if !hasChecklist {
            blockingIssues.append("Factory approval checklist not generated")
        } else {
            passedChecks.append("Factory approval checklist generated")
        }

        // --- Warnings (non-blocking) ---
        let hasVector = generatedFiles.contains { $0.lowercased().contains("vector") || $0.hasSuffix(".ai") || $0.hasSuffix(".svg") }
        if !hasVector {
            warnings.append("No vector file provided — factory will require vectorization before production")
            recommendedActions.append("Have artwork professionally vectorized (Adobe Illustrator / Affinity Designer)")
        }

        let hasRepeat = generatedFiles.contains { $0.lowercased().contains("seamless") || $0.lowercased().contains("repeat") }
        if hasRepeat {
            passedChecks.append("Repeat tiles generated (2×2, 3×3, sparse)")
        } else {
            warnings.append("Repeat tile files not found in package — verify print_files/ folder")
        }

        // Pantone/CMYK — warn only if project notes contain no color reference keywords
        let notesLower = project.notes.lowercased()
        let hasPantoneRef = notesLower.contains("pantone") || notesLower.contains("cmyk") || notesLower.contains("pms ")
        if !hasPantoneRef {
            warnings.append("No Pantone/CMYK references in notes — factory color matching will be estimated")
        } else {
            passedChecks.append("Color references noted in project notes")
        }

        recommendedActions.append("Confirm Pantone or CMYK color references with a professional color consultant")
        recommendedActions.append("Request physical pre-production sample from factory before bulk order")
        recommendedActions.append("Fill in all ⚠️ Not specified items in the tech pack before sending to factory")

        // --- Final status ---
        let status: ApprovalStatus = blockingIssues.isEmpty ? .approved : .blocked

        return ApprovalReport(
            status: status,
            passedChecks: passedChecks,
            blockingIssues: blockingIssues,
            warnings: warnings,
            recommendedActions: recommendedActions,
            generatedAt: Date()
        )
    }

    func aiReadinessReport(project: FactoryProject, analysis: ArtworkAnalysis, report: ApprovalReport) -> String {
        let dateStr = DateFormatter.localizedString(from: report.generatedAt, dateStyle: .long, timeStyle: .medium)
        let passed = report.passedChecks.map { "  ✅ \($0)" }.joined(separator: "\n")
        let blocked = report.blockingIssues.isEmpty ? "  (none)" : report.blockingIssues.map { "  🚫 \($0)" }.joined(separator: "\n")
        let warns = report.warnings.map { "  ⚠️ \($0)" }.joined(separator: "\n")
        let actions = report.recommendedActions.enumerated().map { i, a in "  \(i + 1). \(a)" }.joined(separator: "\n")

        return """
        # AI FACTORY READINESS REPORT
        **Project:** \(project.projectCode) — \(project.displayName)
        **Generated:** \(dateStr)

        ---

        ## STATUS: \(report.status.rawValue)

        ---

        ## Passed Checks
        \(passed.isEmpty ? "  (none)" : passed)

        ## Blocking Issues
        \(blocked)

        ## Warnings
        \(warns.isEmpty ? "  (none)" : warns)

        ## Recommended Next Actions
        \(actions.isEmpty ? "  (none)" : actions)

        ---

        ## IMPORTANT LIMITATION

        \(ApprovalReport.massProductionDisclaimer)

        ---

        ## About This Report
        This report was generated by the PrintFactoryKit local approval agent.
        It performs deterministic checks based on file presence and project completeness.
        It does NOT use external AI APIs, does NOT access the internet, and does NOT
        have knowledge of factory-specific requirements.

        This report is a first-pass readiness evaluation intended to:
        • Ensure the package is structurally complete before sending to factory
        • Identify obvious missing elements
        • Communicate known limitations clearly

        **This report does NOT constitute:**
        • Professional quality certification
        • Pantone or color accuracy validation
        • Vector or print production approval
        • Mass production clearance

        ---
        *Generated by PrintFactoryKit v1.0 — Local-first macOS app — Apple Silicon*
        *No cloud services were used. No external APIs were called.*
        """
    }
}
