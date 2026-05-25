"""Advisory cross-process lock for canonical Excel workbook writes (POSIX flock)."""

from __future__ import annotations

import fcntl
import json
import os
import socket
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


@contextmanager
def locked_workbook(
    workbook_path: Path,
    *,
    owner: str,
    timeout_sec: float = 600.0,
    poll_sec: float = 0.25,
) -> Iterator[None]:
    """
    Exclusive lock for mutations to workbook_path. Lock file lives beside the workbook:
    ``FuloFilo_Master.xlsx.lock`` (JSON metadata: owner, pid, host, utc timestamp).

    Uses ``fcntl.flock`` — cooperative (all writers must use this helper).
    """
    workbook_path = workbook_path.resolve()
    lock_path = workbook_path.parent / f"{workbook_path.name}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() - start > timeout_sec:
                    raise TimeoutError(
                        f"Workbook lock timeout ({timeout_sec}s) on {lock_path}"
                    ) from None
                time.sleep(poll_sec)
        meta = {
            "owner": owner,
            "pid": os.getpid(),
            "host": socket.gethostname(),
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        os.ftruncate(fd, 0)
        os.write(fd, json.dumps(meta, ensure_ascii=False).encode("utf-8"))
        os.fsync(fd)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(fd)
        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            pass
