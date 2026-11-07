from django.urls import path
from . import views

app_name = 'members'

urlpatterns = [
    path('', views.member_list, name='list'),
    path('add/', views.member_create, name='create'),
    path('<int:pk>/', views.member_detail, name='detail'),
    path('<int:pk>/edit/', views.member_update, name='update'),
    path('<int:pk>/delete/', views.member_delete, name='delete'),
    path('payment/', views.payment_record, name='payment_record'),
    path('<int:pk>/payment/', views.payment_record, name='payment_record_for'),
    path('my-dashboard/', views.my_dashboard, name='my_dashboard'),
]
