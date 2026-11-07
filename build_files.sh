#!/bin/bash

# Exit on error
set -e

# Install dependencies
# Use uv pip if available (Vercel uses uv-managed Python), otherwise fall back to pip with --break-system-packages
if command -v uv &> /dev/null; then
    uv pip install --system -r requirements.txt
else
    pip install --break-system-packages -r requirements.txt
fi

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate --noinput

# Create staticfiles directory if it doesn't exist
mkdir -p staticfiles
