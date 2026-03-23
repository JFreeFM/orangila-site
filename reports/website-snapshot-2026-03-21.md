# OranGila Website Snapshot

Snapshot date: 2026-03-21

## Live state

- domain:
  - `orangila.com`
- hosting:
  - TransIP webhosting
- deploy source:
  - `/home/jeffreyklein/orangila-site`
- deploy method:
  - `rsync` over SSH from this server
- live webroot:
  - `/data/sites/web/orangilacom/www`

## Published homepage

- hero image:
  - `OranGilanewserver.png`
- top-left page brand mark:
  - `ORANGILA DAYZ`
- visual direction:
  - red accents
  - white text
- CTA text:
  - `Join Our DayZ Server`
- CTA target:
  - `https://discord.gg/SZdwUpmTXp`
- live server status:
  - homepage badge fed by `status.json`
  - green = `Online`
  - orange = `Restart Soon` / `Scheduled Restart` / `Maintenance`
  - red = `Offline`
  - public source: `https://orangila.com/status.json`

## Verified infrastructure

- DNS points to TransIP
- HTTP redirects to HTTPS
- HTTPS serves a valid Let's Encrypt certificate
- live deploy path works from this server
- TransIP key-based deploy is active
- status updater publishes live state to the website
- browser caching can briefly show an older status right after a state flip

## Important local files

- `/home/jeffreyklein/orangila-site/site/index.html`
- `/home/jeffreyklein/orangila-site/site/styles.css`
- `/home/jeffreyklein/orangila-site/site/status.json`
- `/home/jeffreyklein/orangila-site/scripts/update_server_status.py`
- `/home/jeffreyklein/orangila-site/scripts/deploy_transip.sh`
- `/home/jeffreyklein/orangila-site/.env.deploy`
- `/home/jeffreyklein/orangila-site/WEBSITE_SETUP.md`
- `/home/jeffreyklein/.config/systemd/user/orangila-website-status.service`
- `/home/jeffreyklein/.config/systemd/user/orangila-website-status.timer`

## Next likely phase

- turn the homepage into a fuller OranGila landing page
- optionally replace the raw Discord invite with `orangila.com/discord`
- add server info, join guide, rules, and update blocks
