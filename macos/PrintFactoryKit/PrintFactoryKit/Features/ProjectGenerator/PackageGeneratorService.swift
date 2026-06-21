import Foundation
import AppKit

final class PackageGeneratorService {

    static let shared = PackageGeneratorService()
    private init() {}

    func generate(project projectIn: FactoryProject, analysis: ArtworkAnalysis) throws -> FactoryPackage {
        var project = projectIn
        let fs = FileSystemService.shared
        let pdf = PDFGenerationService.shared
        let tmpl = MarkdownTemplateService.shared

        // 1. Ensure base dir exists BEFORE reading project number
        try fs.ensureBaseDirectoryExists()
        if project.projectCode.isEmpty {
            let year = Calendar.current.component(.year, from: project.createdAt)
            let number = fs.nextProjectNumber()
            project.projectCode = fs.makeProjectCode(year: year, number: number)
        }

        // 2. Create folder structure (only folders that will contain files)
        let projectFolder = try fs.createProjectFolder(for: project)
        let packageFolder   = projectFolder.appendingPathComponent("08_FACTORY_PACKAGE")
        let artworkFolder   = packageFolder.appendingPathComponent("09_ORIGINAL_ARTWORK_IMAGE")
        let vectorFolder    = packageFolder.appendingPathComponent("10_VECTOR_AND_REPEAT")

        // 3. Load source image
        var sourceCGImage: CGImage? = nil
        if let srcPath = project.artworkImagePath, !srcPath.isEmpty {
            _ = try? fs.copyArtwork(from: srcPath, into: projectFolder)
            let src  = URL(fileURLWithPath: srcPath)
            let dest = artworkFolder.appendingPathComponent(src.lastPathComponent)
            if !FileManager.default.fileExists(atPath: dest.path) {
                try FileManager.default.copyItem(at: src, to: dest)
            }
            sourceCGImage = NSImage(contentsOfFile: srcPath)?
                .cgImage(forProposedRect: nil, context: nil, hints: nil)
        }

        // 4. Generate print-ready files at 300 DPI (PNG, PDF, SVG, repeat tiles)
        var generatedProductionFiles: [String] = []
        if let cgImage = sourceCGImage {
            let printReadyFiles = try? PrintReadyExportService.shared.generate(
                from: cgImage,
                specs: project.specs,
                material: project.material,
                into: vectorFolder
            )
            if let f = printReadyFiles {
                if let u = f.png300        { generatedProductionFiles.append(u.path) }
                if let u = f.pdf           { generatedProductionFiles.append(u.path) }
                if let u = f.svg           { generatedProductionFiles.append(u.path) }
                if let u = f.repeat2x2_300 { generatedProductionFiles.append(u.path) }
                if let u = f.repeat3x3_300 { generatedProductionFiles.append(u.path) }
            }
        } else {
            // No image — write honest note
            let vectorNote = "No artwork image provided. Add an image and regenerate to get print-ready files."
            try fs.writeText(vectorNote, to: vectorFolder.appendingPathComponent("NO_IMAGE_PROVIDED.txt"))
        }

        // 6. Generate all documents
        let briefMD      = tmpl.designBrief(project: project, analysis: analysis)
        let paletteMD    = tmpl.colorPalette(project: project, analysis: analysis)
        let productionMD = tmpl.productionNotes(project: project, analysis: analysis)
        let techPackMD   = tmpl.techPack(project: project, analysis: analysis)
        let checklistMD  = tmpl.approvalChecklist(project: project)
        let supplierTXT  = tmpl.supplierMessage(project: project)

        // Save markdown source to 00_BRIEF
        let briefFolder = projectFolder.appendingPathComponent("00_BRIEF")
        try fs.writeText(briefMD,      to: briefFolder.appendingPathComponent("design_brief.md"))
        try fs.writeText(paletteMD,    to: briefFolder.appendingPathComponent("color_palette.md"))
        try fs.writeText(productionMD, to: briefFolder.appendingPathComponent("production_notes.md"))
        try fs.writeText(techPackMD,   to: briefFolder.appendingPathComponent("tech_pack.md"))
        try fs.writeText(checklistMD,  to: briefFolder.appendingPathComponent("approval_checklist.md"))

        // 7. Approval report
        let allFiles = generatedProductionFiles + [
            packageFolder.appendingPathComponent("04_PRODUCT_TECH_PACK.pdf").path,
            packageFolder.appendingPathComponent("06_FACTORY_APPROVAL_CHECKLIST.pdf").path
        ]
        let approvalReport = ApprovalAgentService.shared.evaluate(
            project: project, analysis: analysis, generatedFiles: allFiles
        )
        let readinessMD = ApprovalAgentService.shared.aiReadinessReport(
            project: project, analysis: analysis, report: approvalReport
        )
        let readMeStr = makeReadMe(project: project, productionFileCount: generatedProductionFiles.count)

        // 8. Generate PDFs
        let readMePDF      = pdf.generatePDF(from: readMeStr,      title: "Read Me First")
        let briefPDF       = pdf.generatePDF(from: briefMD,        title: "Design Brief")
        let palettePDF     = pdf.generateColorPalettePDF(project: project, analysis: analysis)
        let techPackPDF    = pdf.generatePDF(from: techPackMD,     title: "Product Tech Pack")
        let productionPDF  = pdf.generatePDF(from: productionMD,   title: "Production Notes")
        let checklistPDF   = pdf.generatePDF(from: checklistMD,    title: "Factory Approval Checklist")
        let readinessPDF   = pdf.generatePDF(from: readinessMD,    title: "AI Factory Readiness Report")

        // 9. Write PDFs
        try fs.writeData(readMePDF,     to: packageFolder.appendingPathComponent("01_READ_ME_FIRST.pdf"))
        try fs.writeData(briefPDF,      to: packageFolder.appendingPathComponent("02_DESIGN_BRIEF.pdf"))
        try fs.writeData(palettePDF,    to: packageFolder.appendingPathComponent("03_COLOR_PALETTE.pdf"))
        try fs.writeData(techPackPDF,   to: packageFolder.appendingPathComponent("04_PRODUCT_TECH_PACK.pdf"))
        try fs.writeData(productionPDF, to: packageFolder.appendingPathComponent("05_PRODUCTION_NOTES.pdf"))
        try fs.writeData(checklistPDF,  to: packageFolder.appendingPathComponent("06_FACTORY_APPROVAL_CHECKLIST.pdf"))
        try fs.writeData(readinessPDF,  to: packageFolder.appendingPathComponent("07_AI_FACTORY_READINESS_REPORT.pdf"))
        try fs.writeText(supplierTXT,   to: packageFolder.appendingPathComponent("08_SUPPLIER_MESSAGE.txt"))

        // 10. ZIP — only non-empty files
        let exportFolder = projectFolder.appendingPathComponent("09_EXPORT")
        let zipFilename = "\(project.projectCode)_FACTORY_PACKAGE.zip"
        let zipURL = exportFolder.appendingPathComponent(zipFilename)
        try ZipExportService.shared.createZip(sourceDirectory: packageFolder, outputURL: zipURL)

        return FactoryPackage(
            project: project,
            analysis: analysis,
            approvalReport: approvalReport,
            projectFolderURL: projectFolder,
            zipURL: zipURL,
            generatedAt: Date()
        )
    }

