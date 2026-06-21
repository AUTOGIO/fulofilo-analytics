import Foundation
import CoreGraphics
import AppKit

final class PaletteExtractionService {

    static let shared = PaletteExtractionService()
    private init() {}

    func extractColors(from cgImage: CGImage, count: Int = 8) -> [ExtractedColor] {
        let thumbSize = 150
        let colorSpace = CGColorSpaceCreateDeviceRGB()
        let bitmapInfo = CGImageAlphaInfo.premultipliedLast.rawValue

        guard let context = CGContext(
            data: nil, width: thumbSize, height: thumbSize,
            bitsPerComponent: 8, bytesPerRow: thumbSize * 4,
            space: colorSpace, bitmapInfo: bitmapInfo
        ) else { return [] }

        context.interpolationQuality = .high
        context.draw(cgImage, in: CGRect(x: 0, y: 0, width: thumbSize, height: thumbSize))
        guard let data = context.data else { return [] }
        let buffer = data.bindMemory(to: UInt8.self, capacity: thumbSize * thumbSize * 4)

        // Collect all opaque pixels
        var pixels: [(r: Int, g: Int, b: Int)] = []
        pixels.reserveCapacity(thumbSize * thumbSize)

        for i in 0..<(thumbSize * thumbSize) {
            let o = i * 4
            let a = Int(buffer[o + 3])
            guard a > 30 else { continue }
            pixels.append((Int(buffer[o]), Int(buffer[o + 1]), Int(buffer[o + 2])))
        }

        guard !pixels.isEmpty else { return [] }

        // --- K-means style: segment into hue + brightness buckets for diversity ---
        // Bucket by: hue segment (12 segments) + brightness (3 levels) = 36 buckets
        struct Bucket {
            var sumR: Int = 0
            var sumG: Int = 0
            var sumB: Int = 0
            var count: Int = 0
        }
        let hueSeg = 12
        let brightSeg = 3
        var buckets = [Int: Bucket]()

        for p in pixels {
            let (h, s, v) = rgbToHSV(p.r, p.g, p.b)
            // Skip near-white and near-black only if there are better options
            let brightBucket: Int
            if v < 0.18 { brightBucket = 0 }
            else if v > 0.88 && s < 0.12 { brightBucket = 2 }
            else { brightBucket = 1 }

            let hueBucket = s < 0.08 ? hueSeg : Int(h / 360.0 * Double(hueSeg)) % hueSeg
            let key = brightBucket * hueSeg + hueBucket

            var b = buckets[key] ?? Bucket()
            b.sumR += p.r; b.sumG += p.g; b.sumB += p.b; b.count += 1
            buckets[key] = b
        }

        // Sort buckets by pixel count descending, pick top `count` with diversity enforcement
        let sorted = buckets.values
            .filter { $0.count > 0 }
            .sorted { $0.count > $1.count }

        var result: [ExtractedColor] = []
        for bucket in sorted {
            guard result.count < count else { break }
            let n = bucket.count
            let r = bucket.sumR / n
            let g = bucket.sumG / n
            let b_ = bucket.sumB / n
            // Skip if too similar to already selected colors
            let tooClose = result.contains { existing in
                let dr = abs(existing.r - r)
                let dg = abs(existing.g - g)
                let db = abs(existing.b - b_)
                return dr + dg + db < 30
            }
            if !tooClose {
                result.append(ExtractedColor(r: r, g: g, b: b_))
            }
        }

        // If we couldn't get `count` diverse colors, fill remaining from raw top buckets
        if result.count < count {
            for bucket in sorted {
                guard result.count < count else { break }
                let n = bucket.count
                let r = bucket.sumR / n
                let g = bucket.sumG / n
                let b_ = bucket.sumB / n
                let alreadyIn = result.contains { $0.r == r && $0.g == g && $0.b == b_ }
                if !alreadyIn { result.append(ExtractedColor(r: r, g: g, b: b_)) }
            }
        }

        // Sort result: most saturated/colorful first, neutrals last
        return result.sorted { a, b in
            let (_, sa, _) = rgbToHSV(a.r, a.g, a.b)
            let (_, sb, _) = rgbToHSV(b.r, b.g, b.b)
            return sa > sb
        }
    }

    private func rgbToHSV(_ r: Int, _ g: Int, _ b: Int) -> (h: Double, s: Double, v: Double) {
        let rf = Double(r) / 255.0
        let gf = Double(g) / 255.0
        let bf = Double(b) / 255.0
        let cmax = max(rf, gf, bf)
        let cmin = min(rf, gf, bf)
        let delta = cmax - cmin

        let v = cmax
        let s = cmax == 0 ? 0.0 : delta / cmax

        var h = 0.0
        if delta > 0 {
            if cmax == rf      { h = 60 * (((gf - bf) / delta).truncatingRemainder(dividingBy: 6)) }
            else if cmax == gf { h = 60 * (((bf - rf) / delta) + 2) }
            else               { h = 60 * (((rf - gf) / delta) + 4) }
            if h < 0 { h += 360 }
        }
        return (h, s, v)
    }
}
