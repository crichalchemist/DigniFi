"""
User views: registration (public) and current-user profile (authenticated).
"""

from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer, UserProfileSerializer

User = get_user_model()

_DEMO_USERNAME = "demo_maria"


class RegisterView(generics.CreateAPIView):
    """POST /api/users/register/ — create a new account."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class CurrentUserView(generics.RetrieveAPIView):
    """GET /api/users/me/ — return the authenticated user's profile."""

    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user


class DemoLoginView(APIView):
    """POST /api/users/demo/ — issue JWT tokens for the pre-seeded demo account.

    Returns 503 if seed_demo_data has not been run yet.
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        try:
            user = User.objects.get(username=_DEMO_USERNAME)
        except User.DoesNotExist:
            return Response(
                {"detail": "Demo account not available. Run: python manage.py seed_demo_data"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})
