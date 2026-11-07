#!/bin/bash

# Exit on error
set -e

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate --noinput

# Create staticfiles directory if it doesn't exist
mkdir -p staticfiles
