"""
Middleware to dynamically trust request origins on Vercel deployments.

Django's CSRF_TRUSTED_ORIGINS setting doesn't support wildcards for arbitrary
custom domains. This middleware adds the request's origin to CSRF_TRUSTED_ORIGINS
at runtime when running on Vercel, so custom domains work without manual configuration.

Also ensures that Vercel's HTTPS requests are properly recognized as secure,
since Vercel terminates SSL at the edge and may not always send X-Forwarded-Proto.
"""

import os
from django.conf import settings


class VercelOriginTrustMiddleware:
    """
    Dynamically add the request's origin to CSRF_TRUSTED_ORIGINS when running on Vercel.
    
    This allows custom domains (like collection.nexflowsoft.com) to work without
    pre-configuring CSRF_TRUSTED_ORIGINS, while still maintaining CSRF protection.
    Only active when ON_VERCEL=True for safety.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only active on Vercel — local development doesn't need this
        on_vercel = os.getenv('VERCEL', '').lower() in ('true', '1', 'yes')
        
        if on_vercel:
            # Build the origin from the request's host and scheme
            # On Vercel, all requests are HTTPS — force the scheme to https
            host = request.get_host()
            # Vercel always serves HTTPS, so force scheme to https
            # This fixes the issue where X-Forwarded-Proto header may be missing
            scheme = 'https'
            origin = f'{scheme}://{host}'
            
            # Add to CSRF_TRUSTED_ORIGINS if not already present
            if not hasattr(settings, '_csrf_origins_initialized'):
                settings._csrf_origins_initialized = True
            
            if origin not in settings.CSRF_TRUSTED_ORIGINS:
                settings.CSRF_TRUSTED_ORIGINS.append(origin)
        
        response = self.get_response(request)
        return response
