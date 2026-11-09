"""
REST API views for JWT token-based authentication.

These endpoints allow the frontend to obtain, refresh, and revoke JWT tokens,
enabling stateless authentication that works reliably on Vercel serverless.
"""

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
        # Include profile info if available
        if hasattr(self.user, 'profile'):
            data['profile'] = {
                'role': self.user.profile.role,
                'tenant': {
                    'id': self.user.profile.tenant.id,
                    'name': self.user.profile.tenant.name,
                },
                'is_superadmin': self.user.profile.is_superadmin,
            }
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
    
    # Include profile info if available
    if hasattr(user, 'profile'):
        profile = user.profile
        data['profile'] = {
            'role': profile.role,
            'is_superadmin': profile.is_superadmin,
            'tenant': {
                'id': profile.tenant.id,
                'name': profile.tenant.name,
            },
        }
    
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
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(username=username, password=password)
    if user is None:
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
    if hasattr(user, 'profile'):
        data['profile'] = {
            'role': user.profile.role,
            'tenant': {
                'id': user.profile.tenant.id,
                'name': user.profile.tenant.name,
            },
            'is_superadmin': user.profile.is_superadmin,
        }
    
    return Response(data, status=status.HTTP_200_OK)
