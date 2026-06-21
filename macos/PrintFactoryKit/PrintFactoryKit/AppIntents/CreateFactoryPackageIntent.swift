import AppIntents
import Foundation

// TODO: Phase 6 — Full Shortcuts integration
// This placeholder compiles but the intent is not yet wired up.
// Full implementation requires testing in Shortcuts.app with proper entitlements.

@available(macOS 13.0, *)
struct CreateFactoryPackageIntent: AppIntent {
    static var title: LocalizedStringResource = "Create Factory Package"
    static var description = IntentDescription("Generate a PrintFactoryKit factory package from an artwork image.")

    @Parameter(title: "Project Name")
    var projectName: String

    @Parameter(title: "Product Type", default: "Necessaire")
    var productType: String

    func perform() async throws -> some ReturnsValue<String> {
        let message = """
        PrintFactoryKit — Create Factory Package
        Project: \(projectName) | Product: \(productType)
        Please open PrintFactoryKit.app to generate the full package.
        Full Shortcuts automation coming in a future version.
        """
        return .result(value: message)
    }
}
