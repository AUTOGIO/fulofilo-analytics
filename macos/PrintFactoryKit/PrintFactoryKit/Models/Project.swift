import Foundation
import AppKit

enum ProductType: String, CaseIterable, Codable {
    case necessaire = "Necessaire"
    case toteBag = "Tote Bag"
    case beachBag = "Beach Bag"
    case cosmeticPouch = "Cosmetic Pouch"
    case canga = "Canga"
    case other = "Other"
}

enum Material: String, CaseIterable, Codable {
    case canvas12oz = "Canvas 12 oz"
    case cetimColado = "Cetim + Lona (impressão no cetim, colado na lona)"
    case polyesterElastano = "Poliéster com Elastano"
    case cotton = "Cotton"
    case polyester = "Polyester"
    case other = "Other"
}

enum PrintMethod: String, CaseIterable, Codable {
    case digitalTextile = "Digital Textile Print"
    case sublimation = "Sublimation"
    case screenPrint = "Screen Print"
    case other = "Other"
}

struct FactoryProject: Identifiable, Codable {
    let id: UUID
    var projectName: String
    var collectionName: String
    var productType: ProductType
    var material: Material
    var printMethod: PrintMethod
    var factoryName: String
    var notes: String
    var artworkImagePath: String?
    var createdAt: Date
    var projectCode: String
    var specs: ProductionSpecs

    init(
        id: UUID = UUID(),
        projectName: String = "",
        collectionName: String = "",
        productType: ProductType = .necessaire,
        material: Material = .canvas12oz,
        printMethod: PrintMethod = .digitalTextile,
        factoryName: String = "",
        notes: String = "",
        artworkImagePath: String? = nil,
        createdAt: Date = Date(),
        projectCode: String = "",
        specs: ProductionSpecs = ProductionSpecs()
    ) {
        self.id = id
        self.projectName = projectName
        self.collectionName = collectionName
        self.productType = productType
        self.material = material
        self.printMethod = printMethod
        self.factoryName = factoryName
        self.notes = notes
        self.artworkImagePath = artworkImagePath
        self.createdAt = createdAt
        self.projectCode = projectCode
        self.specs = specs
    }

    var folderName: String {
        let safeName = projectName
            .uppercased()
            .replacingOccurrences(of: " ", with: "_")
            .replacingOccurrences(of: "/", with: "-")
            .filter { $0.isLetter || $0.isNumber || $0 == "_" || $0 == "-" }
        return "\(projectCode)_\(safeName)"
    }

    /// Display name preserving original casing for use in documents.
    var displayName: String { projectName }

    /// Humanizes a raw field value for display in salutations and headings.
    /// "CAJU_CACTO_factory" → "Caju Cacto Factory"
    /// "Summer 2026" → "Summer 2026" (unchanged)
    static func humanize(_ raw: String) -> String {
        raw
            .replacingOccurrences(of: "_", with: " ")
            .replacingOccurrences(of: "-", with: " ")
            .split(separator: " ")
            .map { word in
                let s = String(word)
                // If already mixed case, keep it; if ALL CAPS word, title-case it
                let isAllCaps = s == s.uppercased() && s.contains(where: { $0.isLetter })
                return isAllCaps ? (s.prefix(1).uppercased() + s.dropFirst().lowercased()) : s
            }
            .joined(separator: " ")
    }

    var displayFactoryName: String {
        factoryName.isEmpty ? "Factory" : FactoryProject.humanize(factoryName)
    }

    var displayCollectionName: String {
        FactoryProject.humanize(collectionName)
    }
}
