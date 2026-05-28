from __future__ import annotations

import csv
import json
import logging
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent.parent
VENV_PYTHON = ROOT / ".venv" / "bin" / "python3"
IMPORT_SCRIPT = ROOT / "scripts" / "import_sales_summary_to_excel.py"
SYNC_SCRIPT = ROOT / "scripts" / "sync_excel.sh"

LOYVERSE_DATA_ROOT = Path("/Users/eduardofgiovannini/Developer/loyverse-data")
RAW_DIR = LOYVERSE_DATA_ROOT / "raw"
PROCESSED_DIR = LOYVERSE_DATA_ROOT / "processed"
LOG_DIR = LOYVERSE_DATA_ROOT / "logs"

SUPPORTED_FORMATS = {"csv", "xlsx", "pdf"}
EXT_BY_FORMAT = {"csv": "csv", "xlsx": "xlsx", "pdf": "pdf"}
STATE_ORDER = ["idle", "running", "downloaded", "imported", "validated", "failed"]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

REPORT_URL = (
    "https://r.loyverse.com/dashboard/#/report/goods?page=0&limit=10&chart=bar&group=hour"
    "&periodLength=1d&from={date}%2000:00:00&to={date}%2023:59:59"
    "&fromHour=0&toHour=0&outletsIds=all&merchantsIds=all"
)

CANONICAL_COLUMNS = [
    "Item",
    "SKU",
    "Categoria",
    "Itens vendidos",
    "Vendas brutas",
    "Itens reembolsados",
    "Reembolsos",
    "Descontos",
    "Vendas líquidas",
    "Custo das mercadorias",
    "Lucro bruto",
    "Margem",
    "Impostos",
]

COLUMN_ALIASES = {
    "Item": ["Item", "Nome do item", "Nome", "Name"],
    "SKU": ["SKU", "Sku"],
    "Categoria": ["Categoria", "Category"],
    "Itens vendidos": ["Itens vendidos", "Items sold", "Quantidade vendida", "Qty sold"],
    "Vendas brutas": ["Vendas brutas", "Gross sales"],
    "Itens reembolsados": ["Itens reembolsados", "Items refunded"],
    "Reembolsos": ["Reembolsos", "Refunds"],
    "Descontos": ["Descontos", "Discounts"],
    "Vendas líquidas": ["Vendas líquidas", "Net sales", "Vendas liquidas"],
    "Custo das mercadorias": ["Custo das mercadorias", "Cost of goods", "COGS"],
    "Lucro bruto": ["Lucro bruto", "Gross profit"],
    "Margem": ["Margem", "Margin"],
    "Impostos": ["Impostos", "Taxes"],
}


@dataclass(frozen=True)
class LoyverseAutomationResult:
    ok: bool
    date: str
    format: str
    raw_path: str | None
    processed_path: str | None
    status: str
    message: str
    log_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LoyverseAutomationError(RuntimeError):
    def __init__(self, message: str, status: str = "failed") -> None:
        super().__init__(message)
        self.status = status


def run_loyverse_daily_sales_import(date_text: str, fmt: str = "csv", force: bool = False) -> LoyverseAutomationResult:
    target_date = _validate_date(date_text)
    clean_format = _validate_format(fmt)
    raw_path = RAW_DIR / f"loyverse_goods_daily_{target_date}.{EXT_BY_FORMAT[clean_format]}"
    processed_path = PROCESSED_DIR / f"loyverse_goods_daily_{target_date}.csv"
    logger, log_path = _configure_logger(target_date, clean_format)

    logger.info("event=%s date=%s format=%s force=%s", "running", target_date, clean_format, force)
    try:
        _ensure_dirs()
        if raw_path.exists() and not force:
            if raw_path.stat().st_size <= 0:
                raise LoyverseAutomationError(f"Existing file is empty: {raw_path}")
            logger.info("event=downloaded idempotent=true raw_path=%s", raw_path)
        else:
            downloaded = _download_with_playwright(target_date, clean_format, logger)
            _move_download(downloaded, raw_path, force=force)
            logger.info("event=downloaded raw_path=%s size=%s", raw_path, raw_path.stat().st_size)

        _assert_non_empty(raw_path)
        if clean_format == "pdf":
            return LoyverseAutomationResult(
                ok=True,
                date=target_date,
                format=clean_format,
                raw_path=str(raw_path),
                processed_path=None,
                status="downloaded",
                message="PDF baixado e validado. Importação automática requer CSV ou Excel.",
                log_path=str(log_path),
            )

        if processed_path.exists() and not force:
            logger.info("event=imported idempotent=true processed_path=%s", processed_path)
        else:
            normalized = _normalize_to_processed_csv(raw_path, processed_path, target_date)
            logger.info("event=imported processed_path=%s rows=%s", processed_path, normalized)

        _import_processed_csv(processed_path, logger)
        logger.info("event=validated processed_path=%s", processed_path)
        return LoyverseAutomationResult(
            ok=True,
            date=target_date,
            format=clean_format,
            raw_path=str(raw_path),
            processed_path=str(processed_path),
            status="validated",
            message="Loyverse baixado, importado no Excel master e sincronizado.",
            log_path=str(log_path),
        )
    except Exception as exc:
        logger.exception("event=failed error=%s", exc)
        return LoyverseAutomationResult(
            ok=False,
            date=target_date if DATE_RE.match(str(date_text)) else str(date_text),
            format=str(fmt).lower(),
            raw_path=str(raw_path) if "raw_path" in locals() else None,
            processed_path=str(processed_path) if "processed_path" in locals() else None,
            status="failed",
            message=str(exc),
            log_path=str(log_path),
        )


