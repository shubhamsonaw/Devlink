from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
)


class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'jwt_obtain'


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'jwt_refresh'


class ThrottledTokenBlacklistView(TokenBlacklistView):
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'jwt_blacklist'


class CurrentUserAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response({
            'id': request.user.pk,
            'username': request.user.get_username(),
            'email': request.user.email,
        })
