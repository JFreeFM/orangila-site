#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "site"
STATUS_JSON = SITE_DIR / "status.json"
DEPLOY_SCRIPT = ROOT / "scripts" / "deploy_transip.sh"
DEFAULT_DAYZ_ENV = ROOT.parent / "dayzserver" / ".env.dayz-restart"
STATE_CACHE = ROOT / ".server-status-core.json"
STATUS_MEMORY = ROOT / ".status-memory.json"
LOCAL_TZ = ZoneInfo("Europe/Amsterdam")
RESTART_HOURS = (0, 5, 10, 15, 20)
RESTART_SOON_MINUTES = 15
DAYZ_QUERY_PORT = 2302
ONLINE_CONFIRMATIONS = 2
OFFLINE_CONFIRMATIONS = 2


@dataclass
class StatusPayload:
    status: str
    label: str
    detail: str
    timezone: str
    checked_at_utc: str
    server_time_utc: str
    server_time_local: str
    next_restart_utc: str
    next_restart_local: str

    def to_json(self) -> dict[str, Any]:
        return {
            "state": self.status,
            "status": self.status,
            "label": self.label,
            "detail": self.detail,
            "timezone": self.timezone,
            "checked_at_utc": self.checked_at_utc,
            "server_time_utc": self.server_time_utc,
            "server_time_local": self.server_time_local,
            "next_restart_utc": self.next_restart_utc,
            "next_restart_local": self.next_restart_local,
        }

    def core_json(self) -> dict[str, Any]:
        return {
            "state": self.status,
            "label": self.label,
            "detail": self.detail,
            "checked_at_utc": self.checked_at_utc,
            "server_time_utc": self.server_time_utc,
            "server_time_local": self.server_time_local,
            "next_restart_local": self.next_restart_local,
        }


@dataclass
class ServerSignals:
    service_active: bool
    process_running: bool
    port_open: bool
    pids: list[int]
    service_output: str
    port_matches: list[str]


def dayz_env_path() -> Path:
    override = os.environ.get("DAYZ_RESTART_ENV_FILE", "").strip()
    if override:
        return Path(override)
    return DEFAULT_DAYZ_ENV


def log(message: str) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[website-status] {now} {message}", flush=True)


def load_dayz_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_path = dayz_env_path()
    if not env_path.is_file():
        return env
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
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


def service_signal(service_name: str) -> tuple[bool, str]:
    proc = subprocess.run(
        ["systemctl", "--user", "is-active", service_name],
        capture_output=True,
        text=True,
        check=False,
    )
    output = proc.stdout.strip() or proc.stderr.strip() or f"exit={proc.returncode}"
    return proc.returncode == 0 and proc.stdout.strip() == "active", output


