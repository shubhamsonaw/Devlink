from django.urls import path
from importlib import import_module

TokenVerifyView = import_module('rest_framework_simplejwt.views').TokenVerifyView

from .api_views import (
    CurrentUserAPIView,
    ThrottledTokenBlacklistView,
    ThrottledTokenObtainPairView,
    ThrottledTokenRefreshView,
)


urlpatterns = [
    path('token/', ThrottledTokenObtainPairView.as_view(), name='jwt_token_obtain'),
    path('token/refresh/', ThrottledTokenRefreshView.as_view(), name='jwt_token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='jwt_token_verify'),
    path('token/blacklist/', ThrottledTokenBlacklistView.as_view(), name='jwt_token_blacklist'),
    path('me/', CurrentUserAPIView.as_view(), name='jwt_current_user'),
]
