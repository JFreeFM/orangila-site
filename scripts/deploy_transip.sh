#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SITE_DIR="${ROOT_DIR}/site/"
ENV_FILE="${ROOT_DIR}/.env.deploy"
DRY_RUN=0

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

if [[ ! -d "${SITE_DIR}" ]]; then
  echo "site directory missing: ${SITE_DIR}" >&2
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "deploy env file missing: ${ENV_FILE}" >&2
  exit 1
fi

set -a
source "${ENV_FILE}"
set +a

: "${TRANSIP_HOST:?TRANSIP_HOST is required}"
: "${TRANSIP_USER:?TRANSIP_USER is required}"
: "${TRANSIP_TARGET_DIR:?TRANSIP_TARGET_DIR is required}"
: "${TRANSIP_SSH_KEY_PATH:?TRANSIP_SSH_KEY_PATH is required}"

if [[ ! -f "${TRANSIP_SSH_KEY_PATH}" ]]; then
  echo "ssh key missing: ${TRANSIP_SSH_KEY_PATH}" >&2
  exit 1
fi

if [[ "${TRANSIP_TARGET_DIR}" == "/" || "${TRANSIP_TARGET_DIR}" == "" ]]; then
  echo "unsafe target dir: ${TRANSIP_TARGET_DIR}" >&2
  exit 1
fi

RSYNC_ARGS=(
  -avz
  --delete
  --exclude=".DS_Store"
  -e "ssh -i ${TRANSIP_SSH_KEY_PATH} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
)

if [[ "${DRY_RUN}" == "1" ]]; then
  RSYNC_ARGS+=(--dry-run)
fi

rsync \
  "${RSYNC_ARGS[@]}" \
  "${SITE_DIR}" \
  "${TRANSIP_USER}@${TRANSIP_HOST}:${TRANSIP_TARGET_DIR}"
