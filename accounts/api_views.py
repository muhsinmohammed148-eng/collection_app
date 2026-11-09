"""
REST API views for JWT token-based authentication.

These endpoints allow the frontend to obtain, refresh, and revoke JWT tokens,
enabling stateless authentication that works reliably on Vercel serverless.
"""

import os
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.contrib.auth.models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom serializer that includes user details in the token response."""
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['username'] = user.username
        token['user_id'] = user.id
        token['email'] = user.email
        return token

    def validate(self, attrs):
        import logging
        logger = logging.getLogger(__name__)
        data = super().validate(attrs)
        # Add user info to response
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'is_staff': self.user.is_staff,
        }
        # Include profile info if available — handle missing profile/tenant gracefully
        try:
            if hasattr(self.user, 'profile') and self.user.profile.tenant:
                data['profile'] = {
                    'role': self.user.profile.role,
                    'tenant': {
                        'id': self.user.profile.tenant.id,
                        'name': self.user.profile.tenant.name,
                    },
                    'is_superadmin': self.user.profile.is_superadmin,
                }
            else:
                logger.warning(f'Token obtain for {self.user.username}: user has no profile or tenant')
        except Exception as e:
            logger.error(f'Token obtain for {self.user.username}: error accessing profile: {e}', exc_info=True)
        return data


@api_view(['POST'])
@permission_classes([AllowAny])
def token_obtain_pair(request):
    """
    Obtain JWT access and refresh tokens.
    
    POST /api/auth/token/
    {
        "username": "user@example.com",
        "password": "secret"
    }
    
    Returns access and refresh tokens plus user info.
    """
    serializer = CustomTokenObtainPairSerializer(data=request.data)
    try:
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)
    except Exception as e:
        # Log the real error for debugging, but don't expose it to the client
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Token obtain failed for username={request.data.get("username")}: {e}', exc_info=True)
        return Response(
            {'error': 'Invalid username or password.'},
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh(request):
    """
    Refresh an expired access token using a valid refresh token.
    
    POST /api/auth/token/refresh/
    {
        "refresh": "eyJhbGciOiJIUzI1NiIs..."
    }
    
    Returns a new access token.
    """
    refresh_token = request.data.get('refresh')
    if not refresh_token:
        return Response(
            {'error': 'Refresh token is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken(refresh_token)
        return Response({
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': 'Invalid or expired refresh token.'},
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def token_blacklist_view(request):
    """
    Logout by blacklisting the refresh token.
    
    POST /api/auth/logout/
    {
        "refresh": "eyJhbGciOiJIUzI1NiIs..."
    }
    """
    refresh_token = request.data.get('refresh')
    if not refresh_token:
        return Response(
            {'error': 'Refresh token is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken(refresh_token)
        refresh.blacklist()
        return Response(
            {'message': 'Successfully logged out.'},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'error': 'Invalid refresh token.'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info(request):
    """
    Get current authenticated user's information.
    
    GET /api/auth/user/
    
    Returns user details and profile information.
    """
    user = request.user
    data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_staff': user.is_staff,
        'is_active': user.is_active,
    }
    
    # Include profile info if available — handle missing profile/tenant gracefully
    try:
        if hasattr(user, 'profile') and user.profile.tenant:
            profile = user.profile
            data['profile'] = {
                'role': profile.role,
                'is_superadmin': profile.is_superadmin,
                'tenant': {
                    'id': profile.tenant.id,
                    'name': profile.tenant.name,
                },
            }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'User info error for {user.username}: {e}', exc_info=True)
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def token_obtain_pair_with_credentials(request):
    """
    Alternative login endpoint that uses Django's authenticate() directly.
    Useful for form-based login that also needs a JWT token.
    
    POST /api/auth/login/
    {
        "username": "user@example.com",
        "password": "secret"
    }
    """
    import logging
    logger = logging.getLogger(__name__)
    
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Try case-insensitive username lookup first — Django's authenticate() is case-sensitive,
    # but users may type their username in a different case than how it was created.
    # On Vercel serverless, this also helps diagnose database sync issues.
    try:
        existing_user = User.objects.get(username__iexact=username)
        # If the case differs, use the correct case for authenticate()
        if existing_user.username != username:
            logger.info(f'Login for "{username}" -> corrected case to "{existing_user.username}"')
            username = existing_user.username
    except User.DoesNotExist:
        pass  # Will handle below after authenticate()
    
    user = authenticate(username=username, password=password)
    if user is None:
        # Debug: check if the user exists (case-insensitive) and has a valid password
        try:
            existing_user = User.objects.get(username__iexact=username)
            logger.warning(f'Login failed for {username}: user exists but auth failed. '
                          f'is_active={existing_user.is_active}, '
                          f'password_set={bool(existing_user.password)}, '
                          f'password_start={existing_user.password[:20] if existing_user.password else "EMPTY"}')
            if not existing_user.password:
                return Response(
                    {'error': 'Invalid username or password. (Account has no password set — please reset your password.)'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            if not existing_user.is_active:
                return Response(
                    {'error': 'Account is disabled.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except User.DoesNotExist:
            # User truly does not exist — log all existing users for debugging
            all_usernames = list(User.objects.values_list('username', flat=True))
            user_count = User.objects.count()
            logger.warning(f'Login failed for {username}: user does not exist. '
                          f'Total users in DB: {user_count}. '
                          f'Existing usernames: {all_usernames}')
            # Check if running on Vercel with ephemeral SQLite — common cause of "user not found"
            on_vercel = os.getenv('VERCEL', '').lower() in ('true', '1', 'yes')
            db_url = os.getenv('DATABASE_URL', '')
            if on_vercel and not db_url:
                logger.warning('WARNING: Running on Vercel without DATABASE_URL! '
                              'SQLite in /tmp/ is ephemeral — each cold start loses all data. '
                              'Set DATABASE_URL to a PostgreSQL database for persistent storage.')
        
        return Response(
            {'error': 'Invalid username or password.'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    if not user.is_active:
        return Response(
            {'error': 'Account is disabled.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    refresh = RefreshToken.for_user(user)
    
    data = {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_staff': user.is_staff,
        },
    }
    
    # Include profile info if available
    try:
        if hasattr(user, 'profile') and user.profile.tenant:
            data['profile'] = {
                'role': user.profile.role,
                'tenant': {
                    'id': user.profile.tenant.id,
                    'name': user.profile.tenant.name,
                },
                'is_superadmin': user.profile.is_superadmin,
            }
        else:
            logger.warning(f'Login for {username}: user has no profile or tenant')
    except Exception as e:
        logger.error(f'Login for {username}: error accessing profile: {e}', exc_info=True)
    
    return Response(data, status=status.HTTP_200_OK)
