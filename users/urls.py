# users/urls.py
from django.urls import path
from .views import (
    RegisterView,
    VerifyEmailView,
    ResendVerificationView,
    check_verification_status,
    send_test_email,           # Optional
    send_welcome_email_view,   # Optional
    LogoutAllView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetTokenValidateView,
    PasswordResetRequestView
)


urlpatterns = [
    # Authentication endpoints
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify_email'),
    path('resend-verification/', ResendVerificationView.as_view(), name='resend_verification'),
    
    # Status check
    path('check-verification/', check_verification_status, name='check_verification'),
    
    # Optional testing endpoints (protect these in production!)
    path('send-test-email/', send_test_email, name='send_test_email'),  # DEBUG only
    path('send-welcome-email/', send_welcome_email_view, name='send_welcome_email'),

    # Logout endpoints
    path('logout/', LogoutView.as_view(), name='logout'),
    # logout fromall devices
    path('logout-all/', LogoutAllView.as_view(), name='logout_all'),

    # Password reset
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/validate/<uuid:token>/', PasswordResetTokenValidateView.as_view(), name='password_reset_validate'),

]