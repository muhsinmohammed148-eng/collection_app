from django.contrib import admin
from .models import Member, Payment


class StatusFilter(admin.SimpleListFilter):
    title = 'Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return [
            ('up-to-date', 'Up to Date'),
            ('advance', 'In Advance'),
            ('behind', 'Behind'),
            ('unpaid', 'Unpaid'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'up-to-date':
            return [m for m in queryset if m.status == 'up-to-date']
        elif self.value() == 'advance':
            return [m for m in queryset if m.status == 'advance']
        elif self.value() == 'behind':
            return [m for m in queryset if m.status == 'behind']
        elif self.value() == 'unpaid':
            return [m for m in queryset if m.status == 'unpaid']
        return queryset


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'tenant', 'email', 'phone', 'monthly_due', 'status', 'is_active', 'created_at']
    list_filter = [StatusFilter, 'tenant', 'is_active', 'start_date']
    search_fields = ['name', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at', 'total_paid', 'current_balance_owed', 'advance_balance', 'status']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['member', 'member_tenant', 'amount', 'method', 'date', 'note']
    list_filter = ['method', 'date', 'member__tenant']
    search_fields = ['member__name', 'note']
    readonly_fields = ['created_at', 'member_tenant']

    def member_tenant(self, obj):
        return obj.member.tenant.name
    member_tenant.short_description = 'Tenant'
