from django.contrib import admin
from django.urls import path,include

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
    TokenBlacklistView,
)
from users.views import VerifiedEmailLoginView
urlpatterns = [
    path('admin/', admin.site.urls),

    # ==================api/v1=====================
    # authentication
    path('api/token/', VerifiedEmailLoginView.as_view(), name='token_obtain_pair'),#<==== Login endpoint
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),


    path("api/v1/auth/",include("users.urls")), #<=== Register endpoint 
  
]