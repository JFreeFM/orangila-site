#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = Path(
    os.environ.get("ORANGILA_REPORTS_DIR", str(ROOT.parent / "dayzserver" / "reports"))
)
SITE_DIR = ROOT / "site"
STATUS_DIR = SITE_DIR / "status"
PUBLIC_DATA_PATH = SITE_DIR / "status-data.json"
RECENT_FIXES_PATH = REPORTS_DIR / "recent-fixes.json"
LOCAL_TZ = ZoneInfo("Europe/Amsterdam")


def latest_report_path() -> Path:
    candidates = sorted(
        REPORTS_DIR.glob("community-insights-*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise SystemExit("No community insights report found.")
    return candidates[0]


def load_json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SystemExit(f"Unexpected JSON structure in {path}")
    return raw


def load_json_array(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def clean_item(text: str) -> str:
    return " ".join((text or "").split()).strip()


def item_label(title: str, qualifier: str | None = None) -> str:
    label = clean_item(title)
    if qualifier:
        label = f"{label} ({qualifier})"
    return label


def plain_title(title: str) -> str:
    return clean_item(title)


def normalize_key(text: str) -> str:
    return clean_item(text).casefold()


def distinct(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = normalize_key(item)
        if not item or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def is_completed_item(text: str) -> bool:
    low = clean_item(text).casefold()
    completed_markers = (
        "restart countdown bot in discord",
        "pre-restart countdown notification in discord",
    )
    return any(marker in low for marker in completed_markers)


def rewrite_progress_item(text: str) -> str:
    clean = clean_item(text)
    rewrites = {
        "Create pinned Discord starter guide with trader locations and rules":
            "Improve the starter guide so new players can get in faster.",
        "Adjust basic repair item prices in trader configuration":
            "Tune trader pricing for basic repair items.",
        "Investigate server performance and zombie AI synchronization near Novy Sobor and Staroye during peak population":
            "Improve zombie performance and stability around busy areas like Novy Sobor and Staroye.",
        "Fix trader UI scroll event handling to prevent transaction interruption":
            "Improve trader menu stability during fast scrolling.",
    }
    return rewrites.get(clean, clean)


def rewrite_recent_fix(title: str, description: str, date: str) -> str:
    title_clean = clean_item(title)
    desc_clean = clean_item(description)
    rewrites = {
        "Discord restart countdown live": "Discord restart warnings now post before scheduled restarts",
        "Krona trader survivor issue removed": "The broken Krona trader survivor issue was removed",
        "Krona trader fallback switched to signs and marker boards": "Krona trading now uses stable signs and marker boards",
        "RCON chat delivery restored": "Discord and admin chat delivery was restored",
    }
    label = rewrites.get(title_clean, title_clean or desc_clean)
    if not label:
        return ""
    if date:
        return f"{label} ({date})"
    return label


RECENT_FIX_TO_KNOWN_ISSUE_ALIASES = {
    normalize_key("Krona trader board placement fixed"): {
        normalize_key("Misplaced car trader sign in Krona City"),
        normalize_key("Reposition car trader sign behind counter in Krona City"),
        normalize_key("Adjust car trader board coordinates in Krona City to place it behind the counter as intended"),
    },
    normalize_key("Krona trader survivor issue removed"): {
        normalize_key("Misplaced car trader sign in Krona City"),
    },
    normalize_key("Krona trader fallback switched to signs and marker boards"): {
        normalize_key("Misplaced car trader sign in Krona City"),
    },
}


def resolved_issue_keys_from_recent_fixes(items: list[dict[str, Any]]) -> set[str]:
    resolved: set[str] = set()
    for item in items:
        title_key = normalize_key(str(item.get("title") or ""))
        if not title_key:
            continue
        resolved.update(RECENT_FIX_TO_KNOWN_ISSUE_ALIASES.get(title_key, set()))
    return resolved


def map_public_sections(report: dict[str, Any]) -> dict[str, Any]:
    top_bugs = report.get("top_bugs") if isinstance(report.get("top_bugs"), list) else []
    top_requests = report.get("top_feature_requests") if isinstance(report.get("top_feature_requests"), list) else []
    recurring = report.get("recurring_problems") if isinstance(report.get("recurring_problems"), list) else []
    quick_wins = report.get("quick_wins") if isinstance(report.get("quick_wins"), list) else []
    actions = report.get("recommended_actions") if isinstance(report.get("recommended_actions"), list) else []
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    meta = report.get("meta") if isinstance(report.get("meta"), dict) else {}

    known_issues = [
        plain_title(str(item.get("title") or ""))
        for item in top_bugs
        if isinstance(item, dict)
    ]
    recurring_issue_titles = [
        plain_title(str(item.get("title") or ""))
        for item in recurring
        if isinstance(item, dict)
    ]
    planned_requested = [
        plain_title(str(item.get("title") or ""))
        for item in top_requests
        if isinstance(item, dict)
    ]
    planned_requested = [item for item in distinct(planned_requested) if not is_completed_item(item)]
    in_progress = [rewrite_progress_item(str(item)) for item in quick_wins[:3]] + [
        rewrite_progress_item(str(item)) for item in actions[:2]
    ]
    recent_fixes_raw = load_json_array(RECENT_FIXES_PATH)
    recent_fixes_raw.sort(key=lambda item: str(item.get("date") or ""), reverse=True)
    resolved_issue_keys = resolved_issue_keys_from_recent_fixes(recent_fixes_raw)
    in_progress = [
        item for item in distinct(in_progress)
        if not is_completed_item(item) and normalize_key(item) not in resolved_issue_keys
    ]

    recently_fixed = []
    for item in recent_fixes_raw[:4]:
        title = str(item.get("title") or "")
        description = str(item.get("description") or "")
        date = clean_item(str(item.get("date") or ""))
        label = rewrite_recent_fix(title, description, date)
        if not label:
            continue
        recently_fixed.append(label)

    notes = []
    if not recently_fixed:
        notes.append("Recently fixed items will appear here as they are confirmed and added to the workflow.")

    reporting_period = clean_item(str(summary.get("reporting_period") or "Latest daily report"))
    generated_at_raw = clean_item(str(meta.get("generated_at") or ""))
    generated_at = generated_at_raw
    generated_at_local = "UNKNOWN"
    if generated_at_raw:
        try:
            generated_dt = datetime.fromisoformat(generated_at_raw.replace("Z", "+00:00"))
            generated_at = generated_dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
            generated_at_local = generated_dt.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M %Z")
        except ValueError:
            generated_at = generated_at_raw

    all_known_issues = distinct(known_issues + recurring_issue_titles)
    known_issues_public = [
        item for item in all_known_issues
        if normalize_key(item) not in resolved_issue_keys
    ]

    return {
        "reporting_period": reporting_period,
        "generated_at": generated_at,
        "generated_at_local": generated_at_local,
        "known_issues": known_issues_public,
        "in_progress": in_progress,
        "planned_requested": planned_requested,
        "recently_fixed": recently_fixed,
        "notes": notes,
    }


def render_list(items: list[str], empty_text: str) -> str:
    if not items:
        return f"<p class=\"status-empty\">{escape(empty_text)}</p>"
    lines = ["<ul class=\"status-list\">"]
    for item in items:
        lines.append(f"  <li>{escape(item)}</li>")
    lines.append("</ul>")
    return "\n".join(lines)


def render_page(public_data: dict[str, Any]) -> str:
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>OranGila DayZ | Server Status & Roadmap</title>
    <meta
      name="description"
      content="Known issues, work in progress, and requested improvements for the OranGila DayZ server."
    >
    <link rel="canonical" href="https://orangila.com/status/">
    <meta name="robots" content="index,follow">
    <link rel="stylesheet" href="../styles.css">
  </head>
  <body>
    <div class="page-shell page-shell-status">
      <a class="site-mark" href="/">ORANGILA DAYZ</a>
      <div class="glow glow-a"></div>
      <div class="glow glow-b"></div>
      <main class="hero-stage status-stage">
        <section class="status-hero-card">
          <p class="eyebrow">Player Update</p>
          <h1>Server Status & What We Are Working On</h1>
          <p class="intro">
            A simple public view of what was fixed recently, what players are running into, and what is being improved next.
          </p>
          <div class="status-summary-grid">
            <section>
              <h2>Feedback Window</h2>
              <p>{escape(public_data["reporting_period"])}</p>
            </section>
            <section>
              <h2>Based On</h2>
              <p>Recent community feedback and confirmed fixes.</p>
            </section>
            <section>
              <h2>Updated</h2>
              <p id="status-updated-summary">{escape(public_data["generated_at"] or "Unknown")}</p>
            </section>
          </div>
        </section>

        <section class="status-card status-time-card">
          <div class="status-time-head">
            <div>
              <h2>Time Reference</h2>
              <p class="status-time-note">
                Backend timestamps stay in UTC. The website renders explicit UTC and Europe/Amsterdam local values with CET or CEST labels from server-side status data.
              </p>
            </div>
            <div class="status-time-live">
              <p class="status-time-live-label">Current Server Time</p>
              <p class="status-time-live-value" id="current-server-time-live">Loading...</p>
            </div>
          </div>
          <div class="status-time-table-wrap">
            <table class="status-time-table">
              <thead>
                <tr>
                  <th scope="col">Reference</th>
                  <th scope="col">UTC Time</th>
                  <th scope="col">Local Time (CET/CEST)</th>
                  <th scope="col">Current Server Time</th>
                </tr>
              </thead>
              <tbody id="status-time-table-body">
                <tr>
                  <td>Status Page Updated</td>
                  <td>Loading...</td>
                  <td>Loading...</td>
                  <td>Loading...</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="status-columns">
          <article class="status-card">
            <h2>Recently Fixed</h2>
            {render_list(public_data["recently_fixed"], "No recent fixes have been published yet.")}
          </article>

          <article class="status-card">
            <h2>Known Issues</h2>
            {render_list(public_data["known_issues"], "No major player-facing issues are listed right now.")}
          </article>

          <article class="status-card">
            <h2>In Progress</h2>
            {render_list(public_data["in_progress"], "No active public items are listed right now.")}
          </article>

          <article class="status-card">
            <h2>Planned / Requested</h2>
            {render_list(public_data["planned_requested"], "No requested items are listed right now.")}
          </article>
        </section>

        <section class="seo-copy status-footnote">
          <h2>How To Help</h2>
          <p>
            Found a bug or have an idea? Join Discord and post it in bug reports or suggestions.
          </p>
        </section>
      </main>
    </div>
    <script>
      function formatAmsterdamLabel(date) {{
        const zonePart = new Intl.DateTimeFormat("en-GB", {{
          timeZone: "Europe/Amsterdam",
          timeZoneName: "shortOffset",
        }})
          .formatToParts(date)
          .find((part) => part.type === "timeZoneName");

        const rawZone = zonePart ? zonePart.value : "";
        const zone = rawZone === "GMT+2" ? "CEST" : rawZone === "GMT+1" ? "CET" : "UNKNOWN";
        const parts = new Intl.DateTimeFormat("en-GB", {{
          timeZone: "Europe/Amsterdam",
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
        }}).formatToParts(date);
        const map = Object.fromEntries(parts.filter((part) => part.type !== "literal").map((part) => [part.type, part.value]));
        return `${{map.year}}-${{map.month}}-${{map.day}} ${{map.hour}}:${{map.minute}}:${{map.second}} ${{zone}}`;
      }}

      function startLiveServerClock() {{
        const live = document.getElementById("current-server-time-live");
        if (!live) {{
          return;
        }}

        function tick() {{
          const text = formatAmsterdamLabel(new Date());
          live.textContent = text;
          document.querySelectorAll(".current-server-time-cell").forEach((cell) => {{
            cell.textContent = text;
          }});
        }}

        tick();
        window.setInterval(tick, 1000);
      }}

      function renderTimeRows(rows) {{
        const body = document.getElementById("status-time-table-body");
        if (!body) {{
          return;
        }}

        body.innerHTML = rows
          .map((row) => {{
            return `
              <tr>
                <th scope="row">${{row.label}}</th>
                <td>${{row.utc || "UNKNOWN"}}</td>
                <td>${{row.local || "UNKNOWN"}}</td>
                <td class="current-server-time-cell">${{row.current || "UNKNOWN"}}</td>
              </tr>
            `;
          }})
          .join("");
      }}

      async function loadStatusTimeData() {{
        try {{
          const [statusDataResponse, statusResponse] = await Promise.all([
            fetch("../status-data.json", {{ cache: "no-store" }}),
            fetch("../status.json", {{ cache: "no-store" }}),
          ]);

          const statusData = await statusDataResponse.json();
          const status = await statusResponse.json();
          const currentServerTime = status.server_time_local || "UNKNOWN";
          const rows = [
            {{
              label: "Status Page Updated",
              utc: statusData.generated_at || "UNKNOWN",
              local: statusData.generated_at_local || "UNKNOWN",
              current: currentServerTime,
            }},
            {{
              label: "Server Checked At",
              utc: status.checked_at_utc || "UNKNOWN",
              local: status.server_time_local || "UNKNOWN",
              current: currentServerTime,
            }},
          ];

          renderTimeRows(rows);

          const summary = document.getElementById("status-updated-summary");
          if (summary) {{
            summary.textContent = `${{rows[0].utc}} | ${{rows[0].local}}`;
          }}

          startLiveServerClock();
        }} catch (error) {{
          const body = document.getElementById("status-time-table-body");
          if (body) {{
            body.innerHTML = `
              <tr>
                <th scope="row">Time Data</th>
                <td>UNKNOWN</td>
                <td>UNKNOWN</td>
                <td class="current-server-time-cell">UNKNOWN</td>
              </tr>
            `;
          }}
          startLiveServerClock();
        }}
      }}

      loadStatusTimeData();
    </script>
  </body>
</html>
"""


def main() -> int:
    report_path = latest_report_path()
    report = load_json(report_path)
    public_data = map_public_sections(report)

    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    (STATUS_DIR / "index.html").write_text(render_page(public_data), encoding="utf-8")
    PUBLIC_DATA_PATH.write_text(json.dumps(public_data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"Wrote {STATUS_DIR / 'index.html'}")
    print(f"Wrote {PUBLIC_DATA_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
