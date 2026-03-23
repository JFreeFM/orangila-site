#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${ORANGILA_STATUS_PYTHON:-python3}"

"${PYTHON_BIN}" "${ROOT_DIR}/scripts/build_status_page.py"
"${ROOT_DIR}/scripts/deploy_transip.sh"
