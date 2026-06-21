import Foundation
import CoreGraphics
import AppKit

final class RepeatTileService {

    static let shared = RepeatTileService()
    private init() {}

    // Generate NxN seamless repeat tile from source image
    func generateRepeatTile(from cgImage: CGImage, gridSize: Int, targetPX: CGSize? = nil) -> CGImage? {
        let srcW = cgImage.width
        let srcH = cgImage.height
        let outW = Int(targetPX?.width  ?? CGFloat(srcW * gridSize))
        let outH = Int(targetPX?.height ?? CGFloat(srcH * gridSize))

        let colorSpace = CGColorSpaceCreateDeviceRGB()
        guard let ctx = CGContext(
            data: nil,
            width: outW, height: outH,
            bitsPerComponent: 8,
            bytesPerRow: outW * 4,
            space: colorSpace,
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else { return nil }

        let tileW = CGFloat(outW) / CGFloat(gridSize)
        let tileH = CGFloat(outH) / CGFloat(gridSize)

        for row in 0..<gridSize {
            for col in 0..<gridSize {
                let x = CGFloat(col) * tileW
                let y = CGFloat(row) * tileH
                ctx.draw(cgImage, in: CGRect(x: x, y: y, width: tileW, height: tileH))
            }
        }

        return ctx.makeImage()
    }

    // Generate print-scaled artwork at target DPI for given cm dimensions
    func generatePrintScaled(from cgImage: CGImage, widthCM: Double, heightCM: Double, dpi: Int) -> CGImage? {
        guard widthCM > 0, heightCM > 0 else { return nil }
        let pxW = Int((widthCM / 2.54) * Double(dpi))
        let pxH = Int((heightCM / 2.54) * Double(dpi))
        guard pxW > 0, pxH > 0 else { return nil }

        let colorSpace = CGColorSpaceCreateDeviceRGB()
        guard let ctx = CGContext(
            data: nil,
            width: pxW, height: pxH,
            bitsPerComponent: 8,
            bytesPerRow: pxW * 4,
            space: colorSpace,
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else { return nil }

        ctx.interpolationQuality = .high
        ctx.draw(cgImage, in: CGRect(x: 0, y: 0, width: pxW, height: pxH))
        return ctx.makeImage()
    }

    func savePNG(_ cgImage: CGImage, to url: URL) throws {
        let bitmapRep = NSBitmapImageRep(cgImage: cgImage)
        guard let data = bitmapRep.representation(using: .png, properties: [:]) else {
            throw RepeatError.encodingFailed
        }
        try data.write(to: url, options: .atomic)
    }

    enum RepeatError: LocalizedError {
        case encodingFailed
        var errorDescription: String? { "Failed to encode PNG data." }
    }
}
