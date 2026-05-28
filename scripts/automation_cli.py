#!/usr/bin/env python3
"""
FulôFiló Automation CLI
=======================
Thin orchestration layer for external tools (including n8n).
All business logic remains in existing modules/scripts.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import polars as pl

ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = ROOT / ".venv" / "bin" / "python3"
SYNC_SCRIPT = ROOT / "scripts" / "sync_excel.sh"
MASTER_XLSX = ROOT / "data" / "excel" / "FuloFilo_Master.xlsx"
PARQUET_DIR = ROOT / "data" / "parquet"
STATUS_JSON = ROOT / "data" / "excel" / "source_sync_status.json"

LOG_DIR = ROOT / "logs" / "automation"
STATE_DIR = ROOT / "data" / "automation"
IDEMPOTENCY_FILE = STATE_DIR / "idempotency_state.json"
LOCK_DIR = STATE_DIR / "locks"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dirs() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LOCK_DIR.mkdir(parents=True, exist_ok=True)


def _json_load(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _json_dump_atomic(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _resolve_fingerprint_inputs(action: str) -> list[Path]:
    if action in {"refresh-dashboard-data", "sync-excel-master", "validate-data-integrity", "run-daily-automation"}:
        return [MASTER_XLSX]
    if action in {"generate-replenishment-alerts", "export-reports"}:
        return sorted(PARQUET_DIR.glob("*.parquet"))
    return []


def _compute_fingerprint(action: str, sku_policy: str) -> str:
    parts = [f"action={action}", f"sku_policy={sku_policy}"]
    for path in _resolve_fingerprint_inputs(action):
        if path.exists():
            stat = path.stat()
            parts.append(f"{path}:{stat.st_size}:{stat.st_mtime_ns}")
        else:
            parts.append(f"{path}:missing")
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return digest


@contextlib.contextmanager
def _command_lock(action: str):
    _ensure_dirs()
    lock_path = LOCK_DIR / f"{action}.lock"
    pid = os.getpid()
    payload = {"pid": pid, "action": action, "started_at": _utc_now()}

    for _ in range(2):
        try:
            fd = os.open(str(lock_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
            break
        except FileExistsError:
            stale = True
            try:
                existing = _json_load(lock_path, {})
                existing_pid = int(existing.get("pid", -1))
                if existing_pid > 0:
                    os.kill(existing_pid, 0)
                    stale = False
            except Exception:
                stale = True
            if stale:
                with contextlib.suppress(FileNotFoundError):
                    lock_path.unlink()
                continue
            raise RuntimeError(
                f"Action '{action}' is already running (lock file: {lock_path})."
            )
    else:
        raise RuntimeError(f"Could not acquire lock for action '{action}'.")

    try:
        yield
    finally:
        with contextlib.suppress(FileNotFoundError):
            lock_path.unlink()


def _configure_logger(action: str, run_id: str) -> tuple[logging.Logger, Path]:
    _ensure_dirs()
    logger = logging.getLogger(f"automation.{action}.{run_id}")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    log_path = LOG_DIR / f"{action}.log"
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger, log_path


def _run_subprocess(cmd: list[str], logger: logging.Logger, label: str) -> dict[str, Any]:
    logger.info("Running step: %s", label)
    logger.info("Command: %s", " ".join(cmd))
    started = time.time()
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    elapsed = round(time.time() - started, 3)
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    if stdout:
        logger.info("%s stdout:\n%s", label, stdout)
    if stderr:
        logger.warning("%s stderr:\n%s", label, stderr)
    if proc.returncode != 0:
        raise RuntimeError(
            f"{label} failed with exit={proc.returncode}. "
            f"Check logs under {LOG_DIR}."
        )
    return {"label": label, "exit_code": proc.returncode, "elapsed_s": elapsed}


def _sync_excel(logger: logging.Logger, sku_policy: str) -> dict[str, Any]:
    result = _run_subprocess(
        ["bash", str(SYNC_SCRIPT), "--sku-policy", sku_policy],
        logger,
        "sync_excel",
    )
    status = _json_load(STATUS_JSON, {})
    return {
        "step": result,
        "status_file": str(STATUS_JSON),
        "status_ok": bool(status.get("ok", False)),
        "status_warnings": status.get("warnings", []),
        "status_errors": status.get("errors", []),
    }


def _generate_replenishment_alerts(logger: logging.Logger) -> dict[str, Any]:
    from app.db import get_conn
    from app.utils.reorder_engine import ALERT_THRESHOLD, LEAD_TIME_DAYS, export_excel, get_alerts

    outputs = ROOT / "data" / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    out_json = outputs / "replenishment_alerts.json"

    conn = get_conn()
    try:
        alerts_df = get_alerts(conn)
        workbook_path = export_excel(conn)
    finally:
        conn.close()

    if alerts_df.empty:
        payload = {
            "generated_at": _utc_now(),
            "total_alerts": 0,
            "urgent_alerts": 0,
            "alert_threshold_days": ALERT_THRESHOLD,
            "urgent_threshold_days": LEAD_TIME_DAYS,
            "top_alerts": [],
            "alert_workbook": str(workbook_path) if workbook_path else None,
        }
    else:
        urgent = alerts_df[alerts_df["days_remaining"] <= LEAD_TIME_DAYS]
        top = alerts_df.head(20).to_dict(orient="records")
        payload = {
            "generated_at": _utc_now(),
            "total_alerts": int(len(alerts_df)),
            "urgent_alerts": int(len(urgent)),
            "alert_threshold_days": ALERT_THRESHOLD,
            "urgent_threshold_days": LEAD_TIME_DAYS,
            "top_alerts": top,
            "alert_workbook": str(workbook_path) if workbook_path else None,
        }

    _json_dump_atomic(out_json, payload)
    logger.info("Replenishment alert JSON saved: %s", out_json)
    return {
        "alert_json": str(out_json),
        "alert_workbook": payload.get("alert_workbook"),
        "total_alerts": payload["total_alerts"],
        "urgent_alerts": payload["urgent_alerts"],
    }


def _export_reports(logger: logging.Logger) -> dict[str, Any]:
    from excel.build_report import build_report
    from reports.weekly_report import generate_abc_report

    products_parquet = PARQUET_DIR / "products.parquet"
    if not products_parquet.exists():
        raise RuntimeError(f"Missing parquet input: {products_parquet}")

    excel_path = build_report()
    logger.info("Excel report generated: %s", excel_path)

    df = pl.read_parquet(products_parquet).to_pandas()
    abc_report = generate_abc_report(df, save_md=True)

    return {
        "excel_report": str(excel_path),
        "abc_report_json": str(ROOT / "data" / "outputs" / "abc_weekly_report.json"),
        "abc_report_md": str(ROOT / "data" / "outputs" / "abc_weekly_report.md"),
        "abc_total_products": int(abc_report.get("metadata", {}).get("total_products", 0)),
    }


def _validate_data_integrity(logger: logging.Logger, run_tests: bool) -> dict[str, Any]:
    steps = []
    steps.append(_sync_excel(logger, sku_policy="strict"))

    if run_tests:
        if not VENV_PYTHON.exists():
            raise RuntimeError(f"Missing Python runtime: {VENV_PYTHON}")
        step = _run_subprocess(
            [str(VENV_PYTHON), "-m", "pytest", "-q", "tests/test_pipeline.py"],
            logger,
            "pytest_pipeline",
        )
        steps.append(step)

    return {"validation_steps": steps}


def _run_daily_automation(logger: logging.Logger, sku_policy: str) -> dict[str, Any]:
    steps = [
        {"action": "refresh-dashboard-data", "details": _sync_excel(logger, sku_policy=sku_policy)},
        {"action": "generate-replenishment-alerts", "details": _generate_replenishment_alerts(logger)},
        {"action": "export-reports", "details": _export_reports(logger)},
    ]
    return {"automation_steps": steps}


def _download_loyverse_daily_sales(logger: logging.Logger, target_date: str, fmt: str, force: bool) -> dict[str, Any]:
    from app.utils.loyverse_automation import run_loyverse_daily_sales_import

    logger.info("Running Loyverse daily sales download: date=%s format=%s force=%s", target_date, fmt, force)
    result = run_loyverse_daily_sales_import(target_date, fmt=fmt, force=force).to_dict()
    if not result.get("ok", False):
        raise RuntimeError(result.get("message") or "Loyverse daily sales download failed.")
    return result


def _download_loyverse_sales_period(logger: logging.Logger, start_date: str, end_date: str, fmt: str, force: bool) -> dict[str, Any]:
    from datetime import date, timedelta

    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if end < start:
        raise ValueError("Period end date must be on or after start date.")

    days = []
    cursor = start
    while cursor <= end:
        day = cursor.isoformat()
        try:
            details = _download_loyverse_daily_sales(logger, target_date=day, fmt=fmt, force=force)
            days.append({"date": day, "ok": True, "status": details.get("status"), "details": details})
        except Exception as exc:
            logger.exception("Loyverse period day failed: %s", day)
            days.append({"date": day, "ok": False, "status": "failed", "error": str(exc)})
            raise
        cursor += timedelta(days=1)

    return {
        "ok": True,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "format": fmt,
        "status": "validated",
        "days": days,
        "message": f"Loyverse period imported and validated: {start.isoformat()} -> {end.isoformat()}",
    }


def _launch_rede_sales_download(logger: logging.Logger, target_date: str, formats: str) -> dict[str, Any]:
    from datetime import date

    from app.utils.rede_automation import launch_rede_sales_download

    clean_formats = [item.strip().lower() for item in formats.split(",") if item.strip()]
    parsed_date = date.fromisoformat(target_date)
    result = launch_rede_sales_download("date", parsed_date, clean_formats)
    logger.info("Rede download launch result: ok=%s message=%s", result.ok, result.message)
    if not result.ok:
        raise RuntimeError(result.message)
    return {
        "ok": True,
        "date": parsed_date.isoformat(),
        "formats": clean_formats or ["csv"],
        "status": "downloaded",
        "launcher_path": str(result.launcher_path) if result.launcher_path else None,
        "message": result.message,
    }


def _load_idempotency_state() -> dict[str, Any]:
    return _json_load(
        IDEMPOTENCY_FILE,
        {"commands": {}, "idempotency_keys": {}},
    )


def _save_idempotency_state(state: dict[str, Any]) -> None:
    _json_dump_atomic(IDEMPOTENCY_FILE, state)


def execute_action(
    action: str,
    *,
    sku_policy: str = "balanced",
    force: bool = False,
    idempotency_key: str | None = None,
    run_tests: bool = True,
    target_date: str | None = None,
    fmt: str = "csv",
) -> dict[str, Any]:
    _ensure_dirs()
    run_id = datetime.now().strftime("%Y%m%dT%H%M%S")
    logger, log_path = _configure_logger(action, run_id)
    fingerprint = _compute_fingerprint(action, sku_policy=sku_policy)
    started = time.time()

    with _command_lock(action):
        state = _load_idempotency_state()
        command_state = state["commands"].get(action, {})

        if not force and idempotency_key:
            idem = state["idempotency_keys"].get(idempotency_key)
            if idem and idem.get("action") == action and idem.get("status") == "success":
                logger.info("Skipping %s due to idempotency key: %s", action, idempotency_key)
                return {
                    "ok": True,
                    "action": action,
                    "skipped": True,
                    "skip_reason": "idempotency_key_already_succeeded",
                    "idempotency_key": idempotency_key,
                    "fingerprint": fingerprint,
                    "log_file": str(log_path),
                }

        if (
            action not in {"download-loyverse-daily-sales", "download-loyverse-sales-period", "launch-rede-sales-download"}
            and
            not force
            and command_state.get("last_status") == "success"
            and command_state.get("last_fingerprint") == fingerprint
        ):
            logger.info("Skipping %s because inputs are unchanged.", action)
            return {
                "ok": True,
                "action": action,
                "skipped": True,
                "skip_reason": "input_fingerprint_unchanged",
                "fingerprint": fingerprint,
                "log_file": str(log_path),
            }

        details: dict[str, Any]
        try:
            if action == "refresh-dashboard-data":
                details = _sync_excel(logger, sku_policy=sku_policy)
            elif action == "sync-excel-master":
                details = _sync_excel(logger, sku_policy=sku_policy)
            elif action == "generate-replenishment-alerts":
                details = _generate_replenishment_alerts(logger)
            elif action == "export-reports":
                details = _export_reports(logger)
            elif action == "validate-data-integrity":
                details = _validate_data_integrity(logger, run_tests=run_tests)
            elif action == "run-daily-automation":
                details = _run_daily_automation(logger, sku_policy=sku_policy)
            elif action == "download-loyverse-daily-sales":
                if not target_date:
                    raise ValueError("Missing required target_date for download-loyverse-daily-sales.")
                details = _download_loyverse_daily_sales(logger, target_date=target_date, fmt=fmt, force=force)
            elif action == "download-loyverse-sales-period":
                if not target_date or ":" not in target_date:
                    raise ValueError("Missing required period as target_date=start:end for download-loyverse-sales-period.")
                start_date, end_date = target_date.split(":", 1)
                details = _download_loyverse_sales_period(logger, start_date=start_date, end_date=end_date, fmt=fmt, force=force)
            elif action == "launch-rede-sales-download":
                if not target_date:
                    raise ValueError("Missing required target_date for launch-rede-sales-download.")
                details = _launch_rede_sales_download(logger, target_date=target_date, formats=fmt)
            else:
                raise ValueError(f"Unsupported action: {action}")

            elapsed = round(time.time() - started, 3)
            state["commands"][action] = {
                "last_status": "success",
                "last_fingerprint": fingerprint,
                "last_run_at": _utc_now(),
                "last_run_id": run_id,
            }
            if idempotency_key:
                state["idempotency_keys"][idempotency_key] = {
                    "action": action,
                    "status": "success",
                    "timestamp": _utc_now(),
                    "run_id": run_id,
                }
            _save_idempotency_state(state)
            return {
                "ok": True,
                "action": action,
                "skipped": False,
                "fingerprint": fingerprint,
                "elapsed_s": elapsed,
                "log_file": str(log_path),
                "details": details,
            }
        except Exception as exc:
            elapsed = round(time.time() - started, 3)
            logger.exception("Action failed: %s", exc)
            state["commands"][action] = {
                "last_status": "failed",
                "last_fingerprint": fingerprint,
                "last_run_at": _utc_now(),
                "last_run_id": run_id,
                "last_error": str(exc),
            }
            if idempotency_key:
                state["idempotency_keys"][idempotency_key] = {
                    "action": action,
                    "status": "failed",
                    "timestamp": _utc_now(),
                    "run_id": run_id,
                }
            _save_idempotency_state(state)
            return {
                "ok": False,
                "action": action,
                "skipped": False,
                "fingerprint": fingerprint,
                "elapsed_s": elapsed,
                "log_file": str(log_path),
                "error": str(exc),
            }


def _add_common_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--force", action="store_true", help="Bypass idempotency checks.")
    parser.add_argument(
        "--idempotency-key",
        type=str,
        default=None,
        help="Stable unique key from orchestrator execution context.",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FulôFiló automation entrypoint for n8n and schedulers.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_refresh = sub.add_parser("refresh-dashboard-data", help="Sync Excel master to refresh dashboard parquet data.")
    p_refresh.add_argument("--sku-policy", choices=("balanced", "strict"), default="balanced")
    _add_common_flags(p_refresh)

    p_sync = sub.add_parser("sync-excel-master", help="Run canonical Excel sync.")
    p_sync.add_argument("--sku-policy", choices=("balanced", "strict"), default="balanced")
    _add_common_flags(p_sync)

    p_alerts = sub.add_parser("generate-replenishment-alerts", help="Generate replenishment alerts artifacts.")
    _add_common_flags(p_alerts)

    p_export = sub.add_parser("export-reports", help="Generate Excel and ABC report artifacts.")
    _add_common_flags(p_export)

    p_validate = sub.add_parser("validate-data-integrity", help="Run strict sync and pipeline tests.")
    p_validate.add_argument("--skip-tests", action="store_true", help="Run strict sync only.")
    _add_common_flags(p_validate)

    p_daily = sub.add_parser("run-daily-automation", help="Run the automatic daily routine: sync, alerts, reports.")
    p_daily.add_argument("--sku-policy", choices=("balanced", "strict"), default="balanced")
    _add_common_flags(p_daily)

    p_loyverse = sub.add_parser("download-loyverse-daily-sales", help="Download and import Loyverse item sales for one day.")
    p_loyverse.add_argument("--date", required=True, dest="target_date", help="Report date as YYYY-MM-DD.")
    p_loyverse.add_argument("--format", choices=("csv", "xlsx", "excel", "pdf"), default="csv")
    _add_common_flags(p_loyverse)

    p_loyverse_period = sub.add_parser("download-loyverse-sales-period", help="Download and import Loyverse item sales day-by-day for a period.")
    p_loyverse_period.add_argument("--from", required=True, dest="period_from", help="Start date as YYYY-MM-DD.")
    p_loyverse_period.add_argument("--to", required=True, dest="period_to", help="End date as YYYY-MM-DD.")
    p_loyverse_period.add_argument("--format", choices=("csv", "xlsx", "excel", "pdf"), default="csv")
    _add_common_flags(p_loyverse_period)

    p_rede = sub.add_parser("launch-rede-sales-download", help="Launch the separate Rede sales download automation.")
    p_rede.add_argument("--date", required=True, dest="target_date", help="Report date as YYYY-MM-DD.")
    p_rede.add_argument("--formats", default="csv", help="Comma-separated Rede formats: csv,excel,pdf.")
    _add_common_flags(p_rede)

    p_server = sub.add_parser("serve-webhook", help="Run local webhook server for n8n HTTP Request nodes.")
    p_server.add_argument("--host", default="127.0.0.1")
    p_server.add_argument("--port", type=int, default=8787)
    p_server.add_argument(
        "--token",
        default=os.environ.get("FULOFILO_AUTOMATION_TOKEN", ""),
        help="Token expected in X-Automation-Token header (optional but recommended).",
    )
    return parser


def _make_handler(token: str):
    def _resolve_request_token(headers) -> str:
        direct = str(headers.get("X-Automation-Token", "")).strip()
        if direct:
            return direct

        auth = str(headers.get("Authorization", "")).strip()
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
        return ""

    class Handler(BaseHTTPRequestHandler):
        server_version = "FulofiloAutomationWebhook/1.0"

        def _json_response(self, payload: dict[str, Any], status: int = 200) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):  # noqa: N802
            if self.path == "/health":
                self._json_response({"ok": True, "service": "fulofilo-automation", "timestamp": _utc_now()})
                return
            self._json_response({"ok": False, "error": "not_found"}, status=404)

        def do_POST(self):  # noqa: N802
            if self.path != "/run":
                self._json_response({"ok": False, "error": "not_found"}, status=404)
                return

            if token:
                incoming = _resolve_request_token(self.headers)
                if incoming != token:
                    self._json_response({"ok": False, "error": "unauthorized"}, status=401)
                    return

            try:
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length) if length > 0 else b"{}"
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                self._json_response({"ok": False, "error": "invalid_json"}, status=400)
                return

            action = str(payload.get("action", "")).strip()
            params = payload.get("params") or {}
            if not action:
                self._json_response({"ok": False, "error": "missing_action"}, status=400)
                return

            result = execute_action(
                action,
                sku_policy=str(params.get("sku_policy", "balanced")),
                force=bool(params.get("force", False)),
                idempotency_key=payload.get("idempotency_key") or self.headers.get("X-Idempotency-Key"),
                run_tests=not bool(params.get("skip_tests", False)),
                target_date=(
                    f"{params.get('from')}:{params.get('to')}"
                    if action == "download-loyverse-sales-period" and params.get("from") and params.get("to")
                    else params.get("date") or params.get("target_date")
                ),
                fmt=str(params.get("formats") or params.get("format", "csv")),
            )
            status = 200 if result.get("ok", False) else 500
            self._json_response(result, status=status)

        def log_message(self, fmt: str, *args: Any) -> None:
            return

    return Handler


def _serve_webhook(host: str, port: int, token: str) -> None:
    server = ThreadingHTTPServer((host, port), _make_handler(token))
    print(f"[automation_webhook] listening on http://{host}:{port}")
    print("[automation_webhook] endpoints: GET /health | POST /run")
    if token:
        print("[automation_webhook] token auth: enabled (X-Automation-Token)")
    else:
        print("[automation_webhook] token auth: disabled")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "serve-webhook":
        _serve_webhook(args.host, args.port, args.token)
        return

    kwargs = {
        "action": args.command,
        "sku_policy": getattr(args, "sku_policy", "balanced"),
        "force": getattr(args, "force", False),
        "idempotency_key": getattr(args, "idempotency_key", None),
        "run_tests": not getattr(args, "skip_tests", False),
        "target_date": (
            f"{args.period_from}:{args.period_to}"
            if hasattr(args, "period_from") and hasattr(args, "period_to")
            else getattr(args, "target_date", None)
        ),
        "fmt": getattr(args, "formats", getattr(args, "format", "csv")),
    }
    result = execute_action(**kwargs)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
