import Foundation
import AppKit
import CoreGraphics

final class ImageAnalysisService {

    static let shared = ImageAnalysisService()
    private init() {}

    func analyze(imagePath: String) throws -> ArtworkAnalysis {
        let url = URL(fileURLWithPath: imagePath)
        let fileSize = (try? FileManager.default.attributesOfItem(atPath: imagePath)[.size] as? Int64) ?? 0
        let ext = url.pathExtension.uppercased()

        guard let image = NSImage(contentsOf: url) else {
            throw AnalysisError.cannotLoadImage
        }

        guard let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
            throw AnalysisError.cannotLoadImage
        }

        let width = cgImage.width
        let height = cgImage.height

        let colors = PaletteExtractionService.shared.extractColors(from: cgImage, count: 8)

        var warnings: [AnalysisWarning] = [
            .nonVectorSource,
            .pantoneNotDefined,
            .factorySampleRequired
        ]
        if width < 2000 || height < 2000 {
            warnings.insert(.lowResolution, at: 0)
        }

        return ArtworkAnalysis(
            pixelWidth: width,
            pixelHeight: height,
            fileSizeBytes: fileSize,
            fileFormat: ext.isEmpty ? "Unknown" : ext,
            dominantColors: colors,
            warnings: warnings
        )
    }

    enum AnalysisError: LocalizedError {
        case cannotLoadImage
        var errorDescription: String? { "Cannot load or decode the selected image." }
    }
}
