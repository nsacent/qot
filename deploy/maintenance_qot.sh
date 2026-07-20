#!/usr/bin/env bash
set -Eeuo pipefail

API_DIR="/home/qot.ug/public_html/api"

cd "${API_DIR}"
DJANGO_SETTINGS_MODULE=config.settings.prod venv/bin/python manage.py expire_listings
DJANGO_SETTINGS_MODULE=config.settings.prod venv/bin/python manage.py expire_featured_listings
DJANGO_SETTINGS_MODULE=config.settings.prod venv/bin/python manage.py cleanup_pending_images
DJANGO_SETTINGS_MODULE=config.settings.prod venv/bin/python manage.py flushexpiredtokens
