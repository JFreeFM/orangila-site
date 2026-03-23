#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from zoneinfo import ZoneInfo


ROOT = Path("/home/jeffreyklein/orangila-site")
SITE_DIR = ROOT / "site"
STATUS_JSON = SITE_DIR / "status.json"
DEPLOY_SCRIPT = ROOT / "scripts" / "deploy_transip.sh"
DAYZ_ENV = Path("/home/jeffreyklein/dayzserver/.env.dayz-restart")
STATE_CACHE = ROOT / ".server-status-core.json"
LOCAL_TZ = ZoneInfo("Europe/Amsterdam")
RESTART_HOURS = (0, 5, 10, 15, 20)
RESTART_SOON_MINUTES = 15


@dataclass
class StatusPayload:
    state: str
    label: str
    detail: str
    next_restart: str
    checked_at: str

    def to_json(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "label": self.label,
            "detail": self.detail,
            "next_restart": self.next_restart,
            "checked_at": self.checked_at,
        }

    def core_json(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "label": self.label,
            "detail": self.detail,
            "next_restart": self.next_restart,
        }


def log(message: str) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[website-status] {now} {message}", flush=True)


def load_dayz_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if not DAYZ_ENV.is_file():
        return env
    for raw_line in DAYZ_ENV.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def is_dayz_active(service_name: str) -> bool:
    proc = subprocess.run(
        ["systemctl", "--user", "is-active", service_name],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0 and proc.stdout.strip() == "active"


def next_restart(now_local: datetime) -> datetime:
    today = now_local.date()
    candidates = [
        datetime(today.year, today.month, today.day, hour, 0, tzinfo=LOCAL_TZ)
        for hour in RESTART_HOURS
    ]
    for candidate in candidates:
        if candidate > now_local:
            return candidate
    tomorrow = now_local + timedelta(days=1)
    return datetime(tomorrow.year, tomorrow.month, tomorrow.day, RESTART_HOURS[0], 0, tzinfo=LOCAL_TZ)


def build_payload() -> StatusPayload:
    env = load_dayz_env()
    service_name = env.get("DAYZ_SERVICE_NAME", "dayz.service")
    maintenance_lock = Path(env.get("SCHEDULED_RESTART_LOCK_PATH", "/home/jeffreyklein/dayzserver/.restart-lock"))
    runtime_lock = Path(
        env.get("SCHEDULED_RESTART_RUNTIME_LOCK_PATH", "/home/jeffreyklein/dayzserver/.scheduled-restart-running.lock")
    )
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(LOCAL_TZ)
    next_restart_local = next_restart(now_local)
    next_restart_label = next_restart_local.strftime("%H:%M %Z")
    minutes_until_restart = max(0, math.ceil((next_restart_local - now_local).total_seconds() / 60.0))

    if not is_dayz_active(service_name):
        return StatusPayload(
            state="offline",
            label="Offline",
            detail="The DayZ server is currently offline.",
            next_restart=next_restart_label,
            checked_at=now_utc.isoformat(),
        )

    if maintenance_lock.exists():
        return StatusPayload(
            state="maintenance",
            label="Maintenance",
            detail="Server maintenance is active right now.",
            next_restart=next_restart_label,
            checked_at=now_utc.isoformat(),
        )

    if runtime_lock.exists():
        return StatusPayload(
            state="scheduled-restart",
            label="Scheduled Restart",
            detail="Scheduled restart countdown is active. The server is still online until the restart completes.",
            next_restart=next_restart_label,
            checked_at=now_utc.isoformat(),
        )

    if minutes_until_restart <= RESTART_SOON_MINUTES:
        return StatusPayload(
            state="restart-soon",
            label="Restart Soon",
            detail=f"Scheduled restart in about {minutes_until_restart} minute(s).",
            next_restart=next_restart_label,
            checked_at=now_utc.isoformat(),
        )

    return StatusPayload(
        state="online",
        label="Online",
        detail=f"Server is live. Next scheduled restart: {next_restart_label}.",
        next_restart=next_restart_label,
        checked_at=now_utc.isoformat(),
    )


def load_previous_core() -> dict[str, Any] | None:
    if not STATE_CACHE.is_file():
        return None
    try:
        return json.loads(STATE_CACHE.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_status(payload: StatusPayload) -> bool:
    STATUS_JSON.write_text(json.dumps(payload.to_json(), indent=2) + "\n", encoding="utf-8")
    previous_core = load_previous_core()
    current_core = payload.core_json()
    STATE_CACHE.write_text(json.dumps(current_core, indent=2) + "\n", encoding="utf-8")
    return previous_core != current_core


def deploy() -> None:
    subprocess.run([str(DEPLOY_SCRIPT)], check=True)


def main() -> int:
    payload = build_payload()
    changed = write_status(payload)
    log(f"rendered state={payload.state} label={payload.label} next_restart={payload.next_restart}")
    if changed:
        log("status changed; deploying website update")
        deploy()
        log("deploy completed")
    else:
        log("status unchanged; deploy skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
