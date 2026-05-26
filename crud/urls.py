from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    # Root redirect — always go to login first
    path('', RedirectView.as_view(url='/login/', permanent=False)),

    # Portal Security Authentication Gateway
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Main Vault Dashboard
    path('dashboard/', views.user_list, name='user_list'),
    
    # Live Security Scanners (AJAX)
    path('check-username/', views.check_username_exists, name='check_username'),
    path('check-email/', views.check_email_exists, name='check_email'),
    
    # Identity Management
    path('delete/<int:pk>/', views.delete_user, name='delete_user'),
    path('recover/<int:pk>/', views.recover_user, name='recover_user'),
    path('purge/<int:pk>/', views.permanent_purge, name='permanent_purge'),
    
    # Bulk Core Matrix Operations
    path('bulk-archive/', views.bulk_archive, name='bulk_archive'),
    path('bulk-archive-action/', views.bulk_archive_action, name='bulk_archive_action'),
    
    # Data Operations
    path('export/', views.export_users_csv, name='export_users'),
]