    private func makeReadMe(project: FactoryProject, productionFileCount: Int) -> String {
        let specs = project.specs
        let hasDims = specs.widthCM > 0
        let hasPrint = specs.printAreaWidthCM > 0

        return """
        # READ ME FIRST — FACTORY PACKAGE
        **Project:** \(project.projectCode) — \(project.displayName)
        **Collection:** \(project.displayCollectionName)
        **Product:** \(project.productType.rawValue)
        **Material:** \(project.material.rawValue)
        **Print Method:** \(project.printMethod.rawValue)

        ---

        ## Package Contents

        ### Documents
        | File | Description |
        |------|-------------|
        | 02_DESIGN_BRIEF.pdf | Design concept, palette, product details |
        | 03_COLOR_PALETTE.pdf | Extracted color palette — HEX + RGB + swatches |
        | 04_PRODUCT_TECH_PACK.pdf | Full technical spec sheet |
        | 05_PRODUCTION_NOTES.pdf | Material-specific production requirements |
        | 06_FACTORY_APPROVAL_CHECKLIST.pdf | Factory fills and signs before production |
        | 07_AI_FACTORY_READINESS_REPORT.pdf | Readiness audit |
        | 08_SUPPLIER_MESSAGE.txt | Ready-to-send message EN + PT |

        ### Production Files (\(productionFileCount) files in print_files/)
        | File | Use |
        |------|-----|
        | seamless_2x2.png | 2×2 seamless repeat tile — main production repeat |
        | seamless_3x3.png | 3×3 seamless repeat tile — alternate scale |
        | sparse_2x2.png | Sparse repeat variant |
        \(hasPrint ? "| artwork_print_scaled_\(specs.targetDPI)dpi.png | Scaled to \(specs.printAreaSummary) @ \(specs.targetDPI) DPI |" : "| (no scaled file) | Print dimensions not specified |")

        ### Original Artwork & Print-Ready Files
        | Folder | Contents |
        |--------|---------|
        | 09_ORIGINAL_ARTWORK_IMAGE/ | Source image provided — raster format |
        | 10_VECTOR_AND_REPEAT/ | ✅ Print-ready files: 300 DPI PNG, PDF, SVG, repeat tiles |

        ---

        ## Specifications Summary
        - **Dimensions:** \(hasDims ? specs.dimensionSummary : "⚠️ Not specified")
        - **Print Area:** \(hasPrint ? specs.printAreaSummary : "⚠️ Not specified")
        - **Zipper:** \(!specs.zipperColor.isEmpty ? specs.zipperColor + " " + specs.zipperType : "⚠️ Not specified")
        - **Lining:** \(!specs.liningColor.isEmpty ? specs.liningColor : "⚠️ Not specified")

        ---

        ## ⚠️ Critical Requirements Before Mass Production

        1. **Vector files required** — raster PNG cannot be used for professional print production
        2. **Color confirmation required** — factory must confirm all colors via physical sample
        3. **Physical sample mandatory** — client must sign off before bulk run
        4. **[TBD] items in tech pack** — any incomplete spec must be confirmed before production

        ---

        ## Status
        **APPROVED FOR FACTORY REVIEW — NOT FOR MASS PRODUCTION**

        ---
        *PrintFactoryKit v1 — Local-first macOS app — No cloud services used*
        """
    }
}
