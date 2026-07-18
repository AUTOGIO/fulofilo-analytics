"""Runtime capability checks shared by dashboard automation entrypoints."""

from __future__ import annotations

import os
import sys


def is_streamlit_cloud() -> bool:
    return bool(os.environ.get("STREAMLIT_SHARING_MODE") or os.environ.get("IS_STREAMLIT_CLOUD"))


def local_automations_available() -> bool:
    """Return whether this process can launch the macOS-only automation tools."""
    return sys.platform == "darwin" and not is_streamlit_cloud()
