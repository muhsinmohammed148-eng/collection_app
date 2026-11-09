from django.urls import path
from . import api_views

app_name = 'accounts_api'

urlpatterns = [
    # Token authentication endpoints
    path('token/', api_views.token_obtain_pair, name='token_obtain_pair'),
    path('token/refresh/', api_views.token_refresh, name='token_refresh'),
    path('login/', api_views.token_obtain_pair_with_credentials, name='token_login'),
    path('logout/', api_views.token_blacklist_view, name='token_logout'),
    path('user/', api_views.user_info, name='user_info'),
]
