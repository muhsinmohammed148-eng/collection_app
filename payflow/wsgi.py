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


# On Vercel, run migrations on cold start since the database is in /tmp.
# Static files are collected during the build phase, not at runtime.
on_vercel = os.getenv('VERCEL', '').lower() in ('true', '1', 'yes')
if on_vercel:
    import pathlib
    project_root = pathlib.Path(__file__).resolve().parent.parent
    
    try:
        # Run migrations (required for SQLite in /tmp)
        subprocess.run(
            [sys.executable, str(project_root / 'manage.py'), 'migrate', '--noinput'],
            check=True,
            capture_output=True,
            cwd=str(project_root),
        )
    except Exception:
        pass
    
    # Auto-create default superuser so login always works on Vercel
    # (SQLite in /tmp is ephemeral — database resets on every cold start)
    try:
        import django
        django.setup()
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@nexflowsoft.com',
                password='admin123',
            )
    except Exception:
        pass
