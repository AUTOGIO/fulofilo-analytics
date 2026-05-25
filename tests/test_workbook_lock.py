"""Advisory workbook lock: acquire/release and metadata sidecar."""

from __future__ import annotations

import json
import multiprocessing
import tempfile
from pathlib import Path

import pytest

from app.utils.workbook_lock import locked_workbook


def test_locked_workbook_writes_metadata_and_releases(tmp_path: Path) -> None:
    wb = tmp_path / "book.xlsx"
    wb.write_bytes(b"dummy")
    lock_path = tmp_path / "book.xlsx.lock"

    with locked_workbook(wb, owner="test_owner", timeout_sec=2.0):
        assert lock_path.is_file()
        meta = json.loads(lock_path.read_text(encoding="utf-8"))
        assert meta["owner"] == "test_owner"
        assert "pid" in meta and "host" in meta

    assert not lock_path.exists()


def _child_hold_lock(wb: str, ready: multiprocessing.Queue, done: multiprocessing.Event) -> None:
    p = Path(wb)
    with locked_workbook(p, owner="child", timeout_sec=30.0):
        ready.put(True)
        done.wait(timeout=60)


def test_locked_workbook_blocks_second_process(tmp_path: Path) -> None:
    wb = tmp_path / "book2.xlsx"
    wb.write_bytes(b"x")
    ready: multiprocessing.Queue = multiprocessing.Queue()
    done = multiprocessing.Event()
    proc = multiprocessing.Process(
        target=_child_hold_lock, args=(str(wb), ready, done)
    )
    proc.start()
    assert ready.get(timeout=10)
    with pytest.raises(TimeoutError):
        with locked_workbook(wb, owner="main", timeout_sec=1.0, poll_sec=0.05):
            pass
    done.set()
    proc.join(timeout=10)
    assert proc.exitcode == 0
