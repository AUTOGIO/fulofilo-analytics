from __future__ import annotations

from datetime import date

from app.utils import rede_automation
from app.utils import runtime


def test_local_automations_are_disabled_off_macos(monkeypatch) -> None:
    monkeypatch.delenv("STREAMLIT_SHARING_MODE", raising=False)
    monkeypatch.delenv("IS_STREAMLIT_CLOUD", raising=False)
    monkeypatch.setattr(runtime.sys, "platform", "linux")

    assert runtime.is_streamlit_cloud() is False
    assert runtime.local_automations_available() is False


def test_cloud_flag_disables_local_automations_on_macos(monkeypatch) -> None:
    monkeypatch.setattr(runtime.sys, "platform", "darwin")
    monkeypatch.setenv("IS_STREAMLIT_CLOUD", "1")

    assert runtime.local_automations_available() is False


def test_rede_launcher_fails_cleanly_off_macos(monkeypatch) -> None:
    monkeypatch.setattr(runtime.sys, "platform", "linux")

    def unexpected_run(*args, **kwargs):
        raise AssertionError("subprocess.run must not be called outside macOS")

    monkeypatch.setattr(rede_automation.subprocess, "run", unexpected_run)

    result = rede_automation.launch_rede_sales_download("date", date(2026, 7, 13), ["csv"])

    assert result.ok is False
    assert result.launcher_path is None
    assert "local macOS FF Terminal" in result.message
