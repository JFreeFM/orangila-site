# OranGila Website Setup

Status date: 2026-03-21

## Current state

The OranGila website is now managed from this server and deployed directly to TransIP.

Live workspace:
- `/home/jeffreyklein/orangila-site`

Live TransIP webroot:
- `/data/sites/web/orangilacom/www`

Current published files:
- `index.html`
- `styles.css`
- `OranGilanewserver.png`
- `status.json`
- `robots.txt`
- `sitemap.xml`

Current live URL:
- `https://orangila.com`

## Deploy model

Deploy is done from this server over SSH using a dedicated deploy key.

Deploy script:
- `/home/jeffreyklein/orangila-site/scripts/deploy_transip.sh`

Local deploy config:
- `/home/jeffreyklein/orangila-site/.env.deploy`

SSH deploy key on this server:
- `/home/jeffreyklein/.ssh/transip_orangila_ed25519`

## Current homepage

The current first version includes:
- full-screen hero image using `OranGilanewserver.png`
- centered overlay content
- `ORANGILA DAYZ` brand mark positioned top-left outside the hero image
- CTA button text:
  - `Join Our DayZ Server`
- CTA button target:
  - `https://discord.gg/SZdwUpmTXp`
- red/white visual direction
- core DayZ server info
- live server status badge on the homepage
- basic SEO metadata for search and social previews

Current status states:
- `Online` (green)
- `Restart Soon` (orange)
- `Scheduled Restart` (orange)
- `Maintenance` (orange)
- `Offline` (red)

Main files:
- `/home/jeffreyklein/orangila-site/site/index.html`
- `/home/jeffreyklein/orangila-site/site/styles.css`

## Verified live checks

Confirmed:
- `orangila.com` resolves to TransIP:
  - IPv4: `85.10.159.194`
  - IPv6: `2a01:7c8:f0:1111:0:2:b05a:2d60`
- HTTP responds and redirects to HTTPS
- HTTPS responds successfully with the correct deployed homepage
- live certificate is now Let's Encrypt:
  - subject: `orangila.com`
  - issuer: `Let's Encrypt R12`
- TransIP webroot contains the expected uploaded files

## Deploy command

```bash
cd /home/jeffreyklein/orangila-site
./scripts/deploy_transip.sh
```

Dry-run check:

```bash
cd /home/jeffreyklein/orangila-site
./scripts/deploy_transip.sh --dry-run
```

## Notes

- The old `index.php` placeholder in the TransIP webroot was replaced by the static site.
- Future changes can be made locally in `site/` and then published with the deploy script.
- The deploy script now validates the SSH key path and refuses unsafe empty or root target paths.
- Website server status is generated locally from the DayZ runtime state and published through `site/status.json`.
- Basic SEO files now ship with the site:
  - `site/robots.txt`
  - `site/sitemap.xml`
- The status updater runs as:
  - `/home/jeffreyklein/.config/systemd/user/orangila-website-status.service`
  - `/home/jeffreyklein/.config/systemd/user/orangila-website-status.timer`
- Status source logic:
  - `dayz.service` active -> base online signal
  - scheduled restart runtime lock -> `Scheduled Restart`
  - maintenance lock -> `Maintenance`
  - next scheduled restart within 15 minutes -> `Restart Soon`
  - inactive DayZ service -> `Offline`
- Public status source:
  - `https://orangila.com/status.json`
- Browser note:
  - after a restart or status flip, browsers may briefly show a cached older state until a hard refresh or cache-bypassed request is used
- A later improvement is to point the homepage CTA to a branded Discord landing route such as `orangila.com/discord`.
- The current Discord CTA already uses a permanent invite created via the Discord bot.
