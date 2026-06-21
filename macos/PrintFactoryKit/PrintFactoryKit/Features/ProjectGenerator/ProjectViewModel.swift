import SwiftUI
import AppKit

@MainActor
final class ProjectViewModel: ObservableObject {
    @Published var selectedImagePath: String?
    @Published var projectName: String = ""
    @Published var collectionName: String = ""
    @Published var factoryName: String = ""
    @Published var productType: ProductType = .necessaire
    @Published var material: Material = .canvas12oz
    @Published var printMethod: PrintMethod = .digitalTextile
    @Published var notes: String = ""

    // Production specs
    @Published var specsWidthCM: Double = 0
    @Published var specsHeightCM: Double = 0
    @Published var specsDepthCM: Double = 0
    @Published var specsPrintWidthCM: Double = 0
    @Published var specsPrintHeightCM: Double = 0
    @Published var specsTargetDPI: Int = 150
    @Published var specsZipperColor: String = ""
    @Published var specsZipperLengthCM: Double = 0
    @Published var specsZipperType: String = ""
    @Published var specsStrapMaterial: String = ""
    @Published var specsStrapWidthCM: Double = 0
    @Published var specsStrapLengthCM: Double = 0
    @Published var specsLiningColor: String = ""
    @Published var specsLiningMaterial: String = ""
    @Published var specsTargetQty: Int = 0
    @Published var specsSeam: String = ""

    @Published var analysis: ArtworkAnalysis?
    @Published var generatedPackage: FactoryPackage?
    @Published var isGenerating: Bool = false
    @Published var isSmartFilling: Bool = false
    @Published var showError: Bool = false
    @Published var errorMessage: String = ""
    @Published var smartFillSuggestions: ProjectFieldSuggestions?

    var generateButtonTooltip: String {
        if selectedImagePath == nil { return "Please select an artwork image first" }
        if projectName.isEmpty { return "Please enter a project name" }
        return "Generate full factory package"
    }

    func browseForImage() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = false
        panel.allowedContentTypes = [.jpeg, .png, .tiff, .heic, .image]
        panel.message = "Select your artwork image"

