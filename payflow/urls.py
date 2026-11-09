"""
URL configuration for payflow project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('api/auth/', include('accounts.api_urls')),
    path('members/', include('members.urls')),
    path('', include('reports.urls')),
]
