"""
Middleware for Vercel deployments and JWT token authentication.

1. VercelOriginTrustMiddleware — dynamically trusts request origins on Vercel.
2. TokenAuthenticationMiddleware — validates JWT tokens from the Authorization
   header and sets request.user, so all Django views work with token-based auth.
   This solves the Vercel serverless session problem where each function instance
   has a separate /tmp/ database and can't share session data.
"""

import os
from django.conf import settings
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


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


class TokenAuthenticationMiddleware:
    """
    Extract JWT token from the Authorization header and authenticate the user.
    
    This middleware runs AFTER Django's AuthenticationMiddleware, so it only
    sets request.user when session auth could not find a user (AnonymousUser).
    It checks for a Bearer token in the Authorization header and validates
    it against the JWT secret.
    
    This is the key fix for the Vercel serverless session problem: instead of
    relying on server-side sessions (which are lost across cold starts), the
    user's identity is carried in a signed JWT token stored on the client.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only authenticate via JWT if session auth did not find a user
        if request.user.is_authenticated:
            response = self.get_response(request)
            return response

        # Try to get the JWT token from:
        # 1. Authorization: Bearer <token> header (fetch/XHR calls)
        # 2. payflow_jwt cookie (regular page navigations)
        # Cookies are sent automatically with every browser request,
        # which is the key fix for Vercel serverless cold starts.
        token_str = None

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token_str = auth_header[7:]  # Strip 'Bearer ' prefix
        elif 'payflow_jwt' in request.COOKIES:
            token_str = request.COOKIES['payflow_jwt']

        if token_str:
            try:
                # Validate and decode the JWT token
                token = AccessToken(token_str)
                user_id = token['user_id']

                # Look up the user from the database
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    user = User.objects.get(pk=user_id, is_active=True)
                    request.user = user
                except User.DoesNotExist:
                    pass  # Leave as AnonymousUser
            except (InvalidToken, TokenError, KeyError, ValueError):
                pass  # Leave as AnonymousUser

        response = self.get_response(request)
        return response
