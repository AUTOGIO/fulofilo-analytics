import XCTest
@testable import PrintFactoryKit

final class PrintFactoryKitTests: XCTestCase {

    // MARK: - Project Folder Name Generation

    func testProjectFolderName() {
        var project = FactoryProject(projectName: "Caju Cacto", collectionName: "Summer 2026")
        project.projectCode = "FF_PRINT_2026_001"
        XCTAssertEqual(project.folderName, "FF_PRINT_2026_001_CAJU_CACTO")
    }

    func testProjectFolderNameSpecialChars() {
        var project = FactoryProject(projectName: "Cactos & Flores!", collectionName: "")
        project.projectCode = "FF_PRINT_2026_002"
        // Special chars stripped, spaces -> underscores
        XCTAssertFalse(project.folderName.contains(" "))
        XCTAssertFalse(project.folderName.contains("!"))
        XCTAssertFalse(project.folderName.contains("&"))
    }

    // MARK: - Project Code Generation

    func testProjectCodeFormat() {
        let fs = FileSystemService.shared
        let code = fs.makeProjectCode(year: 2026, number: 3)
        XCTAssertEqual(code, "FF_PRINT_2026_003")
    }

    func testProjectCodePaddingLargeNumber() {
        let fs = FileSystemService.shared
        let code = fs.makeProjectCode(year: 2026, number: 42)
        XCTAssertEqual(code, "FF_PRINT_2026_042")
    }

    // MARK: - Palette Extraction

    func testPaletteExtractionReturnsSomeColors() {
        // Create a simple 10x10 red CGImage
        let size = 10
        let colorSpace = CGColorSpaceCreateDeviceRGB()
        guard let ctx = CGContext(
            data: nil, width: size, height: size,
            bitsPerComponent: 8, bytesPerRow: size * 4,
            space: colorSpace, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else { return XCTFail("Could not create context") }
        ctx.setFillColor(red: 1, green: 0, blue: 0, alpha: 1)
        ctx.fill(CGRect(x: 0, y: 0, width: size, height: size))
        guard let cgImage = ctx.makeImage() else { return XCTFail("No image") }

        let colors = PaletteExtractionService.shared.extractColors(from: cgImage, count: 8)
        XCTAssertFalse(colors.isEmpty, "Expected at least one extracted color")
        // Should be mostly red
        let first = colors[0]
        XCTAssertGreaterThan(first.r, 100)
    }

    // MARK: - Approval Agent Logic

    func testApprovalBlockedWhenProjectNameMissing() {
        var project = FactoryProject(projectName: "", collectionName: "")
        project.artworkImagePath = "/tmp/test.png"
        project.projectCode = "FF_PRINT_2026_001"
        let analysis = ArtworkAnalysis(
            pixelWidth: 3000, pixelHeight: 3000,
            fileSizeBytes: 1_000_000, fileFormat: "PNG",
            dominantColors: [ExtractedColor(r: 255, g: 0, b: 0)],
            warnings: []
        )
        let report = ApprovalAgentService.shared.evaluate(
            project: project, analysis: analysis,
            generatedFiles: ["04_PRODUCT_TECH_PACK.pdf", "06_FACTORY_APPROVAL_CHECKLIST.pdf"]
        )
        XCTAssertEqual(report.status, .blocked)
        XCTAssertTrue(report.blockingIssues.contains { $0.contains("Project name") })
    }

    func testApprovalBlockedWhenLowResolution() {
        var project = FactoryProject(projectName: "Test", collectionName: "Col")
        project.artworkImagePath = "/tmp/test.png"
        project.projectCode = "FF_PRINT_2026_001"
        let analysis = ArtworkAnalysis(
            pixelWidth: 800, pixelHeight: 600,
            fileSizeBytes: 100_000, fileFormat: "PNG",
            dominantColors: [ExtractedColor(r: 100, g: 100, b: 100)],
            warnings: [.lowResolution]
        )
        let report = ApprovalAgentService.shared.evaluate(
            project: project, analysis: analysis,
            generatedFiles: ["04_PRODUCT_TECH_PACK.pdf", "06_FACTORY_APPROVAL_CHECKLIST.pdf"]
        )
        XCTAssertEqual(report.status, .blocked)
        XCTAssertTrue(report.blockingIssues.contains { $0.contains("resolution") })
    }

    func testApprovalApprovedWhenAllRequiredPresent() {
        var project = FactoryProject(
            projectName: "Caju",
            collectionName: "Summer",
            productType: .necessaire,
            material: .canvas12oz,
            printMethod: .digitalTextile,
            factoryName: "Factory X"
        )
        project.artworkImagePath = "/tmp/test.png"
        project.projectCode = "FF_PRINT_2026_001"
        let analysis = ArtworkAnalysis(
            pixelWidth: 4000, pixelHeight: 4000,
            fileSizeBytes: 5_000_000, fileFormat: "PNG",
            dominantColors: [
                ExtractedColor(r: 255, g: 100, b: 50),
                ExtractedColor(r: 0, g: 200, b: 100)
            ],
            warnings: [.nonVectorSource, .repeatTileMissing, .pantoneNotDefined, .factorySampleRequired]
        )
        let report = ApprovalAgentService.shared.evaluate(
            project: project, analysis: analysis,
            generatedFiles: ["04_PRODUCT_TECH_PACK.pdf", "06_FACTORY_APPROVAL_CHECKLIST.pdf"]
        )
        XCTAssertEqual(report.status, .approved)
        XCTAssertTrue(report.blockingIssues.isEmpty)
    }

    // MARK: - Markdown Template

    func testDesignBriefContainsProjectName() {
        var project = FactoryProject(projectName: "Meu Projeto", collectionName: "Col 2026")
        project.projectCode = "FF_PRINT_2026_001"
        let analysis = ArtworkAnalysis(
            pixelWidth: 2000, pixelHeight: 2000,
            fileSizeBytes: 1_000_000, fileFormat: "PNG",
            dominantColors: [], warnings: []
        )
        let md = MarkdownTemplateService.shared.designBrief(project: project, analysis: analysis)
        XCTAssertTrue(md.contains("Meu Projeto"))
        XCTAssertTrue(md.contains("FF_PRINT_2026_001"))
    }

    func testSupplierMessageContainsBothLanguages() {
        var project = FactoryProject(projectName: "Test", collectionName: "Col")
        project.factoryName = "Fabrica ABC"
        project.projectCode = "FF_PRINT_2026_001"
        let msg = MarkdownTemplateService.shared.supplierMessage(project: project)
        XCTAssertTrue(msg.contains("ENGLISH"))
        XCTAssertTrue(msg.contains("PORTUGUÊS"))
        XCTAssertTrue(msg.contains("Fabrica ABC"))
    }
}
