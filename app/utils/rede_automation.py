from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path


REDE_AUTOMATION_ROOT = Path("/Users/eduardofgiovannini/Developer/rede-automation")
REDE_SCRIPT = REDE_AUTOMATION_ROOT / "scripts" / "rede-vendas.mjs"
REDE_DOWNLOAD_DIR = Path("/Users/eduardofgiovannini/Downloads/Rede")
LAUNCHER_DIR = Path("/Users/eduardofgiovannini/Developer/rede-automation/.dashboard-launchers")
SUPPORTED_FORMATS = {"csv", "excel", "pdf"}


@dataclass(frozen=True)
class RedeLaunchResult:
    ok: bool
    message: str
    launcher_path: Path | None = None


def launch_rede_sales_download(date_mode: str, target_date: date | None, formats: list[str]) -> RedeLaunchResult:
    """Launch Rede automation in a macOS Terminal window.

    Running it in Terminal preserves the manual-security flow for CAPTCHA, token,
    or 2FA prompts. This function only triggers the downloader; it does not
    import Rede files into the Fulofilo canonical data pipeline.
    """
    if not REDE_AUTOMATION_ROOT.exists() or not REDE_SCRIPT.exists():
        return RedeLaunchResult(
            ok=False,
            message=f"Rede automation project not found at {REDE_AUTOMATION_ROOT}",
        )

    clean_formats = sorted({fmt.strip().lower() for fmt in formats if fmt.strip()})
    if not clean_formats:
        clean_formats = ["csv"]
    invalid = [fmt for fmt in clean_formats if fmt not in SUPPORTED_FORMATS]
    if invalid:
        return RedeLaunchResult(ok=False, message=f"Unsupported Rede format(s): {', '.join(invalid)}")

    date_args = _date_args(date_mode, target_date)
    command = [
        "cd /Users/eduardofgiovannini/Developer/rede-automation",
        f"npm run rede:vendas -- {' '.join(date_args)} --formats {','.join(clean_formats)}",
        'echo ""',
        'echo "Rede automation finished. Press ENTER to close this window."',
        "read -r _",
    ]

    REDE_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    LAUNCHER_DIR.mkdir(parents=True, exist_ok=True)
    launcher_path = LAUNCHER_DIR / f"rede-vendas-{date.today().isoformat()}-{_safe_suffix(date_args)}.command"
    launcher_path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + "\n".join(command) + "\n", encoding="utf-8")
    launcher_path.chmod(0o755)

    result = subprocess.run(["/usr/bin/open", str(launcher_path)], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        error = (result.stderr or result.stdout or "macOS open command failed").strip()
        return RedeLaunchResult(ok=False, message=error, launcher_path=launcher_path)

    return RedeLaunchResult(
        ok=True,
        message=f"Rede automation launched in Terminal. Downloads will go to {REDE_DOWNLOAD_DIR}",
        launcher_path=launcher_path,
    )


def _date_args(date_mode: str, target_date: date | None) -> list[str]:
    if date_mode == "today":
        return ["--today"]
    if date_mode == "yesterday":
        return ["--yesterday"]
    if date_mode == "date" and target_date:
        return ["--date", target_date.isoformat()]
    return ["--yesterday"]


def _safe_suffix(parts: list[str]) -> str:
    return re.sub(r"[^a-zA-Z0-9-]+", "-", "-".join(parts)).strip("-").lower()