def _validate_date(value: str) -> str:
    text = str(value).strip()
    if not DATE_RE.match(text):
        raise LoyverseAutomationError("invalid date: expected YYYY-MM-DD")
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError as exc:
        raise LoyverseAutomationError("invalid date: expected real calendar date YYYY-MM-DD") from exc
    return text


def _validate_format(value: str) -> str:
    text = str(value).strip().lower()
    if text == "excel":
        text = "xlsx"
    if text not in SUPPORTED_FORMATS:
        raise LoyverseAutomationError(f"unsupported format: {value}. Expected one of csv, xlsx, pdf")
    return text


def _ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _configure_logger(target_date: str, fmt: str) -> tuple[logging.Logger, Path]:
    _ensure_dirs()
    run_id = datetime.now().strftime("%Y%m%dT%H%M%S")
    log_path = LOG_DIR / f"loyverse_goods_daily_{target_date}_{fmt}_{run_id}.jsonl"
    logger = logging.getLogger(f"loyverse.{target_date}.{fmt}.{run_id}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    class JsonlFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            payload = {
                "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "level": record.levelname,
                "message": record.getMessage(),
            }
            if record.exc_info:
                payload["exception"] = self.formatException(record.exc_info)
            return json.dumps(payload, ensure_ascii=False)

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(JsonlFormatter())
    logger.addHandler(handler)
    return logger, log_path


def _download_with_playwright(target_date: str, fmt: str, logger: logging.Logger) -> Path:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as exc:
        raise LoyverseAutomationError(
            "Playwright is not installed. Run: cd /Users/eduardofgiovannini/Documents/GitHub/fulofilo-analytics && uv add playwright && uv run playwright install chromium"
        ) from exc

    cdp_url = "http://127.0.0.1:9222"
    report_url = REPORT_URL.format(date=target_date)
    download_dir = Path(tempfile.mkdtemp(prefix="loyverse-download-"))
    try:
        try:
            with sync_playwright() as p:
                try:
                    browser = p.chromium.connect_over_cdp(cdp_url)
                except PlaywrightError as exc:
                    raise LoyverseAutomationError(
                        "browser not open for automation. Start Chrome with: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222 --user-data-dir=/Users/eduardofgiovannini/Developer/loyverse-data/chrome-profile"
                    ) from exc

                context = browser.contexts[0] if browser.contexts else browser.new_context(accept_downloads=True)
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(report_url, wait_until="domcontentloaded", timeout=45_000)
                page.wait_for_load_state("networkidle", timeout=45_000)
                if _session_expired(page):
                    raise LoyverseAutomationError("Loyverse session expired. Log in manually, then retry.")

                export = page.locator("#export-button")
                if export.count() == 0:
                    export = page.get_by_role("button", name=re.compile("Exportar|Export", re.I))
                if export.count() == 0:
                    export = page.get_by_text(re.compile("^\\s*(Exportar|Export)\\s*$", re.I))
                if export.count() == 0:
                    raise LoyverseAutomationError("export button not found")

                with page.expect_download(timeout=60_000) as download_info:
                    export.first.click(timeout=15_000)
                    _click_format_choice(page, fmt)
                download = download_info.value
                suggested = download.suggested_filename or f"loyverse-download.{EXT_BY_FORMAT[fmt]}"
                temp_path = download_dir / suggested
                download.save_as(str(temp_path))
                _assert_non_empty(temp_path)
                browser.close()
                return temp_path
        except PlaywrightTimeoutError as exc:
            raise LoyverseAutomationError("download timeout") from exc
    except Exception:
        shutil.rmtree(download_dir, ignore_errors=True)
        raise


