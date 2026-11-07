from django.contrib import admin
from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['amount', 'category', 'date', 'tenant', 'description']
    list_filter = ['category', 'date', 'tenant']
    search_fields = ['description', 'tenant__name']
    date_hierarchy = 'date'
