import Foundation
import AppKit

/// Persistent user preferences — output folder and project prefix.
/// Stored in UserDefaults so they survive app restarts.
final class AppSettings: ObservableObject {

    static let shared = AppSettings()

    @Published var outputFolder: URL {
        didSet { UserDefaults.standard.set(outputFolder.path, forKey: "outputFolder") }
    }

    @Published var projectPrefix: String {
        didSet { UserDefaults.standard.set(projectPrefix, forKey: "projectPrefix") }
    }

    /// True after the user completes first-launch setup
    @Published var isConfigured: Bool {
        didSet { UserDefaults.standard.set(isConfigured, forKey: "isConfigured") }
    }

    private init() {
        let defaultFolder = FileManager.default
            .urls(for: .documentDirectory, in: .userDomainMask).first!
            .appendingPathComponent("FACTORY_PROJECTS", isDirectory: true)

        if let saved = UserDefaults.standard.string(forKey: "outputFolder") {
            outputFolder = URL(fileURLWithPath: saved)
        } else {
            outputFolder = defaultFolder
        }

        projectPrefix = UserDefaults.standard.string(forKey: "projectPrefix") ?? "PRINT"
        isConfigured  = UserDefaults.standard.bool(forKey: "isConfigured")
    }

    func browseForFolder() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.canCreateDirectories = true
        panel.prompt = "Select Output Folder"
        panel.message = "Choose where PrintFactoryKit will save all project folders"
        if panel.runModal() == .OK, let url = panel.url {
            outputFolder = url
        }
    }

    func reset() {
        UserDefaults.standard.removeObject(forKey: "outputFolder")
        UserDefaults.standard.removeObject(forKey: "projectPrefix")
        UserDefaults.standard.removeObject(forKey: "isConfigured")
        let defaultFolder = FileManager.default
            .urls(for: .documentDirectory, in: .userDomainMask).first!
            .appendingPathComponent("FACTORY_PROJECTS", isDirectory: true)
        outputFolder  = defaultFolder
        projectPrefix = "PRINT"
        isConfigured  = false
    }
}
