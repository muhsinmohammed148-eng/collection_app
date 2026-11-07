#!/bin/bash

# Exit on error
set -e

# Install dependencies
# Vercel uses uv-managed Python (PEP 668), so we must set PIP_BREAK_SYSTEM_PACKAGES=1
# This is the most reliable workaround that works across all Vercel Python versions
export PIP_BREAK_SYSTEM_PACKAGES=1
pip install -r requirements.txt

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
