#!/usr/bin/env python3
"""
Remove dashboard.giovannini.us from Cloudflare Tunnel ingress and ensure DNS is proxied (not *.cfargotunnel.com).
Requires CLOUDFLARE_API_TOKEN (or .env.cloudflare in repo root) with:
  Account → Cloudflare Tunnel → Edit, Zone → DNS → Edit for giovannini.us
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# region agent log
_LOG = Path(__file__).resolve().parent.parent / ".cursor" / "debug-664fb3.log"
_SESSION = "664fb3"


def _agent_log(
    hypothesis_id: str,
    location: str,
    message: str,
    data: dict,
    run_id: str = "cleanup-1",
) -> None:
    _LOG.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "sessionId": _SESSION,
        "hypothesisId": hypothesis_id,
        "runId": run_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(__import__("time").time() * 1000),
    }
    with _LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, default=str) + "\n")


# endregion

ROOT = Path(__file__).resolve().parent.parent
ACCOUNT_ID = "933e6be352787ffcd0129d7fe436de11"
DASHBOARD_HOST = "dashboard.giovannini.us"
ZONE_NAME = "giovannini.us"


def _load_dotenv_cloudflare() -> None:
    p = ROOT / ".env.cloudflare"
    if not p.is_file():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


def _api(method: str, url: str, token: str, body: dict | None = None) -> tuple[int, dict | list | None, str]:
    req_data = None
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if body is not None:
        req_data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else None, ""
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            parsed = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = {"raw": raw[:500]}
        return e.code, parsed, raw[:500]


def main() -> int:
    """
    H1: Tunnel still has dashboard hostname in ingress (causes 1033 when connector down).
    H2: DNS points at *.cfargotunnel.com (bypasses Worker).
    H3: DNS exists but proxied=false (Worker route may not apply as expected).
    H4: API token lacks Tunnel or DNS scope (operations fail).
    H5: No tunnel references dashboard (1033 would be from stale DNS only).
    """
    _load_dotenv_cloudflare()
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        _agent_log(
            "H4",
            "cloudflare_dashboard_cleanup.py:main",
            "CLOUDFLARE_API_TOKEN missing — cannot call API in this environment",
            {"hint": f"Set token or create {ROOT / '.env.cloudflare'}"},
        )
        print("Set CLOUDFLARE_API_TOKEN or create .env.cloudflare — see configs/cloudflare.deploy.env.example", file=sys.stderr)
        return 2

    base = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}"

    # --- Tunnels ---
    code, tunnels_body, err = _api("GET", f"{base}/cfd_tunnel", token)
    _agent_log(
        "H1",
        "cloudflare_dashboard_cleanup.py:tunnels_list",
        "list cfd_tunnel",
        {"http_status": code, "success": (tunnels_body or {}).get("success") if isinstance(tunnels_body, dict) else None},
    )
    if code != 200 or not isinstance(tunnels_body, dict) or not tunnels_body.get("success"):
        _agent_log("H4", "cloudflare_dashboard_cleanup.py:tunnels_list", "tunnel list failed", {"code": code, "body": tunnels_body})
        return 3

    tunnels = tunnels_body.get("result") or []
    if not isinstance(tunnels, list):
        tunnels = []

    for t in tunnels:
        tid = t.get("id")
        tname = t.get("name")
        if not tid:
            continue
        c_url = f"{base}/cfd_tunnel/{tid}/configurations"
        ccode, cfg_body, _ = _api("GET", c_url, token)
        if ccode != 200 or not isinstance(cfg_body, dict):
            _agent_log(
                "H4",
                "cloudflare_dashboard_cleanup.py:tunnel_config_get",
                "get tunnel config failed",
                {"tunnel_id": tid, "http_status": ccode},
            )
            continue
        result = cfg_body.get("result") or {}
        config = result.get("config") if isinstance(result, dict) else None
        if not isinstance(config, dict):
            _agent_log("H5", "cloudflare_dashboard_cleanup.py:tunnel_config", "no config blob", {"tunnel": tname, "tid": tid})
            continue
        ingress = config.get("ingress")
        if not isinstance(ingress, list):
            continue
        before = len(ingress)
        new_ingress = [r for r in ingress if isinstance(r, dict) and r.get("hostname") != DASHBOARD_HOST]
        removed = before - len(new_ingress)
        _agent_log(
            "H1",
            "cloudflare_dashboard_cleanup.py:tunnel_ingress_scan",
            "scanned ingress for dashboard host",
            {"tunnel_name": tname, "tunnel_id": tid, "rules_before": before, "rules_removed": removed},
        )
        if removed == 0:
            continue
        if not any(isinstance(r, dict) and r.get("service") == "http_status:404" for r in new_ingress):
            new_ingress.append({"service": "http_status:404"})
        new_config = {**config, "ingress": new_ingress}
        put_code, put_body, _ = _api(
            "PUT",
            c_url,
            token,
            {"config": new_config},
        )
        _agent_log(
            "H1",
            "cloudflare_dashboard_cleanup.py:tunnel_config_put",
            "PUT tunnel config after removing dashboard host",
            {"tunnel_id": tid, "http_status": put_code, "ok": isinstance(put_body, dict) and put_body.get("success")},
        )

    # --- Zone + DNS ---
    zcode, zones_body, _ = _api(
        "GET",
        f"https://api.cloudflare.com/client/v4/zones?name={ZONE_NAME}",
        token,
    )
    if zcode != 200 or not isinstance(zones_body, dict) or not zones_body.get("success"):
        _agent_log("H4", "cloudflare_dashboard_cleanup.py:zones", "zone list failed", {"code": zcode})
        return 4
    zr = zones_body.get("result") or []
    zone_id = zr[0]["id"] if zr else None
    if not zone_id:
        _agent_log("H2", "cloudflare_dashboard_cleanup.py:zones", "zone not found", {})
        return 5

    rcode, rec_body, _ = _api(
        "GET",
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?name={DASHBOARD_HOST}",
        token,
    )
    if rcode != 200 or not isinstance(rec_body, dict):
        _agent_log("H4", "cloudflare_dashboard_cleanup.py:dns_list", "dns list failed", {"code": rcode})
        return 6
    records = rec_body.get("result") or []
    _agent_log(
        "H2",
        "cloudflare_dashboard_cleanup.py:dns_records",
        "dashboard DNS records",
        {
            "count": len(records),
            "summaries": [
                {
                    "id": r.get("id"),
                    "type": r.get("type"),
                    "content": r.get("content"),
                    "proxied": r.get("proxied"),
                }
                for r in records
                if isinstance(r, dict)
            ],
        },
    )

    for r in records:
        if not isinstance(r, dict):
            continue
        rid = r.get("id")
        content = (r.get("content") or "").lower()
        proxied = bool(r.get("proxied"))
        needs_fix = ("cfargotunnel.com" in content) or not proxied
        _agent_log(
            "H3",
            "cloudflare_dashboard_cleanup.py:dns_eval",
            "record evaluation",
            {"record_id": rid, "needs_fix": needs_fix, "content_suffix": content[-40:]},
        )
        if not rid or not needs_fix:
            continue
        # Proxied CNAME to apex so orange-cloud applies; Worker is bound by route pattern.
        patch = {
            "type": "CNAME",
            "name": "dashboard",
            "content": ZONE_NAME,
            "proxied": True,
            "ttl": 1,
        }
        pcode, pbody, _ = _api(
            "PATCH",
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{rid}",
            token,
            patch,
        )
        _agent_log(
            "H2",
            "cloudflare_dashboard_cleanup.py:dns_patch",
            "patched dashboard record",
            {"http_status": pcode, "success": isinstance(pbody, dict) and pbody.get("success")},
        )

    print("Cleanup finished — check logs in .cursor/debug-664fb3.log")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
