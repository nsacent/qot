#!/usr/bin/env bash
set -Eeuo pipefail

API_DIR="/home/qot.ug/public_html/api"
WEB_DIR="/home/qot.ug/public_html/web"
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
npm run build

systemctl restart qot-web.service

curl --fail --silent --show-error --location --max-time 30 \
    --retry 15 --retry-delay 2 --retry-all-errors \
    https://api.qot.ug/api/v1/listings/ >/dev/null
curl --fail --silent --show-error --location --max-time 30 \
    --retry 15 --retry-delay 2 --retry-all-errors \
    https://qot.ug/ >/dev/null

echo "QOT deployment completed successfully."
