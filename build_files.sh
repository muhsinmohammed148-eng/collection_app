#!/bin/bash
# Vercel build script — runs collectstatic so static files are included in the deployment bundle.
# @vercel/python auto-installs dependencies from requirements.txt before running this script.
set -e

# Collect static files into /var/task/staticfiles (included in the deployment bundle)
export DJANGO_SETTINGS_MODULE=payflow.settings
python manage.py collectstatic --noinput
