from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Tenant, Profile


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'member_count', 'user_count', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'email', 'phone']
    readonly_fields = ['member_count', 'user_count', 'created_at', 'updated_at']


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    readonly_fields = ['tenant', 'is_superadmin']
    fields = ['tenant', 'role', 'is_superadmin', 'department', 'phone']


class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]
    list_display = ['username', 'email', 'get_role', 'get_tenant', 'get_superadmin', 'is_active']
    list_filter = ['profile__role', 'profile__is_superadmin', 'profile__tenant', 'is_active']
    search_fields = ['username', 'email', 'profile__tenant__name']

    @admin.display(description='Role')
    def get_role(self, obj):
        return obj.profile.role
    @admin.display(description='Tenant')
    def get_tenant(self, obj):
        return obj.profile.tenant.name
    @admin.display(description='Super Admin', boolean=True)
    def get_superadmin(self, obj):
        return obj.profile.is_superadmin


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
