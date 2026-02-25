"""
User views: registration (public) and current-user profile (authenticated).
"""

from rest_framework import generics, permissions

from .serializers import RegisterSerializer, UserProfileSerializer


class RegisterView(generics.CreateAPIView):
    """POST /api/users/register/ — create a new account."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class CurrentUserView(generics.RetrieveAPIView):
    """GET /api/users/me/ — return the authenticated user's profile."""

    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user