        if panel.runModal() == .OK, let url = panel.url {
            selectImage(at: url.path)
        }
    }

    func selectImage(at path: String) {
        selectedImagePath = path
        analysis = nil
        // Auto-fill specs on first image selection if all specs are still at zero
        if specsWidthCM == 0 { applyProductionDefaults() }
        Task { await analyzeImage(at: path) }
    }

    func analyzeImage(at path: String) async {
        do {
            let result = try await Task.detached(priority: .userInitiated) {
                try ImageAnalysisService.shared.analyze(imagePath: path)
            }.value
            analysis = result
        } catch {
            showError(error.localizedDescription)
        }
    }

    func applyProductionDefaults() {
        let defaults = ProductionDefaults.specs(for: productType, material: material)
        specsWidthCM         = defaults.widthCM
        specsHeightCM        = defaults.heightCM
        specsDepthCM         = defaults.depthCM
        specsPrintWidthCM    = defaults.printAreaWidthCM
        specsPrintHeightCM   = defaults.printAreaHeightCM
        specsTargetDPI       = defaults.targetDPI
        specsZipperColor     = defaults.zipperColor
        specsZipperLengthCM  = defaults.zipperLengthCM
        specsZipperType      = defaults.zipperType
        specsStrapMaterial   = defaults.strapMaterial
        specsStrapWidthCM    = defaults.strapWidthCM
        specsStrapLengthCM   = defaults.strapLengthCM
        specsLiningColor     = defaults.liningColor
        specsLiningMaterial  = defaults.liningMaterial
        specsSeam            = defaults.seam
        specsTargetQty       = defaults.targetQuantity
    }

    func smartFill() {
        guard let path = selectedImagePath else { return }
        isSmartFilling = true
        Task {
            do {
                let suggestions = try await SmartFillService.shared.suggestFields(from: path)
                // Only fill fields that are still empty — never overwrite manual input
                // factoryName is intentionally excluded: the AI cannot know the real factory
                if projectName.isEmpty { projectName = suggestions.projectName }
                if collectionName.isEmpty { collectionName = fixAccents(suggestions.collectionName) }
                if notes.isEmpty {
                    notes = "Motifs: \(suggestions.motifs)\nMood: \(suggestions.colorMood)\n\(suggestions.visualDescription)"
                }
                smartFillSuggestions = suggestions
                isSmartFilling = false
            } catch {
                isSmartFilling = false
                showError(error.localizedDescription)
            }
        }
    }

    func generatePackage() {
        guard let imagePath = selectedImagePath, !projectName.isEmpty else { return }

        isGenerating = true
        generatedPackage = nil

        Task {
            do {
                let specs = ProductionSpecs(
                    widthCM: specsWidthCM,
                    heightCM: specsHeightCM,
                    depthCM: specsDepthCM,
                    printAreaWidthCM: specsPrintWidthCM,
                    printAreaHeightCM: specsPrintHeightCM,
                    targetDPI: specsTargetDPI,
                    zipperColor: specsZipperColor,
                    zipperLengthCM: specsZipperLengthCM,
                    zipperType: specsZipperType,
                    strapMaterial: specsStrapMaterial,
                    strapWidthCM: specsStrapWidthCM,
                    strapLengthCM: specsStrapLengthCM,
                    liningColor: specsLiningColor,
                    liningMaterial: specsLiningMaterial,
                    targetQuantity: specsTargetQty,
                    seam: specsSeam
                )
                let project = FactoryProject(
                    projectName: projectName,
                    collectionName: collectionName,
                    productType: productType,
                    material: material,
                    printMethod: printMethod,
                    factoryName: factoryName,
                    notes: notes,
                    artworkImagePath: imagePath,
                    specs: specs
                )

                let analysis = try self.analysis ?? ImageAnalysisService.shared.analyze(imagePath: imagePath)

                let capturedProject = project
                let capturedAnalysis = analysis
                let pkg = try await Task.detached(priority: .userInitiated) {
                    try PackageGeneratorService.shared.generate(project: capturedProject, analysis: capturedAnalysis)
                }.value

                self.generatedPackage = pkg
                self.isGenerating = false
            } catch {
                self.isGenerating = false
                showError(error.localizedDescription)
            }
        }
    }

    func resetAllFields() {
        selectedImagePath = nil
        projectName = ""
        collectionName = ""
        factoryName = ""
        productType = .necessaire
        material = .canvas12oz
        printMethod = .digitalTextile
        notes = ""
        specsWidthCM = 0; specsHeightCM = 0; specsDepthCM = 0
        specsPrintWidthCM = 0; specsPrintHeightCM = 0; specsTargetDPI = 150
        specsZipperColor = ""; specsZipperLengthCM = 0; specsZipperType = ""
        specsStrapMaterial = ""; specsStrapWidthCM = 0; specsStrapLengthCM = 0
        specsLiningColor = ""; specsLiningMaterial = ""
        specsTargetQty = 0; specsSeam = ""
        analysis = nil
        generatedPackage = nil
        smartFillSuggestions = nil
        isGenerating = false
        isSmartFilling = false
    }

    // Fix common accent losses from on-device model output
    private func fixAccents(_ text: String) -> String {
        text
            .replacingOccurrences(of: "Verao", with: "Verão")
            .replacingOccurrences(of: "verao", with: "verão")
            .replacingOccurrences(of: "Primavera", with: "Primavera") // already correct
            .replacingOccurrences(of: "Outono", with: "Outono")
            .replacingOccurrences(of: "Colecao", with: "Coleção")
            .replacingOccurrences(of: "colecao", with: "coleção")
            .replacingOccurrences(of: "Inverno", with: "Inverno")
    }

    private func showError(_ message: String) {
        errorMessage = message
        showError = true
    }
}
