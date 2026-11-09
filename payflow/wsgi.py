"""
WSGI config for payflow project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import subprocess
import sys

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'payflow.settings')

application = get_wsgi_application()

# Vercel expects the WSGI app to be named `app`
app = application


# On Vercel, run migrations and collect static files on cold start
# since the build step does not run these commands.
# This runs once per function cold start.
on_vercel = os.getenv('VERCEL', '').lower() in ('true', '1', 'yes')
if on_vercel:
    # Find manage.py location (project root)
    import pathlib
    project_root = pathlib.Path(__file__).resolve().parent.parent
    
    try:
        # Run migrations first (required for SQLite in /tmp)
        subprocess.run(
            [sys.executable, str(project_root / 'manage.py'), 'migrate', '--noinput'],
            check=True,
            capture_output=True,
            cwd=str(project_root),
        )
    except Exception:
        pass
    
    try:
        # Collect static files for WhiteNoise
        subprocess.run(
            [sys.executable, str(project_root / 'manage.py'), 'collectstatic', '--noinput'],
            check=True,
            capture_output=True,
            cwd=str(project_root),
        )
    except Exception:
        # If collectstatic fails, the app will still work but static files may be missing
        pass
