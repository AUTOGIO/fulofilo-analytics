import Foundation
import CoreGraphics
import ImageIO
import AppKit

/// Generates production-grade print files at exact dimensions + 300 DPI.
/// Outputs: PNG (300 Dpi metadata), PDF (exact cm page), SVG (embedded raster).
/// Note: native .cdr requires CorelDRAW installed — not generatable on macOS without it.
/// PDF is the recommended CorelDRAW-compatible interchange format for raster artwork.
final class PrintReadyExportService {

    static let shared = PrintReadyExportService()
    private init() {}

    struct GeneratedFiles {
        var png300: URL?
        var pdf: URL?
        var svg: URL?
        var repeat2x2_300: URL?
        var repeat3x3_300: URL?
    }

    func generate(
        from cgImage: CGImage,
        specs: ProductionSpecs,
        material: Material,
        into folder: URL
    ) throws -> GeneratedFiles {
        let widthCM  = specs.printAreaWidthCM
        let heightCM = specs.printAreaHeightCM
        guard widthCM > 0, heightCM > 0 else {
            throw ExportError.missingDimensions
        }

        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)

        let dpi = 300
        var pxW = Int((widthCM / 2.54) * Double(dpi))
        var pxH = Int((heightCM / 2.54) * Double(dpi))

        // Poliéster com Elastano: pre-compensate vertical stretch (8%)
        // Print taller so when fabric stretches it reaches the correct final height
        if material == .polyesterElastano {
            pxH = Int(Double(pxH) * 1.08)
        }

        guard let scaled = scaleImage(cgImage, toWidth: pxW, height: pxH) else {
            throw ExportError.scalingFailed
        }

        // Cetim + Lona: add 4 mm bleed on all sides (mirror-extend edges)
        let finalImage: CGImage
        if material == .cetimColado {
            let bleedPX = Int((4.0 / 10.0) * Double(dpi) / 2.54) // 4mm at 300 DPI
            finalImage = applyBleed(to: scaled, bleedPX: bleedPX) ?? scaled
            pxW += bleedPX * 2
            pxH += bleedPX * 2
        } else {
            finalImage = scaled
        }

        var result = GeneratedFiles()

        // Actual output dimensions in cm (may differ from specs due to bleed/stretch)
        let outWidthCM  = Double(pxW) / Double(dpi) * 2.54
        let outHeightCM = Double(pxH) / Double(dpi) * 2.54

        // 1. PNG at 300 DPI with embedded resolution metadata
        let pngURL = folder.appendingPathComponent("artwork_PRINT_READY_300dpi.png")
        try savePNG(finalImage, to: pngURL, dpi: dpi)
        result.png300 = pngURL

        // 2. PDF at exact print dimensions (CorelDRAW / Illustrator / any RIP software)
        let pdfURL = folder.appendingPathComponent("artwork_PRINT_READY_300dpi.pdf")
        try savePDF(finalImage, to: pdfURL, widthCM: outWidthCM, heightCM: outHeightCM)
        result.pdf = pdfURL

        // 3. SVG with embedded raster (CorelDRAW 2019+, Inkscape, web)
        let svgURL = folder.appendingPathComponent("artwork_PRINT_READY.svg")
        try saveSVG(finalImage, to: svgURL, widthCM: outWidthCM, heightCM: outHeightCM)
        result.svg = svgURL

        // 4. Seamless repeat tiles at 300 DPI
        let tileService = RepeatTileService.shared
        let targetTile2 = CGSize(width: pxW * 2, height: pxH * 2)
        let targetTile3 = CGSize(width: pxW * 3, height: pxH * 3)

        if let tile2 = tileService.generateRepeatTile(from: cgImage, gridSize: 2, targetPX: targetTile2) {
            let url = folder.appendingPathComponent("seamless_repeat_2x2_300dpi.png")
            try savePNG(tile2, to: url, dpi: dpi)
            result.repeat2x2_300 = url
        }

        if let tile3 = tileService.generateRepeatTile(from: cgImage, gridSize: 3, targetPX: targetTile3) {
            let url = folder.appendingPathComponent("seamless_repeat_3x3_300dpi.png")
            try savePNG(tile3, to: url, dpi: dpi)
            result.repeat3x3_300 = url
        }

        // 5. Write a README so factory knows what each file is for
        try writeReadme(to: folder, widthCM: widthCM, heightCM: heightCM, pxW: pxW, pxH: pxH)

