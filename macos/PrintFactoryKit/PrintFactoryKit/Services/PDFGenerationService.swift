import Foundation
import AppKit
import PDFKit

final class PDFGenerationService {

    static let shared = PDFGenerationService()
    private init() {}

    // Generate a PDF from plain text/markdown string using NSAttributedString + PDFDocument
    func generatePDF(from markdown: String, title: String) -> Data {
        let pageRect = CGRect(x: 0, y: 0, width: 595, height: 842) // A4

        // Create PDF data via Core Graphics
        let pdfData = NSMutableData()
        guard let consumer = CGDataConsumer(data: pdfData as CFMutableData) else { return Data() }

        var mediaBox = pageRect
        guard let context = CGContext(consumer: consumer, mediaBox: &mediaBox, nil) else { return Data() }

        let paragraphStyle = NSMutableParagraphStyle()
        paragraphStyle.lineSpacing = 4

        let bodyFont = NSFont.systemFont(ofSize: 10)
        let headingFont = NSFont.boldSystemFont(ofSize: 13)
        let subheadFont = NSFont.boldSystemFont(ofSize: 11)
        let codeFont = NSFont.monospacedSystemFont(ofSize: 9, weight: .regular)
        let italicFont = NSFontManager.shared.font(withFamily: "Helvetica", traits: .italicFontMask, weight: 5, size: 9) ?? NSFont.systemFont(ofSize: 9)

        let margin: CGFloat = 50
        let contentWidth = pageRect.width - margin * 2

        // Parse lines and build attributed string
        let attrStr = NSMutableAttributedString()
        let lines = markdown.components(separatedBy: "\n")

        for line in lines {
            var font = bodyFont
            var text = line
            var color = NSColor.labelColor
            var spacingBefore: CGFloat = 0

            if line.hasPrefix("# ") {
                font = NSFont.boldSystemFont(ofSize: 16)
                text = String(line.dropFirst(2))
                spacingBefore = 8
                color = NSColor(red: 0.1, green: 0.2, blue: 0.5, alpha: 1)
            } else if line.hasPrefix("## ") {
                font = headingFont
                text = String(line.dropFirst(3))
                spacingBefore = 6
            } else if line.hasPrefix("### ") {
                font = subheadFont
                text = String(line.dropFirst(4))
                spacingBefore = 4
            } else if line.hasPrefix("- [ ] ") || line.hasPrefix("- [x] ") {
                text = "☐ " + String(line.dropFirst(6))
            } else if line.hasPrefix("- ") {
                text = "• " + String(line.dropFirst(2))
            } else if line.hasPrefix("> ") {
                font = italicFont
                text = "  " + String(line.dropFirst(2))
                color = NSColor.secondaryLabelColor
            } else if line.hasPrefix("|") {
                font = codeFont
            } else if line.hasPrefix("**") || line.contains("**") {
                // Simple bold strip
                text = line.replacingOccurrences(of: "**", with: "")
                font = NSFont.boldSystemFont(ofSize: 10)
            } else if line.hasPrefix("---") {
                text = "─────────────────────────────────────────────────────────"
                font = codeFont
                color = NSColor.separatorColor
            }

            // Remove remaining markdown bold markers
            text = text.replacingOccurrences(of: "**", with: "")
            text = text.replacingOccurrences(of: "`", with: "")

            let para = NSMutableParagraphStyle()
            para.paragraphSpacingBefore = spacingBefore
            para.lineSpacing = 3

            let attrs: [NSAttributedString.Key: Any] = [
                .font: font,
                .foregroundColor: color,
                .paragraphStyle: para
            ]
            attrStr.append(NSAttributedString(string: text + "\n", attributes: attrs))
        }

        // Paginate using NSLayoutManager
        let textStorage = NSTextStorage(attributedString: attrStr)
        let layoutManager = NSLayoutManager()
        textStorage.addLayoutManager(layoutManager)

        var pageIndex = 0
        let glyphCount = layoutManager.numberOfGlyphs

        // Reserve space: 30pt header + margin top + margin bottom + 20pt footer
        let contentHeight = pageRect.height - margin * 2 - 50
        let textContainer = NSTextContainer(size: CGSize(width: contentWidth, height: contentHeight))
        layoutManager.addTextContainer(textContainer)
        layoutManager.glyphRange(for: textContainer)

        var charIndex = 0

        repeat {
            let remainingStr = NSAttributedString(
                attributedString: attrStr.attributedSubstring(
                    from: NSRange(location: charIndex, length: attrStr.length - charIndex)))
            let ts2 = NSTextStorage(attributedString: remainingStr)
            let lm2 = NSLayoutManager()
            ts2.addLayoutManager(lm2)
            let tc2 = NSTextContainer(size: CGSize(width: contentWidth, height: contentHeight))
            lm2.addTextContainer(tc2)

            let glyphRange2 = lm2.glyphRange(for: tc2)
            let charRange2 = lm2.characterRange(forGlyphRange: glyphRange2, actualGlyphRange: nil)

            context.beginPDFPage(nil)
            context.setFillColor(NSColor.white.cgColor)
            context.fill(pageRect)

            // Flip CTM so (0,0) is top-left — NSLayoutManager then draws top-to-bottom correctly
            context.saveGState()
            context.translateBy(x: 0, y: pageRect.height)
            context.scaleBy(x: 1, y: -1)

            let nsContext = NSGraphicsContext(cgContext: context, flipped: true)
            NSGraphicsContext.saveGraphicsState()
            NSGraphicsContext.current = nsContext

            // Header (page 0 only) — y measured from top in flipped space
            if pageIndex == 0 {
                let headerAttrs: [NSAttributedString.Key: Any] = [
                    .font: NSFont.boldSystemFont(ofSize: 8),
                    .foregroundColor: NSColor.secondaryLabelColor
                ]
                NSAttributedString(string: "PrintFactoryKit — \(title)", attributes: headerAttrs)
                    .draw(at: CGPoint(x: margin, y: 18))
            }

            // Footer — near the page bottom (high y in flipped space)
            let footerAttrs: [NSAttributedString.Key: Any] = [
                .font: NSFont.systemFont(ofSize: 7),
                .foregroundColor: NSColor.tertiaryLabelColor
            ]
            NSAttributedString(
                string: "Page \(pageIndex + 1) — APPROVED FOR FACTORY REVIEW ONLY — Not for mass production",
                attributes: footerAttrs)
                .draw(at: CGPoint(x: margin, y: pageRect.height - 18))

            // Content — starts just below the header area
            let contentOriginY: CGFloat = margin + 30
            lm2.drawBackground(forGlyphRange: glyphRange2, at: CGPoint(x: margin, y: contentOriginY))
            lm2.drawGlyphs(forGlyphRange: glyphRange2, at: CGPoint(x: margin, y: contentOriginY))

            NSGraphicsContext.restoreGraphicsState()
            context.restoreGState()
            context.endPDFPage()

            charIndex += charRange2.length
            pageIndex += 1

            if charRange2.length == 0 { break }

        } while charIndex < attrStr.length

        _ = glyphCount
        context.closePDF()

        return pdfData as Data
    }

