# OranGila Website Setup

Status date: 2026-03-21

## Current state

The OranGila website is deployed from a local working copy to the live hosting target over SSH.

Current published files:
- `index.html`
- `styles.css`
- `OranGilanewserver.png`
- `status.json`
- `robots.txt`
- `sitemap.xml`
- `status/index.html`
- `status-data.json`

Current live URL:
- `https://orangila.com`

## Deploy model

Deploy is done over SSH using a local environment file that is not tracked in git.

Deploy script:
- `scripts/deploy_transip.sh`

Local deploy config:
- `.env.deploy`

## Current homepage

The current first version includes:
- full-screen hero image using `OranGilanewserver.png`
- centered overlay content
- `ORANGILA DAYZ` brand mark positioned top-left outside the hero image
- CTA button text:
  - `Join via Discord`
- CTA button target:
  - `https://discord.gg/SZdwUpmTXp`
- red/white visual direction
- core DayZ server info
- live server status badge on the homepage
- basic SEO metadata for search and social previews
- public `/status/` page generated from the Community Insights pipeline
- copy-to-copy server address block for `85.145.216.36:2302`
- compact `Why OranGila?` value section

Current status states:
- `Online` (green)
- `Restart Soon` (orange)
- `Scheduled Restart` (orange)
- `Maintenance` (orange)
- `Offline` (red)

Main files:
- `site/index.html`
- `site/styles.css`

## Verified live checks

Confirmed:
- `orangila.com` responds over HTTPS
- the live homepage serves correctly
- the website uses Let's Encrypt

## Deploy command

```bash
cd /path/to/orangila-site
./scripts/deploy_transip.sh
```

Dry-run check:

```bash
cd /path/to/orangila-site
./scripts/deploy_transip.sh --dry-run
```

## Notes

- The old hosting placeholder page was replaced by the static site.
- Future changes can be made locally in `site/` and then published with the deploy script.
- The deploy script now validates the SSH key path and refuses unsafe empty or root target paths.
- The homepage keeps the existing visual style, but the copy is now more player-facing:
  - stronger Discord-first CTA
  - direct support text
  - compact value section
  - copy-to-copy connect block
- Website server status is generated locally from the DayZ runtime state and published through `site/status.json`.
- The global page background now explicitly uses the existing dark theme color on both `html` and `body`, so overscroll/empty scroll space no longer shows white.
- Basic SEO files now ship with the site:
  - `site/robots.txt`
  - `site/sitemap.xml`
- The status updater runs as local automation outside the public website repo.
- Status source logic:
  - `dayz.service` active -> base online signal
  - scheduled restart runtime lock -> `Scheduled Restart`
  - maintenance lock -> `Maintenance`
  - next scheduled restart within 15 minutes -> `Restart Soon`
  - inactive DayZ service -> `Offline`
- Public status source:
  - `https://orangila.com/status.json`
- Public roadmap/status page:
  - `https://orangila.com/status/`
- Browser note:
  - after a restart or status flip, browsers may briefly show a cached older state until a hard refresh or cache-bypassed request is used
- A later improvement is to point the homepage CTA to a branded Discord landing route such as `orangila.com/discord`.
- The current Discord CTA already uses a permanent invite created via the Discord bot.

## Weekly Public Update

A weekly public community update is generated from existing public-safe sources and posted to Discord `#announcements`.

Sources:
- `recent-fixes.json`
- public `status-data.json`

Runtime:
- script:
  - `/home/jeffreyklein/dayzserver/scripts/weekly_public_update.py`
- service:
  - `/home/jeffreyklein/.config/systemd/user/weekly-public-update.service`
- timer:
  - `/home/jeffreyklein/.config/systemd/user/weekly-public-update.timer`

Posting rules:
- once per week
- Sunday evening local server time
- duplicate-safe per ISO week
- links back to `https://orangila.com/status/`

## Public Repo Security

This repo stays public on purpose, so the working rule is:
- public website code stays here
- deploy config stays local
- no secrets, private paths, or internal ops snapshots belong in tracked files
- public status output may be tracked, but internal report sources stay outside the public repo
