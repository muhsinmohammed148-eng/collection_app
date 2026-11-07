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

# Create staticfiles directory if it doesn't exist
mkdir -p staticfiles

# Note: migrations are NOT run here because the build environment
# doesn't have access to the production database.
# Run migrations manually after deployment:
#   vercel exec --confirm python manage.py migrate
# Or connect to your database and run:
#   python manage.py migrate
