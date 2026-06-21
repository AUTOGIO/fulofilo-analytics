import Foundation

final class FileSystemService {

    static let shared = FileSystemService()
    private init() {}

    var baseDirectory: URL {
        AppSettings.shared.outputFolder
    }

    private let subfolders = [
        "00_BRIEF",
        "03_MASTER_ARTWORK",
        "04_PATTERN_SYSTEM/seamless_repeat",
        "04_PATTERN_SYSTEM/sparse_repeat",
        "08_FACTORY_PACKAGE/09_ORIGINAL_ARTWORK_IMAGE",
        "08_FACTORY_PACKAGE/10_VECTOR_AND_REPEAT",
        "09_EXPORT"
    ]

    func ensureBaseDirectoryExists() throws {
        try FileManager.default.createDirectory(at: baseDirectory, withIntermediateDirectories: true)
    }

    func nextProjectNumber() -> Int {
        let fm = FileManager.default
        guard let contents = try? fm.contentsOfDirectory(atPath: baseDirectory.path) else { return 1 }
        let prefix = AppSettings.shared.projectPrefix
        let numbers = contents.compactMap { name -> Int? in
            guard name.hasPrefix(prefix) else { return nil }
            let parts = name.components(separatedBy: "_")
            // prefix may itself contain underscores — number is always the last numeric segment before name
            return parts.compactMap { Int($0) }.first
        }
        return (numbers.max() ?? 0) + 1
    }

    func makeProjectCode(year: Int, number: Int) -> String {
        let prefix = AppSettings.shared.projectPrefix
        return String(format: "%@_%04d_%03d", prefix, year, number)
    }

    func createProjectFolder(for project: FactoryProject) throws -> URL {
        try ensureBaseDirectoryExists()
        let projectURL = baseDirectory.appendingPathComponent(project.folderName, isDirectory: true)

        var finalURL = projectURL
        if FileManager.default.fileExists(atPath: finalURL.path) {
            let suffix = Int(Date().timeIntervalSince1970)
            finalURL = baseDirectory.appendingPathComponent(project.folderName + "_\(suffix)", isDirectory: true)
        }

        for sub in subfolders {
            let subURL = finalURL.appendingPathComponent(sub, isDirectory: true)
            try FileManager.default.createDirectory(at: subURL, withIntermediateDirectories: true)
        }

        return finalURL
    }

    func copyArtwork(from sourcePath: String, into projectFolder: URL) throws -> URL {
        let source = URL(fileURLWithPath: sourcePath)
        let filename = source.lastPathComponent
        let dest = projectFolder
            .appendingPathComponent("03_MASTER_ARTWORK")
            .appendingPathComponent(filename)
        if !FileManager.default.fileExists(atPath: dest.path) {
            try FileManager.default.copyItem(at: source, to: dest)
        }
        return dest
    }

    func writeText(_ text: String, to url: URL) throws {
        try text.write(to: url, atomically: true, encoding: .utf8)
    }

    func writeData(_ data: Data, to url: URL) throws {
        try data.write(to: url, options: .atomic)
    }
}
