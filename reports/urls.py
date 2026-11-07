from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('matrix/', views.monthly_matrix, name='monthly_matrix'),
    path('matrix/export/', views.export_monthly_matrix_csv, name='export_monthly_matrix_csv'),
    path('status/', views.status_report, name='status_report'),
    path('export/', views.export_csv, name='export_csv'),
    path('member/<int:member_pk>/yearly-history/', views.yearly_history, name='yearly_history'),
    path('yearly/', views.yearly_report, name='yearly_report'),
    path('yearly/<int:year>/', views.yearly_report, name='yearly_report'),
    path('yearly/<int:year>/export/', views.export_yearly_report_csv, name='export_yearly_report_csv'),
    # Expenses
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/add/', views.expense_create, name='expense_create'),
    path('expenses/<int:expense_pk>/delete/', views.expense_delete, name='expense_delete'),
]
