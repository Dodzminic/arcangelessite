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

    # Employee Record — QR scan target (no login required, works on LAN)
    path('employee/<str:emp_id>/record/', views.employee_record, name='employee_record'),
]


# ═══ ADMIN REGISTRATION + FACE ID + ADMIN PANEL (added) ═══
from . import admin_registration, facial_verification, admin_panel

urlpatterns += [
    path('admin-register/', admin_registration.register_start, name='admin_register'),
    path('admin-register/form/', admin_registration.register_form, name='admin_register_form'),
    path('admin-register/pending/', admin_registration.register_pending, name='admin_register_pending'),
    path('admin-approve/<str:token>/', admin_registration.approve_request, name='admin_approve'),

    path('face-login/', facial_verification.face_login_page, name='face_login'),
    path('face-login/verify/', facial_verification.face_login_verify, name='face_login_verify'),

    # Admin Approvals panel (superuser + emailed unlock code)
    path('admin-panel/', admin_panel.panel_home, name='admin_panel'),
    path('admin-panel/unlock/', admin_panel.panel_unlock, name='admin_panel_unlock'),
]