        return result
    }

    // MARK: - Renderers

    /// Mirror-extend all four edges by bleedPX pixels (standard print bleed technique)
    private func applyBleed(to cgImage: CGImage, bleedPX: Int) -> CGImage? {
        let srcW = cgImage.width
        let srcH = cgImage.height
        let outW = srcW + bleedPX * 2
        let outH = srcH + bleedPX * 2

        guard let ctx = CGContext(
            data: nil, width: outW, height: outH,
            bitsPerComponent: 8, bytesPerRow: outW * 4,
            space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else { return nil }

        ctx.interpolationQuality = .high
        // Draw main image centred
        ctx.draw(cgImage, in: CGRect(x: bleedPX, y: bleedPX, width: srcW, height: srcH))

        // Mirror top edge
        ctx.saveGState()
        ctx.translateBy(x: CGFloat(bleedPX), y: CGFloat(bleedPX + srcH))
        ctx.scaleBy(x: 1, y: -1)
        ctx.draw(cgImage, in: CGRect(x: 0, y: 0, width: srcW, height: bleedPX))
        ctx.restoreGState()

        // Mirror bottom edge
        ctx.saveGState()
        ctx.translateBy(x: CGFloat(bleedPX), y: 0)
        ctx.draw(cgImage, in: CGRect(x: 0, y: CGFloat(bleedPX) - CGFloat(bleedPX), width: CGFloat(srcW), height: CGFloat(bleedPX)))
        ctx.restoreGState()

        // Mirror left edge
        ctx.saveGState()
        ctx.translateBy(x: CGFloat(bleedPX), y: CGFloat(bleedPX))
        ctx.scaleBy(x: -1, y: 1)
        ctx.draw(cgImage, in: CGRect(x: 0, y: 0, width: bleedPX, height: srcH))
        ctx.restoreGState()

        // Mirror right edge
        ctx.saveGState()
        ctx.translateBy(x: CGFloat(bleedPX + srcW), y: CGFloat(bleedPX))
        ctx.draw(cgImage, in: CGRect(x: CGFloat(-srcW + bleedPX), y: 0, width: CGFloat(srcW), height: CGFloat(srcH)))
        ctx.restoreGState()

        return ctx.makeImage()
    }

    private func scaleImage(_ cgImage: CGImage, toWidth w: Int, height h: Int) -> CGImage? {
        guard let ctx = CGContext(
            data: nil, width: w, height: h,
            bitsPerComponent: 8, bytesPerRow: w * 4,
            space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else { return nil }
        ctx.interpolationQuality = .high
        ctx.draw(cgImage, in: CGRect(x: 0, y: 0, width: w, height: h))
        return ctx.makeImage()
    }

    private func savePNG(_ cgImage: CGImage, to url: URL, dpi: Int) throws {
        guard let dest = CGImageDestinationCreateWithURL(url as CFURL, "public.png" as CFString, 1, nil) else {
            throw ExportError.encodingFailed("PNG destination")
        }
        let ppm = Int(Double(dpi) / 0.0254) // pixels per metre
        let props: [CFString: Any] = [
            kCGImagePropertyDPIWidth:  dpi,
            kCGImagePropertyDPIHeight: dpi,
            kCGImagePropertyPNGDictionary: [
                kCGImagePropertyPNGXPixelsPerMeter: ppm,
                kCGImagePropertyPNGYPixelsPerMeter: ppm
            ] as [CFString: Any]
        ]
        CGImageDestinationAddImage(dest, cgImage, props as CFDictionary)
        guard CGImageDestinationFinalize(dest) else {
            throw ExportError.encodingFailed("PNG finalize")
        }
    }

    private func savePDF(_ cgImage: CGImage, to url: URL, widthCM: Double, heightCM: Double) throws {
        // 1 PDF point = 1/72 inch
        let ptW = (widthCM / 2.54) * 72.0
        let ptH = (heightCM / 2.54) * 72.0
        var mediaBox = CGRect(x: 0, y: 0, width: ptW, height: ptH)
        guard let ctx = CGContext(url as CFURL, mediaBox: &mediaBox, nil) else {
            throw ExportError.encodingFailed("PDF context")
        }
        ctx.beginPDFPage(nil)
        ctx.draw(cgImage, in: mediaBox)
        ctx.endPDFPage()
        ctx.closePDF()
    }

    private func saveSVG(_ cgImage: CGImage, to url: URL, widthCM: Double, heightCM: Double) throws {
        // PNG encoded as base64 embedded inside SVG
        guard let dest = CGImageDestinationCreateWithData(
            NSMutableData() as CFMutableData, "public.png" as CFString, 1, nil
        ) else { throw ExportError.encodingFailed("SVG/PNG") }

        // Re-encode image to PNG data for embedding
        let mutable = NSMutableData()
        guard let dest2 = CGImageDestinationCreateWithData(mutable as CFMutableData, "public.png" as CFString, 1, nil) else {
            throw ExportError.encodingFailed("SVG embed")
        }
        CGImageDestinationAddImage(dest2, cgImage, nil)
        guard CGImageDestinationFinalize(dest2) else {
            throw ExportError.encodingFailed("SVG finalize")
        }

        _ = dest
        let b64 = (mutable as Data).base64EncodedString()
        let pxW = cgImage.width
        let pxH = cgImage.height
        let svg = """
        <?xml version="1.0" encoding="UTF-8"?>
        <svg xmlns="http://www.w3.org/2000/svg"
             xmlns:xlink="http://www.w3.org/1999/xlink"
             width="\(String(format: "%.2f", widthCM))cm"
             height="\(String(format: "%.2f", heightCM))cm"
             viewBox="0 0 \(pxW) \(pxH)">
          <!-- Artwork at 300 DPI — \(pxW)x\(pxH)px = \(String(format: "%.1f", widthCM))x\(String(format: "%.1f", heightCM))cm -->
          <!-- Open in CorelDRAW, Inkscape, Adobe Illustrator, or any browser -->
          <image x="0" y="0"
                 width="\(pxW)" height="\(pxH)"
                 xlink:href="data:image/png;base64,\(b64)"
                 image-rendering="high-quality"/>
        </svg>
        """
        try svg.write(to: url, atomically: true, encoding: .utf8)
    }

    private func writeReadme(to folder: URL, widthCM: Double, heightCM: Double, pxW: Int, pxH: Int) throws {
        let text = """
        PRINT-READY FILES — PrintFactoryKit
        =====================================

        All files in this folder are generated at EXACT PRINT DIMENSIONS at 300 DPI.

        Print Area: \(String(format: "%.1f", widthCM)) × \(String(format: "%.1f", heightCM)) cm
        Pixel Size: \(pxW) × \(pxH) px at 300 DPI

        FILES:

        artwork_PRINT_READY_300dpi.png
          → Primary production file. 300 DPI embedded in metadata.
          → Open in CorelDRAW, Photoshop, or send directly to digital textile printer (RIP software).

        artwork_PRINT_READY_300dpi.pdf
          → PDF with artwork at exact print dimensions.
          → Recommended for CorelDRAW import — preserves scale.
          → Also accepted by most factory RIP software directly.

        artwork_PRINT_READY.svg
          → SVG with embedded raster at 300 DPI.
          → Open in CorelDRAW 2019+, Inkscape, Affinity Designer, or any browser.
          → Allows adding vector elements (outlines, text, registration marks) on top.

        seamless_repeat_2x2_300dpi.png
          → 2×2 seamless repeat tile at 300 DPI.
          → Use for full-fabric or full-surface print layout.

        seamless_repeat_3x3_300dpi.png
          → 3×3 seamless repeat tile at 300 DPI.
          → Alternate scale repeat.

        NOTE ON .CDR FILES:
          Native CorelDRAW .cdr files cannot be generated without CorelDRAW installed.
          The PDF and SVG files above open directly in CorelDRAW with full editability.
          Recommendation: open artwork_PRINT_READY_300dpi.pdf in CorelDRAW,
          save as .cdr if the factory requires native format.

        IMPORTANT — BEFORE MASS PRODUCTION:
          • Confirm color accuracy via physical pre-production sample
          • Factory must confirm Pantone or CMYK color references
          • These are raster files — vector tracing may be required for screen printing
        """
        try text.write(to: folder.appendingPathComponent("README_PRINT_FILES.txt"), atomically: true, encoding: .utf8)
    }

    enum ExportError: LocalizedError {
        case missingDimensions
        case scalingFailed
        case encodingFailed(String)

        var errorDescription: String? {
            switch self {
            case .missingDimensions: return "Print area dimensions not set — fill Production Specs before generating."
            case .scalingFailed: return "Failed to scale artwork to print dimensions."
            case .encodingFailed(let s): return "File encoding failed: \(s)"
            }
        }
    }
}
