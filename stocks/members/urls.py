from django.contrib import admin
from django.urls import path
from members.views import user_login, user_registration, user_logout
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('login/', user_login, name='user_login'),
    path('register/', user_registration, name='user_register'),
    path('logout/', user_logout, name='user_logout'),
    
    path('password_reset', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset_done', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password_reset_confirm/<uidb64>/<token>', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password_reset_complete', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