def dayz_processes() -> list[int]:
    proc = subprocess.run(
        ["pgrep", "-f", "^./DayZServer"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode not in (0, 1):
        return []
    pids: list[int] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pids.append(int(line))
        except ValueError:
            continue
    return pids


def udp_port_open(port: int) -> tuple[bool, list[str]]:
    proc = subprocess.run(
        ["ss", "-lun"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return False, []
    pattern = re.compile(rf"(^|[^0-9]){port}([^0-9]|$)")
    matches = [line.strip() for line in proc.stdout.splitlines() if f":{port}" in line and pattern.search(line)]
    return bool(matches), matches


def collect_server_signals(service_name: str, port: int) -> ServerSignals:
    service_active, service_output = service_signal(service_name)
    pids = dayz_processes()
    port_open, port_matches = udp_port_open(port)
    return ServerSignals(
        service_active=service_active,
        process_running=bool(pids),
        port_open=port_open,
        pids=pids,
        service_output=service_output,
        port_matches=port_matches,
    )


def load_status_memory() -> dict[str, Any]:
    if not STATUS_MEMORY.is_file():
        return {
            "stable_online": False,
            "success_streak": 0,
            "failure_streak": 0,
            "last_raw_online": False,
            "last_reason": "uninitialized",
        }
    try:
        data = json.loads(STATUS_MEMORY.read_text(encoding="utf-8"))
    except Exception:
        return {
            "stable_online": False,
            "success_streak": 0,
            "failure_streak": 0,
            "last_raw_online": False,
            "last_reason": "memory-read-failed",
        }
    return {
        "stable_online": bool(data.get("stable_online", False)),
        "success_streak": int(data.get("success_streak", 0)),
        "failure_streak": int(data.get("failure_streak", 0)),
        "last_raw_online": bool(data.get("last_raw_online", False)),
        "last_reason": str(data.get("last_reason", "unknown")),
        "last_checked_utc": str(data.get("last_checked_utc", "")),
    }


def write_status_memory(memory: dict[str, Any]) -> None:
    STATUS_MEMORY.write_text(json.dumps(memory, indent=2) + "\n", encoding="utf-8")


def update_availability_memory(memory: dict[str, Any], raw_online: bool, reason: str, now_utc: datetime) -> bool:
    if raw_online:
        memory["success_streak"] = int(memory.get("success_streak", 0)) + 1
        memory["failure_streak"] = 0
        if not bool(memory.get("stable_online", False)) and memory["success_streak"] >= ONLINE_CONFIRMATIONS:
            memory["stable_online"] = True
    else:
        memory["failure_streak"] = int(memory.get("failure_streak", 0)) + 1
        memory["success_streak"] = 0
        if bool(memory.get("stable_online", False)) and memory["failure_streak"] >= OFFLINE_CONFIRMATIONS:
            memory["stable_online"] = False

    memory["last_raw_online"] = raw_online
    memory["last_reason"] = reason
    memory["last_checked_utc"] = format_utc_label(now_utc)
    write_status_memory(memory)
    return bool(memory.get("stable_online", False))


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


def format_utc_label(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def format_local_label(value: datetime) -> str:
    return value.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")


def base_payload_fields(now_utc: datetime, next_restart_local: datetime) -> dict[str, str]:
    next_restart_utc = next_restart_local.astimezone(timezone.utc)
    checked_at_utc = format_utc_label(now_utc)
    server_time_utc = format_utc_label(now_utc)
    server_time_local = format_local_label(now_utc)
    next_restart_utc_label = format_utc_label(next_restart_utc)
    next_restart_local_label = format_local_label(next_restart_local)
    return {
        "timezone": "UTC source; Europe/Amsterdam local time (CET/CEST)",
        "checked_at_utc": checked_at_utc,
        "server_time_utc": server_time_utc,
        "server_time_local": server_time_local,
        "next_restart_utc": next_restart_utc_label,
        "next_restart_local": next_restart_local_label,
    }


def build_payload() -> StatusPayload:
    env = load_dayz_env()
    service_name = env.get("DAYZ_SERVICE_NAME", "dayz.service")
    default_dayz_root = dayz_env_path().parent
    maintenance_lock = Path(env.get("SCHEDULED_RESTART_LOCK_PATH", str(default_dayz_root / ".restart-lock")))
    runtime_lock = Path(
        env.get("SCHEDULED_RESTART_RUNTIME_LOCK_PATH", str(default_dayz_root / ".scheduled-restart-running.lock"))
    )
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(LOCAL_TZ)
    next_restart_local = next_restart(now_local)
    shared = base_payload_fields(now_utc, next_restart_local)
    minutes_until_restart = max(0, math.ceil((next_restart_local - now_local).total_seconds() / 60.0))
    signals = collect_server_signals(service_name, DAYZ_QUERY_PORT)
    raw_online = signals.service_active and signals.process_running and signals.port_open
    reason = (
        f"service_active={signals.service_active} service_output={signals.service_output!r} "
        f"process_running={signals.process_running} pids={signals.pids} "
        f"port_open={signals.port_open} port={DAYZ_QUERY_PORT} port_matches={signals.port_matches}"
    )
    memory = load_status_memory()
    stable_online = update_availability_memory(memory, raw_online, reason, now_utc)
    log(f"signal-check {reason} stable_online={stable_online} streaks={memory['success_streak']}/{memory['failure_streak']}")

    if not stable_online:
        return StatusPayload(
            status="offline",
            label="Offline",
            detail="The DayZ server is currently offline.",
            **shared,
        )

    if maintenance_lock.exists():
        return StatusPayload(
            status="maintenance",
            label="Maintenance",
            detail="Server maintenance is active right now.",
            **shared,
        )

    if runtime_lock.exists():
        return StatusPayload(
            status="scheduled-restart",
            label="Scheduled Restart",
            detail="Scheduled restart countdown is active. The server is still online until the restart completes.",
            **shared,
        )

    if minutes_until_restart <= RESTART_SOON_MINUTES:
        return StatusPayload(
            status="restart-soon",
            label="Restart Soon",
            detail=f"Scheduled restart in about {minutes_until_restart} minute(s).",
            **shared,
        )

    return StatusPayload(
        status="online",
        label="Online",
        detail="Server is live.",
        **shared,
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
    log(f"rendered state={payload.status} label={payload.label} next_restart={payload.next_restart_local}")
    if changed:
        log("status changed; deploying website update")
        deploy()
        log("deploy completed")
    else:
        log("status unchanged; deploy skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
