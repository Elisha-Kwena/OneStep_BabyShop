# users/urls.py
from django.urls import path
from .views.auth import (
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

from .views.profile import (
    UserProfileRetrieveUpdateView,
    UserProfileMinimalView,
    UserDashboardView,
    UserAddressListView,
    UserAddressCreateView,
    UserAddressRetrieveUpdateDestroyView,
    NotificationPreferencesRetrieveUpdateView,
    NotificationChannelsUpdateView,
    LoyaltyPointsHistoryListView,
    UserActivityLogListView
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



    # Profile URLs
    path('user/profile/', UserProfileRetrieveUpdateView.as_view(), name='user-profile'),
    path('user/profile/minimal/', UserProfileMinimalView.as_view(), name='user-profile-minimal'),
    path('user/dashboard/', UserDashboardView.as_view(), name='user-dashboard'),
    
    # Address URLs
    path('user/addresses/', UserAddressListView.as_view(), name='address-list'),
    path('user/addresses/create/', UserAddressCreateView.as_view(), name='address-create'),
    path('user/addresses/<uuid:id>/', UserAddressRetrieveUpdateDestroyView.as_view(), name='address-detail'),
    
    # Notification URLs
    path('user/notifications/', NotificationPreferencesRetrieveUpdateView.as_view(), name='notification-preferences'),
    path('user/notifications/channels/', NotificationChannelsUpdateView.as_view(), name='notification-channels'),
    
    # Loyalty URLs
    path('user/loyalty/history/', LoyaltyPointsHistoryListView.as_view(), name='loyalty-history'),
    
    # Activity URLs
    path('user/activity/', UserActivityLogListView.as_view(), name='user-activity'),

]

