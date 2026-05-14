from django.urls import path
from . import views

urlpatterns = [
    # Main Vault Dashboard
    path('', views.user_list, name='user_list'),
    
    # Live Security Scanners (AJAX)
    path('check-username/', views.check_username_exists, name='check_username'),
    path('check-email/', views.check_email_exists, name='check_email'),
    
    # Identity Management
    path('delete/<int:pk>/', views.delete_user, name='delete_user'),
    path('recover/<int:pk>/', views.recover_user, name='recover_user'),
    path('purge/<int:pk>/', views.permanent_purge, name='permanent_purge'),
    
    # Data Operations
    path('export/', views.export_users_csv, name='export_users'),
]