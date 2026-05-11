from django.urls import path
from . import views

urlpatterns = [
    path('', views.user_list, name='user_list'), 
    path('add/', views.add_user, name='add_user'),
    path('edit/<int:pk>/', views.edit_user, name='edit_user'),
    path('delete/<int:pk>/', views.delete_user, name='delete_user'),
]