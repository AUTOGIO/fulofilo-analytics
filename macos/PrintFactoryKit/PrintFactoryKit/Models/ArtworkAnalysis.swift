import Foundation
import AppKit

struct ExtractedColor: Identifiable, Codable {
    let id: UUID
    let hex: String
    let r: Int
    let g: Int
    let b: Int

    init(r: Int, g: Int, b: Int) {
        self.id = UUID()
        self.r = r
        self.g = g
        self.b = b
        self.hex = String(format: "#%02X%02X%02X", r, g, b)
    }

    var displayName: String { hex }
}

struct ArtworkAnalysis: Codable {
    var pixelWidth: Int
    var pixelHeight: Int
    var fileSizeBytes: Int64
    var fileFormat: String
    var dominantColors: [ExtractedColor]
    var warnings: [AnalysisWarning]

    var aspectRatio: String {
        let gcd = greatestCommonDivisor(pixelWidth, pixelHeight)
        return "\(pixelWidth / gcd):\(pixelHeight / gcd)"
    }

    var fileSizeFormatted: String {
        let mb = Double(fileSizeBytes) / 1_048_576.0
        if mb >= 1 { return String(format: "%.1f MB", mb) }
        let kb = Double(fileSizeBytes) / 1024.0
        return String(format: "%.0f KB", kb)
    }

    var dpiEstimateNote: String {
        // We can't know print DPI without intended print size, but warn if very small
        if pixelWidth < 1000 || pixelHeight < 1000 {
            return "Very low resolution — likely unsuitable for print"
        } else if pixelWidth < 2000 || pixelHeight < 2000 {
            return "Low resolution — may be insufficient for large format print"
        } else if pixelWidth >= 4000 || pixelHeight >= 4000 {
            return "High resolution — potentially suitable for print (verify DPI at intended size)"
        }
        return "Medium resolution — verify at intended print dimensions"
    }

    private func greatestCommonDivisor(_ a: Int, _ b: Int) -> Int {
        b == 0 ? a : greatestCommonDivisor(b, a % b)
    }
}

enum AnalysisWarning: String, Codable, CaseIterable {
    case lowResolution = "Low resolution image — may not be suitable for professional print"
    case nonVectorSource = "Non-vector source — vectorization required for factory use"
    case repeatTileMissing = "Seamless repeat tile not provided"
    case pantoneNotDefined = "Pantone/CMYK references not defined — factory color matching required"
    case factorySampleRequired = "Physical factory sample required before mass production"
}