    // Generate color palette PDF with colored swatches
    func generateColorPalettePDF(project: FactoryProject, analysis: ArtworkAnalysis) -> Data {
        let pageRect = CGRect(x: 0, y: 0, width: 595, height: 842)
        let pdfData = NSMutableData()
        guard let consumer = CGDataConsumer(data: pdfData as CFMutableData) else { return Data() }
        var mediaBox = pageRect
        guard let context = CGContext(consumer: consumer, mediaBox: &mediaBox, nil) else { return Data() }

        context.beginPDFPage(nil)
        context.setFillColor(NSColor.white.cgColor)
        context.fill(pageRect)

        let nsCtx = NSGraphicsContext(cgContext: context, flipped: false)
        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = nsCtx

        // Title
        let titleAttrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.boldSystemFont(ofSize: 18),
            .foregroundColor: NSColor(red: 0.1, green: 0.2, blue: 0.5, alpha: 1)
        ]
        NSAttributedString(string: "COLOR PALETTE", attributes: titleAttrs)
            .draw(at: CGPoint(x: 50, y: 760))

        let subtitleAttrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 10),
            .foregroundColor: NSColor.secondaryLabelColor
        ]
        NSAttributedString(string: "\(project.projectCode) — \(project.projectName)", attributes: subtitleAttrs)
            .draw(at: CGPoint(x: 50, y: 740))

        // Draw swatches
        let swatchSize: CGFloat = 60
        let gap: CGFloat = 15
        let startX: CGFloat = 50
        var x = startX
        var y: CGFloat = 660

        for (i, color) in analysis.dominantColors.enumerated() {
            let nsColor = NSColor(red: CGFloat(color.r) / 255.0,
                                  green: CGFloat(color.g) / 255.0,
                                  blue: CGFloat(color.b) / 255.0,
                                  alpha: 1.0)
            nsColor.setFill()
            let rect = CGRect(x: x, y: y, width: swatchSize, height: swatchSize)
            context.fill(rect)
            // Border
            context.setStrokeColor(NSColor.separatorColor.cgColor)
            context.setLineWidth(0.5)
            context.stroke(rect)

            // Label: HEX + RGB + CMYK
            let labelAttrs: [NSAttributedString.Key: Any] = [
                .font: NSFont.monospacedSystemFont(ofSize: 7, weight: .regular),
                .foregroundColor: NSColor.labelColor
            ]
            let (c, m, yk, k) = rgbToCMYK(r: color.r, g: color.g, b: color.b)
            NSAttributedString(string: color.hex, attributes: labelAttrs)
                .draw(at: CGPoint(x: x, y: y - 13))
            NSAttributedString(string: "R\(color.r) G\(color.g) B\(color.b)", attributes: labelAttrs)
                .draw(at: CGPoint(x: x, y: y - 22))
            NSAttributedString(string: "C\(c) M\(m) Y\(yk) K\(k)", attributes: labelAttrs)
                .draw(at: CGPoint(x: x, y: y - 31))

            x += swatchSize + gap
            if (i + 1) % 4 == 0 {
                x = startX
                y -= swatchSize + 50
            }
        }

        // Disclaimer
        let disclaimer = """
        ⚠️ These colors are algorithmically extracted from the raster artwork and are approximate.
        Factory must confirm final colors using physical print sample or Pantone/CMYK references.
        Color variation of ±5–10% is expected between digital preview and physical print.
        """
        let disclaimerAttrs: [NSAttributedString.Key: Any] = [
            .font: NSFontManager.shared.font(withFamily: "Helvetica", traits: .italicFontMask, weight: 5, size: 8) ?? NSFont.systemFont(ofSize: 8),
            .foregroundColor: NSColor.secondaryLabelColor
        ]
        NSAttributedString(string: disclaimer, attributes: disclaimerAttrs)
            .draw(in: CGRect(x: 50, y: 50, width: 495, height: 80))

        let footerAttrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 7),
            .foregroundColor: NSColor.tertiaryLabelColor
        ]
        NSAttributedString(string: "Generated by PrintFactoryKit — APPROVED FOR FACTORY REVIEW ONLY — Not for mass production", attributes: footerAttrs)
            .draw(at: CGPoint(x: 50, y: 25))

        NSGraphicsContext.restoreGraphicsState()
        context.endPDFPage()
        context.closePDF()

        return pdfData as Data
    }

    // RGB (0-255) → CMYK (0-100)
    private func rgbToCMYK(r: Int, g: Int, b: Int) -> (c: Int, m: Int, y: Int, k: Int) {
        let rf = Double(r) / 255.0
        let gf = Double(g) / 255.0
        let bf = Double(b) / 255.0
        let k  = 1.0 - max(rf, gf, bf)
        guard k < 1.0 else { return (0, 0, 0, 100) }
        let c = (1.0 - rf - k) / (1.0 - k)
        let m = (1.0 - gf - k) / (1.0 - k)
        let y = (1.0 - bf - k) / (1.0 - k)
        return (Int(c * 100), Int(m * 100), Int(y * 100), Int(k * 100))
    }
}
