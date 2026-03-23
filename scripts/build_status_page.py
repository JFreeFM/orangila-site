#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any


REPORTS_DIR = Path("/home/jeffreyklein/dayzserver/reports")
SITE_DIR = Path("/home/jeffreyklein/orangila-site/site")
STATUS_DIR = SITE_DIR / "status"
PUBLIC_DATA_PATH = SITE_DIR / "status-data.json"
RECENT_FIXES_PATH = REPORTS_DIR / "recent-fixes.json"


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


def distinct(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.casefold()
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


def map_public_sections(report: dict[str, Any]) -> dict[str, Any]:
    top_bugs = report.get("top_bugs") if isinstance(report.get("top_bugs"), list) else []
    top_requests = report.get("top_feature_requests") if isinstance(report.get("top_feature_requests"), list) else []
    recurring = report.get("recurring_problems") if isinstance(report.get("recurring_problems"), list) else []
    quick_wins = report.get("quick_wins") if isinstance(report.get("quick_wins"), list) else []
    actions = report.get("recommended_actions") if isinstance(report.get("recommended_actions"), list) else []
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    meta = report.get("meta") if isinstance(report.get("meta"), dict) else {}

    known_issues = [
        item_label(str(item.get("title") or ""), str(item.get("priority") or "").lower() or None)
        for item in top_bugs
        if isinstance(item, dict)
    ]
    recurring_issue_titles = [
        item_label(str(item.get("title") or ""), str(item.get("type") or "").lower() or None)
        for item in recurring
        if isinstance(item, dict)
    ]
    planned_requested = [
        item_label(str(item.get("title") or ""), str(item.get("impact") or "").lower() or None)
        for item in top_requests
        if isinstance(item, dict)
    ]
    planned_requested = [item for item in distinct(planned_requested) if not is_completed_item(item)]
    in_progress = [clean_item(str(item)) for item in quick_wins[:3]] + [clean_item(str(item)) for item in actions[:2]]
    in_progress = [item for item in distinct(in_progress) if not is_completed_item(item)]

    recent_fixes_raw = load_json_array(RECENT_FIXES_PATH)
    recent_fixes_raw.sort(key=lambda item: str(item.get("date") or ""), reverse=True)
    recently_fixed = []
    for item in recent_fixes_raw[:5]:
        title = clean_item(str(item.get("title") or ""))
        description = clean_item(str(item.get("description") or ""))
        date = clean_item(str(item.get("date") or ""))
        if not title:
            continue
        label = title
        if description:
            label = f"{label} - {description}"
        if date:
            label = f"{label} ({date})"
        recently_fixed.append(label)

    notes = []
    if not recently_fixed:
        notes.append("Recently fixed items will appear here as they are confirmed and added to the workflow.")

    reporting_period = clean_item(str(summary.get("reporting_period") or "Latest daily report"))
    generated_at_raw = clean_item(str(meta.get("generated_at") or ""))
    generated_at = generated_at_raw
    if generated_at_raw:
        try:
            generated_at = (
                datetime.fromisoformat(generated_at_raw.replace("Z", "+00:00"))
                .astimezone(UTC)
                .strftime("%Y-%m-%d %H:%M UTC")
            )
        except ValueError:
            generated_at = generated_at_raw

    source_channels = [
        clean_item(str(item.get("name") or ""))
        for item in meta.get("source_channels", [])
        if isinstance(item, dict) and clean_item(str(item.get("name") or ""))
    ]

    return {
        "reporting_period": reporting_period,
        "generated_at": generated_at,
        "messages_processed": int(summary.get("messages_processed") or 0),
        "source_channels": source_channels,
        "known_issues": distinct(known_issues + recurring_issue_titles),
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
    source_labels = ", ".join(f"#{name}" for name in public_data["source_channels"]) or "Discord feedback channels"
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
          <p class="eyebrow">Public Status</p>
          <h1>Server Status & Roadmap</h1>
          <p class="intro">
            A simple public view of the main issues, improvements, and active work for OranGila DayZ.
          </p>
          <div class="status-summary-grid">
            <section>
              <h2>Reporting Period</h2>
              <p>{escape(public_data["reporting_period"])}</p>
            </section>
            <section>
              <h2>Messages Reviewed</h2>
              <p>{public_data["messages_processed"]}</p>
            </section>
            <section>
              <h2>Source Channels</h2>
              <p>{escape(source_labels)}</p>
            </section>
            <section>
              <h2>Last Updated</h2>
              <p>{escape(public_data["generated_at"] or "Unknown")}</p>
            </section>
          </div>
        </section>

        <section class="status-columns">
          <article class="status-card">
            <h2>Known Issues</h2>
            {render_list(public_data["known_issues"], "No major public issues are listed right now.")}
          </article>

          <article class="status-card">
            <h2>In Progress</h2>
            {render_list(public_data["in_progress"], "No active public items are listed right now.")}
          </article>

          <article class="status-card">
            <h2>Planned / Requested</h2>
            {render_list(public_data["planned_requested"], "No requested items are listed right now.")}
          </article>

          <article class="status-card">
            <h2>Recently Fixed</h2>
            {render_list(public_data["recently_fixed"], "No recent fixes have been published yet.")}
          </article>
        </section>

        <section class="seo-copy status-footnote">
          <h2>How To Help</h2>
          <p>
            Found a bug or have an idea? Join the Discord and use <strong>#report-bugs</strong> or
            <strong>#suggestions</strong>. Clear feedback helps us improve the server faster.
          </p>
        </section>
      </main>
    </div>
  </body>
</html>
"""


def main() -> int:
    report_path = latest_report_path()
    report = load_json(report_path)
    public_data = map_public_sections(report)
    public_data["source_report"] = str(report_path)

    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    (STATUS_DIR / "index.html").write_text(render_page(public_data), encoding="utf-8")
    PUBLIC_DATA_PATH.write_text(json.dumps(public_data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"Wrote {STATUS_DIR / 'index.html'}")
    print(f"Wrote {PUBLIC_DATA_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
