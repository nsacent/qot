#!/usr/bin/env bash
set -Eeuo pipefail

API_DIR="/home/qot.ug/public_html/api"
BACKUP_DIR="/home/qot.ug/backups"
STAMP="$(date -u +%Y%m%d-%H%M%S)"

mkdir -p "${BACKUP_DIR}"

set -a
# The production environment file is maintained by the server administrator.
# shellcheck disable=SC1091
source "${API_DIR}/.env"
set +a

PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    --host="${POSTGRES_HOST:-127.0.0.1}" \
    --port="${POSTGRES_PORT:-5432}" \
    --username="${POSTGRES_USER}" \
    --format=custom \
    --file="${BACKUP_DIR}/qot-db-${STAMP}.dump" \
    "${POSTGRES_DB}"

tar -C "${API_DIR}" -czf "${BACKUP_DIR}/qot-media-${STAMP}.tar.gz" media

sha256sum \
    "${BACKUP_DIR}/qot-db-${STAMP}.dump" \
    "${BACKUP_DIR}/qot-media-${STAMP}.tar.gz" \
    >"${BACKUP_DIR}/qot-${STAMP}.sha256"

find "${BACKUP_DIR}" -type f -name 'qot-db-*.dump' -mtime +30 -delete
find "${BACKUP_DIR}" -type f -name 'qot-media-*.tar.gz' -mtime +30 -delete
find "${BACKUP_DIR}" -type f -name 'qot-*.sha256' -mtime +30 -delete

echo "QOT backup completed: ${STAMP}"
