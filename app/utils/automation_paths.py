"""Repo-relative paths for Loyverse and Rede local automations."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def loyverse_data_root() -> Path:
    default = repo_root() / "automations" / "loyverse-data"
    return Path(os.environ.get("LOYVERSE_DATA_ROOT", str(default))).expanduser().resolve()


def rede_automation_root() -> Path:
    default = repo_root() / "automations" / "rede-automation"
    return Path(os.environ.get("REDE_AUTOMATION_ROOT", str(default))).expanduser().resolve()


def rede_download_dir() -> Path:
    default = Path.home() / "Downloads" / "Rede"
    return Path(os.environ.get("REDE_DOWNLOAD_DIR", str(default))).expanduser().resolve()
