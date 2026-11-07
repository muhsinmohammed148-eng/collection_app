from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    # Tenant management (superadmin only)
    path('tenants/', views.tenant_list, name='tenant_list'),
    path('tenants/add/', views.tenant_create, name='tenant_create'),
    path('tenants/<int:pk>/', views.tenant_detail, name='tenant_detail'),
    path('tenants/<int:pk>/delete/', views.tenant_delete, name='tenant_delete'),
    path('tenants/switch/', views.tenant_switch, name='tenant_switch'),
    path('tenants/<int:tenant_pk>/users/add/', views.tenant_user_form, name='tenant_user_add'),
    path('tenants/<int:tenant_pk>/users/<int:user_pk>/edit/', views.tenant_user_form, name='tenant_user_edit'),
    path('tenants/<int:tenant_pk>/users/<int:user_pk>/remove/', views.tenant_user_remove, name='tenant_user_remove'),
    # Member credentials
    path('member/<int:member_pk>/credentials/', views.member_credentials, name='member_credentials'),
]
