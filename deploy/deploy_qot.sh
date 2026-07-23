#!/usr/bin/env bash
set -Eeuo pipefail

API_DIR="/home/qot.ug/public_html/api"
WEB_DIR="/home/qot.ug/public_html/web"
WEB_BUILD_DIR="${WEB_DIR}/.next-build"
WEB_PREVIOUS_DIR="${WEB_DIR}/.next-previous"
BACKUP_SCRIPT="/home/qot.ug/backup_qot.sh"
LOCK_FILE="/run/lock/qot-deploy.lock"

if [[ "${EUID}" -ne 0 ]]; then
    echo "QOT deployment must run as root." >&2
    exit 1
fi

exec 9>"${LOCK_FILE}"
if ! flock -w 1800 9; then
    echo "Timed out waiting for another QOT deployment to finish." >&2
    exit 1
fi

if [[ -x "${BACKUP_SCRIPT}" ]]; then
    "${BACKUP_SCRIPT}"
fi

cd "${API_DIR}"
git pull --ff-only origin main
venv/bin/pip install --disable-pip-version-check -r requirements/prod.txt
DJANGO_SETTINGS_MODULE=config.settings.prod venv/bin/python manage.py migrate --noinput
DJANGO_SETTINGS_MODULE=config.settings.prod venv/bin/python manage.py collectstatic --noinput
DJANGO_SETTINGS_MODULE=config.settings.prod venv/bin/python manage.py expire_listings
DJANGO_SETTINGS_MODULE=config.settings.prod venv/bin/python manage.py expire_featured_listings
DJANGO_SETTINGS_MODULE=config.settings.prod venv/bin/python manage.py cleanup_pending_images

systemctl restart qot-api.service

cd "${WEB_DIR}"
git pull --ff-only origin main
npm ci

# Build beside the live output so the running Next.js process never reads a
# partially-written client manifest during back-to-back deployments.
rm -rf -- "${WEB_BUILD_DIR}"
NEXT_DIST_DIR=".next-build" npm run build

if [[ ! -f "${WEB_BUILD_DIR}/BUILD_ID" ]]; then
    echo "QOT web build did not produce a BUILD_ID." >&2
    exit 1
fi

rm -rf -- "${WEB_PREVIOUS_DIR}"
systemctl stop qot-web.service

if [[ -d "${WEB_DIR}/.next" ]]; then
    mv "${WEB_DIR}/.next" "${WEB_PREVIOUS_DIR}"
fi

if ! mv "${WEB_BUILD_DIR}" "${WEB_DIR}/.next"; then
    if [[ -d "${WEB_PREVIOUS_DIR}" ]]; then
        mv "${WEB_PREVIOUS_DIR}" "${WEB_DIR}/.next"
    fi
    systemctl start qot-web.service
    exit 1
fi

if systemctl start qot-web.service && \
    curl --fail --silent --show-error --max-time 30 \
        --retry 15 --retry-delay 2 --retry-all-errors \
        http://127.0.0.1:3001/login >/dev/null; then
    rm -rf -- "${WEB_PREVIOUS_DIR}"
else
    echo "New QOT web release failed its health check; rolling back." >&2
    systemctl stop qot-web.service || true
    rm -rf -- "${WEB_DIR}/.next"

    if [[ -d "${WEB_PREVIOUS_DIR}" ]]; then
        mv "${WEB_PREVIOUS_DIR}" "${WEB_DIR}/.next"
    fi

    systemctl start qot-web.service
    exit 1
fi

curl --fail --silent --show-error --location --max-time 30 \
    --retry 15 --retry-delay 2 --retry-all-errors \
    https://api.qot.ug/api/v1/listings/ >/dev/null
curl --fail --silent --show-error --location --max-time 30 \
    --retry 15 --retry-delay 2 --retry-all-errors \
    https://qot.ug/ >/dev/null

echo "QOT deployment completed successfully."
