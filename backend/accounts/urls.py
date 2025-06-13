from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('user-profile/', views.user_profile, name='user_profile'),
    path('admin/users/', views.get_all_users, name='get_all_users'),
    path('admin/users/<int:user_id>/verify/', views.verify_user, name='verify_user'),
] 