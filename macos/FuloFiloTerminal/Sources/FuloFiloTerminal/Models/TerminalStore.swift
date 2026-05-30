import Foundation
import SwiftUI

@MainActor
@Observable
final class TerminalStore {
    struct ReadModelSnapshot: Decodable {
        struct Meta: Decodable {
            let generated_at: String
            let data_version: String
            let last_sync_label: String
            let ok: Bool
        }
        struct Executive: Decodable {
            let revenue_fmt: String
            let margin_pct: Double
            let profit_fmt: String
            let avg_ticket_fmt: String
            let units: Double
            let cash_net_fmt: String
            let cash_in: Double
            let cash_out: Double
            let inv_value_fmt: String
            let active_skus: Int
            let low_critical: Int
            let low_warn: Int
            let ops_score: Int
            let readiness: String
            let avg_turnover: Double
            let sell_through: Double
            let burn_ratio: Double
            let fixed_total: Double
            let healthy_skus: Int
        }

        struct InventoryMatrixRow: Decodable {
            let name: String
            let healthy: Double
            let watch: Double
            let risk: Double
        }

        struct SalesSeriesPoint: Decodable {
            let label: String
            let revenue: Double
            let units: Double
        }

        struct BubbleRow: Decodable {
            let sku: String
            let category: String
            let volume: Double
            let margin: Double
            let revenue: Double
        }

        struct InsightRow: Decodable {
            let code: String
            let text: String
            let detail: String
            let accent: String
        }

        struct AnomalyRow: Decodable {
            let code: String
            let kind: String
            let text: String
            let accent: String
        }

        struct ContractRow: Decodable {
            let k: String
            let v: String
        }

        struct ABCItem: Decodable {
            let name: String
            let revenue: Double
            let margin_pct: Double
        }

        struct ABCSummary: Decodable {
            let a_count: Int
            let a_revenue_pct: Double
            let b_count: Int
            let b_revenue_pct: Double
            let c_count: Int
            let c_revenue_pct: Double
            let top_a: [ABCItem]
            let top_b: [ABCItem]
            let top_c: [ABCItem]
        }

        let meta: Meta
        let executive: Executive
        let inventory_matrix: [InventoryMatrixRow]
        let sales_series: [SalesSeriesPoint]
        let bubbles: [BubbleRow]
        let abc_summary: ABCSummary?
        let insights: [InsightRow]
        let anomalies: [AnomalyRow]
        let contract: [ContractRow]
    }

    enum SyncState: String {
        case idle = "SYNCED"
        case running = "SYNCING"
        case failed = "FAILED"
    }

    var snapshot: ReadModelSnapshot?
    var readModelState: String = "MOCK"

    var syncState: SyncState = .idle
    var syncTimestamp: String = "—"
    var lastSyncError: String?

    var commandText: String = ""
    var lastActionMessage: String?

    var headerStatus: [StatusMetric] {
        let revenue = snapshot?.executive.revenue_fmt ?? "R,079"
        let cashNet = snapshot?.executive.cash_net_fmt ?? "R025,900"
        let cashIn = snapshot?.executive.cash_in ?? 0
        let cashOut = snapshot?.executive.cash_out ?? 25_900
        let inv = snapshot?.executive.inv_value_fmt ?? "R$ 185,407"
        let skus = snapshot?.executive.active_skus ?? 72
        let ops = snapshot?.executive.ops_score ?? 93
        let readiness = snapshot?.executive.readiness ?? "READY"
        let lastSync = snapshot?.meta.last_sync_label ?? syncTimestamp

        return [
            StatusMetric(title: "DAILY REVENUE", value: revenue, subtitle: "selected operating window", accent: TerminalColors.green),
            StatusMetric(title: "CASHFLOW STATUS", value: cashNet, subtitle: "in \(formatMoney(cashIn)) / out \(formatMoney(cashOut))", accent: cashNet.contains("-") ? TerminalColors.red : TerminalColors.green),
            StatusMetric(title: "INVENTORY VALUATION", value: inv, subtitle: "\(skus) active SKUs", accent: TerminalColors.cyan),
            StatusMetric(title: "OPERATIONAL HEALTH", value: "\(ops)/100", subtitle: readiness, accent: ops >= 80 ? TerminalColors.green : TerminalColors.amber),
            StatusMetric(title: "SYNC STATUS", value: syncState.rawValue, subtitle: lastSync, accent: syncState == .failed ? TerminalColors.red : (syncState == .running ? TerminalColors.amber : TerminalColors.green)),
            StatusMetric(title: "AI ASSISTANT", value: "WATCH", subtitle: "rules engine online", accent: TerminalColors.cyan)
        ]
    }

