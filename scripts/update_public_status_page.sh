#!/usr/bin/env bash
set -euo pipefail

/home/jeffreyklein/dayzserver/.venv-dayz-bot/bin/python /home/jeffreyklein/orangila-site/scripts/build_status_page.py
/home/jeffreyklein/orangila-site/scripts/deploy_transip.sh
