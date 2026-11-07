#!/bin/bash

# Exit on error
set -e

# Install dependencies (use --break-system-packages for uv-managed Python on Vercel)
pip install --break-system-packages -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate --noinput

# Create staticfiles directory if it doesn't exist
mkdir -p staticfiles