    var insightRows: [Insight] {
        guard let snap = snapshot, !snap.insights.isEmpty else { return MockData.insights }
        return snap.insights.map { r in
            Insight(code: r.code, text: r.text, detail: r.detail, accent: colorFromToken(r.accent))
        }
    }

    var anomalyRows: [Anomaly] {
        guard let snap = snapshot, !snap.anomalies.isEmpty else { return MockData.anomalies }
        return snap.anomalies.map { r in
            Anomaly(code: r.code, kind: r.kind, text: r.text, accent: colorFromToken(r.accent))
        }
    }

    var contractRows: [(String, String)] {
        guard let snap = snapshot, !snap.contract.isEmpty else { return MockData.contractRows }
        return snap.contract.map { ($0.k, $0.v) }
    }

    var abcSummary: ReadModelSnapshot.ABCSummary? {
        snapshot?.abc_summary
    }

    func refreshReadModel() async {
        do {
            let data = try await ProcessRunner.runJSON(
                executable: pythonPath(),
                arguments: [repoPath("tools/terminal_read_model.py")],
                environment: ["FULO_REPO_ROOT": repoRoot()],
                currentDirectory: repoRoot()
            )
            let decoded = try JSONDecoder().decode(ReadModelSnapshot.self, from: data)
            snapshot = decoded
            readModelState = "READ MODEL"
        } catch {
            snapshot = nil
            readModelState = "MOCK"
            lastSyncError = "\(error)"
        }
    }

    func runCommand(_ raw: String) async {
        let cmd = raw.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        guard !cmd.isEmpty else { return }

        if cmd.hasPrefix("SYNC") {
            await runSync()
            return
        }

        if cmd.hasPrefix("VALIDATE") {
            let fast = cmd.contains("FAST")
            await runValidate(skipTests: fast)
            return
        }
    }

    func runDailyAutomation() async {
        syncState = .running
        lastSyncError = nil
        lastActionMessage = nil
        syncTimestamp = timestampNow()

        do {
            _ = try await ProcessRunner.run(
                executable: pythonPath(),
                arguments: ["scripts/automation_cli.py", "run-daily-automation"],
                environment: ["FULO_REPO_ROOT": repoRoot()],
                currentDirectory: repoRoot()
            )
            syncState = .idle
            syncTimestamp = timestampNow()
            lastActionMessage = "Automation completed."
            await refreshReadModel()
        } catch {
            syncState = .failed
            syncTimestamp = timestampNow()
            lastSyncError = "\(error)"
        }
    }

    func runSync() async {
        syncState = .running
        lastSyncError = nil
        lastActionMessage = nil
        syncTimestamp = timestampNow()

        do {
            _ = try await ProcessRunner.run(
                executable: "/bin/bash",
                arguments: ["scripts/sync_excel.sh"],
                environment: ["FULO_REPO_ROOT": repoRoot()],
                currentDirectory: repoRoot()
            )
            syncState = .idle
            syncTimestamp = timestampNow()
            lastActionMessage = "Sync completed."
            await refreshReadModel()
        } catch {
            syncState = .failed
            syncTimestamp = timestampNow()
            lastSyncError = "\(error)"
        }
    }

    func runValidate(skipTests: Bool) async {
        syncState = .running
        lastSyncError = nil
        lastActionMessage = nil
        syncTimestamp = timestampNow()

        do {
            var args = ["scripts/automation_cli.py", "validate-data-integrity"]
            if skipTests {
                args.append("--skip-tests")
            }
            _ = try await ProcessRunner.run(
                executable: pythonPath(),
                arguments: args,
                environment: ["FULO_REPO_ROOT": repoRoot()],
                currentDirectory: repoRoot()
            )
            syncState = .idle
            syncTimestamp = timestampNow()
            lastActionMessage = skipTests ? "Validation completed (tests skipped)." : "Validation completed."
            await refreshReadModel()
        } catch {
            syncState = .failed
            syncTimestamp = timestampNow()
            lastSyncError = "\(error)"
        }
    }

