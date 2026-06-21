import Foundation
import Vision
import AppKit
import FoundationModels

// MARK: - Generable output struct

@Generable
struct ProjectFieldSuggestions {
    @Guide(description: "A short creative project name in Title Case based on the visual motifs in the image. 2–4 words maximum. In Portuguese or English depending on the cultural context of the artwork. Example: 'Caju Cacto', 'Flores Tropicais', 'Ocean Dream'.")
    var projectName: String

    @Guide(description: "A collection name suggestion in Title Case. Should evoke a season, mood, or theme. 2–3 words. Example: 'Verão 2026', 'Summer Bloom', 'Terra Collection'.")
    var collectionName: String

    @Guide(description: "A one-sentence visual description of the artwork's motifs, colors, and mood. In English. Keep it concise and factory-relevant.")
    var visualDescription: String

    @Guide(description: "The primary visual motifs identified in the image. Comma-separated list of 3–6 items. Example: 'cactus, cashew fruit, tropical leaves, geometric shapes'.")
    var motifs: String

    @Guide(description: "The overall color mood of the artwork in 3–5 words. Example: 'warm earth tones, vibrant tropical palette, muted pastels'.")
    var colorMood: String
}

// MARK: - SmartFillService

@MainActor
final class SmartFillService {

    static let shared = SmartFillService()
    private init() {}

    private var session: LanguageModelSession?

    /// Analyzes the image with Vision + Apple Intelligence and returns field suggestions.
    func suggestFields(from imagePath: String) async throws -> ProjectFieldSuggestions {
        let visionLabels = try await classifyImage(at: imagePath)
        let colorDescription = try await describeColors(at: imagePath)
        return try await generateSuggestions(visionLabels: visionLabels, colorDescription: colorDescription)
    }

    // MARK: - Vision classification

    private func classifyImage(at path: String) async throws -> [String] {
        guard let cgImage = NSImage(contentsOfFile: path)?
            .cgImage(forProposedRect: nil, context: nil, hints: nil)
        else { throw SmartFillError.imageLoadFailed }

        return try await withCheckedThrowingContinuation { continuation in
            let request = VNClassifyImageRequest { request, error in
                if let error {
                    continuation.resume(throwing: error)
                    return
                }
                let observations = request.results as? [VNClassificationObservation] ?? []
                let topLabels = observations
                    .filter { $0.confidence > 0.1 }
                    .prefix(20)
                    .map { "\($0.identifier) (\(Int($0.confidence * 100))%)" }
                continuation.resume(returning: Array(topLabels))
            }

            let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
            do {
                try handler.perform([request])
            } catch {
                continuation.resume(throwing: error)
            }
        }
    }

    private func describeColors(at path: String) async throws -> String {
        guard let cgImage = NSImage(contentsOfFile: path)?
            .cgImage(forProposedRect: nil, context: nil, hints: nil)
        else { return "unknown" }

        let colors = PaletteExtractionService.shared.extractColors(from: cgImage, count: 5)
        let hexList = colors.map { $0.hex }.joined(separator: ", ")

        // Classify dominant hue family
        let hueNames = colors.prefix(3).map { hueFamily(r: $0.r, g: $0.g, b: $0.b) }
        var seen = Set<String>()
        let uniqueHues = hueNames.filter { seen.insert($0).inserted }
        return "\(uniqueHues.joined(separator: ", ")) tones (\(hexList))"
    }

    private func hueFamily(r: Int, g: Int, b: Int) -> String {
        let rf = Double(r), gf = Double(g), bf = Double(b)
        let brightness = (rf + gf + bf) / 765.0
        if brightness > 0.88 { return "white/cream" }
        if brightness < 0.15 { return "black/dark" }
        let max = Swift.max(rf, gf, bf)
        let min = Swift.min(rf, gf, bf)
        let delta = max - min
        if delta < 20 { return brightness > 0.6 ? "light neutral" : "dark neutral" }
        if rf == max {
            if gf > bf + 40 { return "orange/warm" }
            return gf > 100 ? "coral/pink" : "red"
        }
        if gf == max { return bf > rf + 40 ? "teal/cyan" : "green" }
        return rf > gf + 30 ? "purple/violet" : "blue"
    }

    // MARK: - Apple Intelligence generation

    private func generateSuggestions(
        visionLabels: [String],
        colorDescription: String
    ) async throws -> ProjectFieldSuggestions {
        if session == nil {
            session = LanguageModelSession()
        }

        let labelsText = visionLabels.isEmpty
            ? "No specific labels detected"
            : visionLabels.joined(separator: ", ")

        let prompt = """
        You are helping a Brazilian textile/accessories designer fill in project details for a factory production package.

        An artwork image was analyzed using Apple Vision. Here are the results:

        Vision labels detected: \(labelsText)
        Dominant color palette: \(colorDescription)

        Based on these image analysis results, suggest project metadata for a textile print design package.
        The designer makes bolsas (bags), cangas (sarongs), necessaires, and beach accessories.
        Suggestions should be creative but professional, appropriate for factory documents.
        Use Portuguese names when they feel natural for Brazilian market products.
        """

        let response = try await session!.respond(
            to: prompt,
            generating: ProjectFieldSuggestions.self
        )
        return response.content
    }

    enum SmartFillError: LocalizedError {
        case imageLoadFailed
        case modelUnavailable
        var errorDescription: String? {
            switch self {
            case .imageLoadFailed: return "Could not load image for analysis."
            case .modelUnavailable: return "Apple Intelligence model is not available on this device."
            }
        }
    }
}
