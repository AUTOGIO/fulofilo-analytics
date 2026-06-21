import Foundation

/// Industry-standard production specs per product type + material combination.
/// Sources: standard textile bag manufacturing, Brazilian praia/accessories market norms.
struct ProductionDefaults {

    static func specs(for productType: ProductType, material: Material) -> ProductionSpecs {
        var s = ProductionSpecs()

        switch productType {

        case .necessaire:
            // Standard medium cosmetic/toiletry bag
            s.widthCM           = 22
            s.heightCM          = 12
            s.depthCM           = 8
            s.printAreaWidthCM  = 20
            s.printAreaHeightCM = 10
            s.targetDPI         = 150
            s.zipperColor       = "Dourado"
            s.zipperLengthCM    = 22
            s.zipperType        = "YKK #3 nylon espiral"
            s.strapMaterial     = ""         // necessaires typically have no strap
            s.strapWidthCM      = 0
            s.strapLengthCM     = 0
            s.liningColor       = "Preto"
            s.liningMaterial    = materialLining(material)
            s.seam              = "1 cm overlock"
            s.targetQuantity    = 50

        case .cosmeticPouch:
            // Small flat pouch
            s.widthCM           = 18
            s.heightCM          = 10
            s.depthCM           = 2
            s.printAreaWidthCM  = 16
            s.printAreaHeightCM = 8
            s.targetDPI         = 150
            s.zipperColor       = "Dourado"
            s.zipperLengthCM    = 18
            s.zipperType        = "YKK #3 nylon espiral"
            s.strapMaterial     = ""
            s.strapWidthCM      = 0
            s.strapLengthCM     = 0
            s.liningColor       = "Preto"
            s.liningMaterial    = materialLining(material)
            s.seam              = "0.8 cm overlock"
            s.targetQuantity    = 50

        case .toteBag:
            // Standard tote / ecobag
            s.widthCM           = 38
            s.heightCM          = 40
            s.depthCM           = 10
            s.printAreaWidthCM  = 35
            s.printAreaHeightCM = 35
            s.targetDPI         = 150
            s.zipperColor       = ""         // totes typically open top
            s.zipperLengthCM    = 0
            s.zipperType        = ""
            s.strapMaterial     = strapMaterial(material)
            s.strapWidthCM      = 3.0
            s.strapLengthCM     = 55
            s.liningColor       = "Natural"
            s.liningMaterial    = "Sem forro (sem forro padrão)"
            s.seam              = "1.5 cm overlock"
            s.targetQuantity    = 100

        case .beachBag:
            // Large beach / bolsa praia
            s.widthCM           = 45
            s.heightCM          = 38
            s.depthCM           = 15
            s.printAreaWidthCM  = 40
            s.printAreaHeightCM = 35
            s.targetDPI         = 150
            s.zipperColor       = "Dourado"
            s.zipperLengthCM    = 40
            s.zipperType        = "YKK #5 metal ou nylon"
            s.strapMaterial     = strapMaterial(material)
            s.strapWidthCM      = 4.0
            s.strapLengthCM     = 65
            s.liningColor       = "Preto"
            s.liningMaterial    = materialLining(material)
            s.seam              = "1.5 cm overlock"
            s.targetQuantity    = 50

        case .canga:
            // Brazilian beach sarong — standard dimensions
            s.widthCM           = 175
            s.heightCM          = 90
            s.depthCM           = 0          // flat
            s.printAreaWidthCM  = 175
            s.printAreaHeightCM = 90
            s.targetDPI         = 150
            s.zipperColor       = ""
            s.zipperLengthCM    = 0
            s.zipperType        = ""
            s.strapMaterial     = ""
            s.strapWidthCM      = 0
            s.strapLengthCM     = 0
            s.liningColor       = ""
            s.liningMaterial    = "Sem forro — peça única"
            s.seam              = "Bainha dupla 0.5 cm nas 4 bordas"
            s.targetQuantity    = 100

        case .other:
            s.targetDPI      = 150
            s.seam           = "1 cm overlock"
            s.targetQuantity = 50
        }

        // Material overrides
        applyMaterialOverrides(&s, material: material)
        return s
    }

    // MARK: - Helpers

    private static func strapMaterial(_ material: Material) -> String {
        switch material {
        case .canvas12oz:       return "Fita de algodão"
        case .cetimColado:      return "Fita de cetim ou algodão"
        case .polyesterElastano: return "Fita de poliéster"
        case .polyester:        return "Fita de poliéster"
        case .cotton:           return "Fita de algodão"
        case .other:            return "A confirmar com fábrica"
        }
    }

    private static func materialLining(_ material: Material) -> String {
        switch material {
        case .canvas12oz:       return "Oxford 300D ou poliéster"
        case .cetimColado:      return "Poliéster ou cetim liso"
        case .polyesterElastano: return "Sem forro (tecido com elastano)"
        case .polyester:        return "Poliéster liso"
        case .cotton:           return "Algodão liso ou Oxford"
        case .other:            return "A confirmar com fábrica"
        }
    }

    private static func applyMaterialOverrides(_ s: inout ProductionSpecs, material: Material) {
        switch material {
        case .polyesterElastano:
            // Canga/sublimation — higher DPI recommended
            s.targetDPI = 150
            s.seam = s.seam.isEmpty ? "Overlock ou corte a laser nas bordas" : s.seam
        case .cetimColado:
            // Satin print needs bleed
            s.seam = s.seam.isEmpty ? "1 cm overlock + 0.5 cm bleed no cetim" : s.seam
        default:
            break
        }
    }
}
