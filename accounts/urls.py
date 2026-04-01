from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path('register/patient/', views.RegisterPatientView.as_view(), name='register-patient'),
    path('register/agent/', views.RegisterAgentView.as_view(), name='register-agent'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('verify-otp/', views.VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-otp/', views.ResendOTPView.as_view(), name='resend-otp'),
    path('password/reset/', views.PasswordResetRequestView.as_view(), name='password-reset'),
    path('password/confirm/', views.PasswordResetConfirmView.as_view(), name='password-confirm'),
    path('password/change/', views.ChangePasswordView.as_view(), name='password-change'),
    path('me/', views.MeView.as_view(), name='me'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
]
