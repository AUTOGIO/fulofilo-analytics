from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
MASTER_PATH = ROOT / "data" / "excel" / "FuloFilo_Master.xlsx"
BACKUP_DIR = ROOT / "data" / "excel" / "backups"


def backup_workbook(workbook_path: Path = MASTER_PATH, backup_dir: Path | None = None) -> Path:
    """Create a timestamped backup before mutating the canonical workbook."""
    backup_dir = backup_dir or (workbook_path.parent / "backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{workbook_path.stem}_{timestamp}{workbook_path.suffix}"
    counter = 1
    while backup_path.exists():
        backup_path = backup_dir / f"{workbook_path.stem}_{timestamp}_{counter:02d}{workbook_path.suffix}"
        counter += 1
    shutil.copy2(workbook_path, backup_path)
    return backup_path


def run_canonical_sync(root: Path = ROOT) -> tuple[bool, str]:
    """Regenerate derived layers from the canonical Excel workbook."""
    result = subprocess.run(
        ["bash", str(root / "scripts" / "sync_excel.sh")],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    output = "\n".join(part for part in [result.stdout.strip(), result.stderr.strip()] if part).strip()
    return result.returncode == 0, output
