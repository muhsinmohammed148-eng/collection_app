#!/bin/bash
# Exit on error
set -e

# Install dependencies
# Vercel uses uv-managed Python (PEP 668), so we must set PIP_BREAK_SYSTEM_PACKAGES=1
# This is the most reliable workaround that works across all Vercel Python versions
export PIP_BREAK_SYSTEM_PACKAGES=1
pip install -r requirements.txt

# Collect static files — WhiteNoise will serve them from staticfiles/
python manage.py collectstatic --noinput