    func launchRedeDownload(targetDate: Date, formats: [String], force: Bool) async {
        syncState = .running
        lastSyncError = nil
        lastActionMessage = nil
        syncTimestamp = timestampNow()

        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        let dateString = f.string(from: targetDate)
        let cleanFormats = formats.isEmpty ? "csv" : formats.joined(separator: ",")

        do {
            var args = [
                "scripts/automation_cli.py",
                "launch-rede-sales-download",
                "--date",
                dateString,
                "--formats",
                cleanFormats
            ]
            if force {
                args.append("--force")
            }
            let out = try await ProcessRunner.run(
                executable: pythonPath(),
                arguments: args,
                environment: ["FULO_REPO_ROOT": repoRoot()],
                currentDirectory: repoRoot()
            )
            syncState = .idle
            syncTimestamp = timestampNow()
            let raw = (String(data: out, encoding: .utf8) ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
            lastActionMessage = raw.contains("\"status\": \"downloaded\"") ? "Rede download launched." : raw
        } catch {
            syncState = .failed
            syncTimestamp = timestampNow()
            lastSyncError = "\(error)"
        }
    }

    func launchLoyverseDownload(mode: String, targetDate: Date, endDate: Date, format: String, force: Bool) async {
        syncState = .running
        lastSyncError = nil
        lastActionMessage = nil
        syncTimestamp = timestampNow()

        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        let dateString = f.string(from: targetDate)
        let endDateString = f.string(from: endDate)
        let cleanFormat = format.isEmpty ? "csv" : format

        do {
            var args: [String]
            if mode == "period" {
                args = [
                    "scripts/automation_cli.py",
                    "download-loyverse-sales-period",
                    "--from",
                    dateString,
                    "--to",
                    endDateString,
                    "--format",
                    cleanFormat
                ]
            } else {
                args = [
                    "scripts/automation_cli.py",
                    "download-loyverse-daily-sales",
                    "--date",
                    dateString,
                    "--format",
                    cleanFormat
                ]
            }
            if force {
                args.append("--force")
            }
            let out = try await ProcessRunner.run(
                executable: pythonPath(),
                arguments: args,
                environment: ["FULO_REPO_ROOT": repoRoot()],
                currentDirectory: repoRoot()
            )
            syncState = .idle
            syncTimestamp = timestampNow()
            let raw = (String(data: out, encoding: .utf8) ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
            lastActionMessage = raw.contains("\"status\": \"validated\"") ? "Loyverse sales validated." : raw
            await refreshReadModel()
        } catch {
            syncState = .failed
            syncTimestamp = timestampNow()
            lastSyncError = "\(error)"
        }
    }

    private func repoRoot() -> String {
        // 1. Check environment variable (highest priority)
        if let env = ProcessInfo.processInfo.environment["FULO_REPO_ROOT"], !env.isEmpty {
            return env
        }
        
        // 2. Search up directory tree from current working directory for repo markers
        var searchPath = FileManager.default.currentDirectoryPath
        let fm = FileManager.default
        
        // Search up to 10 levels for Package.swift or .git directory
        for _ in 0..<10 {
            // Check for macos/FuloFiloTerminal/Package.swift (indicates this is inside the repo)
            let packagePath = (searchPath as NSString).appendingPathComponent("macos/FuloFiloTerminal/Package.swift")
            if fm.fileExists(atPath: packagePath) {
                return searchPath
            }
            
            // Check for .git directory (repo root marker)
            let gitPath = (searchPath as NSString).appendingPathComponent(".git")
            if fm.fileExists(atPath: gitPath) {
                return searchPath
            }
            
            // Check for distinctive repo files (DOCUMENTATION.md, pyproject.toml)
            let docPath = (searchPath as NSString).appendingPathComponent("DOCUMENTATION.md")
            let pyPath = (searchPath as NSString).appendingPathComponent("pyproject.toml")
            if fm.fileExists(atPath: docPath) || fm.fileExists(atPath: pyPath) {
                return searchPath
            }
            
            // Move up one directory
            let parent = (searchPath as NSString).deletingLastPathComponent
            if parent == searchPath {
                // Reached filesystem root, stop searching
                break
            }
            searchPath = parent
        }
        
        // 3. Fallback: try common clone locations
        let homePath = NSHomeDirectory()
        let commonPaths = [
            (homePath as NSString).appendingPathComponent("Documents/GitHub/fulofilo-analytics"),
            (homePath as NSString).appendingPathComponent("Documents/fulofilo-analytics"),
            (homePath as NSString).appendingPathComponent("code/fulofilo-analytics"),
            (homePath as NSString).appendingPathComponent("fulofilo-analytics"),
            "/opt/fulofilo-analytics"
        ]
        
        for path in commonPaths {
            let packagePath = (path as NSString).appendingPathComponent("macos/FuloFiloTerminal/Package.swift")
            if fm.fileExists(atPath: packagePath) {
                return path
            }
        }
        
        // 4. Last resort: return current directory (will fail gracefully with clear error)
        return FileManager.default.currentDirectoryPath
    }

    private func repoPath(_ relative: String) -> String {
        (repoRoot() as NSString).appendingPathComponent(relative)
    }

    private func pythonPath() -> String {
        let venv = repoPath(".venv/bin/python3")
        if FileManager.default.isExecutableFile(atPath: venv) {
            return venv
        }
        return "/usr/bin/python3"
    }

    private func timestampNow() -> String {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd HH:mm:ss"
        return f.string(from: Date())
    }

    private func formatMoney(_ v: Double) -> String {
        let iv = Int(v.rounded())
        let nf = NumberFormatter()
        nf.numberStyle = .decimal
        nf.groupingSeparator = "."
        nf.decimalSeparator = ","
        let s = nf.string(from: NSNumber(value: iv)) ?? "\(iv)"
        return "R$ \(s)"
    }

    private func colorFromToken(_ t: String) -> Color {
        switch t.lowercased() {
        case "amber": return TerminalColors.amber
        case "orange": return TerminalColors.orange
        case "green": return TerminalColors.green
        case "red": return TerminalColors.red
        case "cyan": return TerminalColors.cyan
        case "blue": return TerminalColors.blue
        default: return TerminalColors.muted
        }
    }
}

enum ProcessRunner {
    struct ProcessError: LocalizedError {
        let message: String
        var errorDescription: String? { message }
    }

    static func run(executable: String, arguments: [String], environment: [String: String] = [:], currentDirectory: String? = nil) async throws -> Data {
        let (data, status) = try await runRaw(executable: executable, arguments: arguments, environment: environment, currentDirectory: currentDirectory)
        guard status == 0 else {
            let s = String(data: data, encoding: .utf8) ?? ""
            throw ProcessError(message: "Process failed (\(status)): \(executable) \(arguments.joined(separator: " "))\n\(s)")
        }
        return data
    }

    static func runJSON(executable: String, arguments: [String], environment: [String: String] = [:], currentDirectory: String? = nil) async throws -> Data {
        let (data, status) = try await runRaw(executable: executable, arguments: arguments, environment: environment, currentDirectory: currentDirectory)
        guard status == 0 else {
            let s = String(data: data, encoding: .utf8) ?? ""
            throw ProcessError(message: "Read-model failed (\(status)): \(s)")
        }
        return data
    }

    private static func runRaw(executable: String, arguments: [String], environment: [String: String], currentDirectory: String?) async throws -> (Data, Int32) {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: executable)
        p.arguments = arguments
        if let currentDirectory {
            p.currentDirectoryURL = URL(fileURLWithPath: currentDirectory)
        }
        var env = ProcessInfo.processInfo.environment
        for (k, v) in environment { env[k] = v }
        p.environment = env

        let out = Pipe()
        let err = Pipe()
        p.standardOutput = out
        p.standardError = err

        try p.run()

        return try await withCheckedThrowingContinuation { cont in
            p.terminationHandler = { proc in
                let stdout = out.fileHandleForReading.readDataToEndOfFile()
                let stderr = err.fileHandleForReading.readDataToEndOfFile()
                let merged = stdout + (stderr.isEmpty ? Data() : Data("\n".utf8) + stderr)
                cont.resume(returning: (merged, proc.terminationStatus))
            }
        }
    }
}
