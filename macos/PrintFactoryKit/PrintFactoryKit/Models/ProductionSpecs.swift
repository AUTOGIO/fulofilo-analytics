import Foundation

struct ProductionSpecs: Codable {
    // Product dimensions
    var widthCM: Double = 0
    var heightCM: Double = 0
    var depthCM: Double = 0

    // Print area
    var printAreaWidthCM: Double = 0
    var printAreaHeightCM: Double = 0
    var targetDPI: Int = 300

    // Hardware
    var zipperColor: String = ""
    var zipperLengthCM: Double = 0
    var zipperType: String = ""          // e.g. "YKK #5 metal", "coil nylon"
    var strapMaterial: String = ""       // e.g. "cotton webbing", "leather"
    var strapWidthCM: Double = 0
    var strapLengthCM: Double = 0

    // Interior
    var liningColor: String = ""
    var liningMaterial: String = ""

    // Order
    var targetQuantity: Int = 0
    var seam: String = ""                // e.g. "1 cm overlock"

    // Computed helpers
    var dimensionSummary: String {
        guard widthCM > 0 || heightCM > 0 || depthCM > 0 else { return "Not specified" }
        if depthCM > 0 { return "\(fmt(widthCM)) × \(fmt(heightCM)) × \(fmt(depthCM)) cm" }
        return "\(fmt(widthCM)) × \(fmt(heightCM)) cm"
    }

    var printAreaSummary: String {
        guard printAreaWidthCM > 0 || printAreaHeightCM > 0 else { return "Not specified" }
        return "\(fmt(printAreaWidthCM)) × \(fmt(printAreaHeightCM)) cm"
    }

    var printPixelWidth: Int  { Int((printAreaWidthCM / 2.54) * Double(targetDPI)) }
    var printPixelHeight: Int { Int((printAreaHeightCM / 2.54) * Double(targetDPI)) }

    private func fmt(_ v: Double) -> String {
        v.truncatingRemainder(dividingBy: 1) == 0 ? String(Int(v)) : String(format: "%.1f", v)
    }
}
