import Foundation

final class ZipExportService {

    static let shared = ZipExportService()
    private init() {}

    func createZip(sourceDirectory: URL, outputURL: URL) throws {
        // Collect only non-empty files (skip empty folders and .DS_Store)
        let fm = FileManager.default
        guard let enumerator = fm.enumerator(
            at: sourceDirectory,
            includingPropertiesForKeys: [.isRegularFileKey, .fileSizeKey],
            options: [.skipsHiddenFiles]
        ) else { throw ZipError.processFailed("Cannot enumerate source directory") }

        var relativePaths: [String] = []
        for case let fileURL as URL in enumerator {
            let attrs = try fileURL.resourceValues(forKeys: [.isRegularFileKey, .fileSizeKey])
            guard attrs.isRegularFile == true else { continue }
            let size = attrs.fileSize ?? 0
            guard size > 0 else { continue }  // skip empty files
            let relative = String(fileURL.path.dropFirst(sourceDirectory.path.count + 1))
            relativePaths.append(relative)
        }

        guard !relativePaths.isEmpty else {
            throw ZipError.processFailed("No files to zip in \(sourceDirectory.path)")
        }

        // Build zip with explicit file list to exclude empty folders
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/zip")
        process.arguments = [outputURL.path] + relativePaths
        process.currentDirectoryURL = sourceDirectory

        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe

        try process.run()
        process.waitUntilExit()

        guard process.terminationStatus == 0 else {
            let output = String(data: pipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
            throw ZipError.processFailed("zip exited with status \(process.terminationStatus): \(output)")
        }

        guard fm.fileExists(atPath: outputURL.path) else {
            throw ZipError.zipNotFound(outputURL.path)
        }

        print("[ZipExportService] ZIP created at: \(outputURL.path) — \(relativePaths.count) files")
    }

    enum ZipError: LocalizedError {
        case processFailed(String)
        case zipNotFound(String)
        var errorDescription: String? {
            switch self {
            case .processFailed(let msg): return "ZIP process failed: \(msg)"
            case .zipNotFound(let path): return "ZIP not found at: \(path)"
            }
        }
    }
}