def _session_expired(page: Any) -> bool:
    url = page.url.lower()
    if "login" in url or "signin" in url:
        return True
    login_fields = page.locator("input[type='password']")
    return login_fields.count() > 0


def _click_format_choice(page: Any, fmt: str) -> None:
    labels = {
        "csv": ["CSV", "Exportar CSV", "Export CSV"],
        "xlsx": ["Excel", "XLSX", "Exportar Excel", "Export Excel"],
        "pdf": ["PDF", "Exportar PDF", "Export PDF"],
    }[fmt]
    for label in labels:
        locator = page.get_by_text(re.compile(f"^\\s*{re.escape(label)}\\s*$", re.I))
        if locator.count() > 0:
            locator.first.click(timeout=10_000)
            return
    # Some Loyverse accounts immediately download the last selected export type.


def _move_download(downloaded: Path, target: Path, force: bool) -> None:
    if target.exists():
        if not force:
            return
        target.unlink()
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(downloaded), str(target))


def _assert_non_empty(path: Path) -> None:
    if not path.exists():
        raise LoyverseAutomationError(f"downloaded file not found: {path}")
    if path.stat().st_size <= 0:
        raise LoyverseAutomationError(f"empty file: {path}")


def _normalize_to_processed_csv(raw_path: Path, processed_path: Path, target_date: str) -> int:
    if raw_path.suffix.lower() == ".csv":
        df = pd.read_csv(raw_path, encoding="utf-8-sig")
    elif raw_path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(raw_path, engine="openpyxl")
    else:
        raise LoyverseAutomationError("unsupported format for import; use csv or xlsx")

    normalized = pd.DataFrame()
    for canonical, aliases in COLUMN_ALIASES.items():
        match = next((col for col in aliases if col in df.columns), None)
        normalized[canonical] = df[match] if match else _default_column(canonical)

    normalized = normalized[CANONICAL_COLUMNS]
    normalized = normalized[normalized["Item"].astype(str).str.strip() != ""].copy()
    normalized = normalized[normalized["SKU"].astype(str).str.strip() != ""].copy()
    normalized = normalized[pd.to_numeric(normalized["Itens vendidos"], errors="coerce").fillna(0) > 0]
    if normalized.empty:
        raise LoyverseAutomationError("downloaded file has no importable sales rows")

    processed_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = processed_path.with_suffix(".tmp")
    normalized.to_csv(tmp, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    tmp.replace(processed_path)
    dated_copy = processed_path.parent / f"item_sales_summary_{target_date}_{target_date}.csv"
    shutil.copy2(processed_path, dated_copy)
    return int(normalized.shape[0])


def _default_column(canonical: str) -> Any:
    if canonical in {"Item", "SKU", "Categoria"}:
        return ""
    if canonical == "Margem":
        return "0.00%"
    return 0


def _import_processed_csv(processed_path: Path, logger: logging.Logger) -> None:
    dated_import = processed_path.parent / _import_filename(processed_path.name)
    if dated_import != processed_path:
        shutil.copy2(processed_path, dated_import)
    runner = VENV_PYTHON if VENV_PYTHON.exists() else Path(sys.executable)
    for cmd, label in [
        ([str(runner), str(IMPORT_SCRIPT), str(dated_import)], "import_sales_summary_to_excel"),
        (["bash", str(SYNC_SCRIPT)], "sync_excel"),
    ]:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        logger.info("event=subprocess label=%s exit=%s stdout=%s stderr=%s", label, proc.returncode, proc.stdout.strip(), proc.stderr.strip())
        if proc.returncode != 0:
            raise LoyverseAutomationError(f"{label} failed: {(proc.stderr or proc.stdout).strip()}")


def _import_filename(name: str) -> str:
    match = re.search(r"(\d{4}-\d{2}-\d{2})", name)
    if not match:
        return name
    day = match.group(1)
    return f"item_sales_summary_{day}_{day}.csv"
