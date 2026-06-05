from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import health_check, health_check_detailed, metrics


class ThrottledTokenObtainView(TokenObtainPairView):
    """Login with scoped rate limiting (production: 5/minute per IP)."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class ThrottledTokenRefreshView(TokenRefreshView):
    """Token refresh with scoped rate limiting."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health_check"),
    path("health/detailed/", health_check_detailed, name="health_check_detailed"),
    path("metrics/", metrics, name="metrics"),
    path("api/token/obtain/", ThrottledTokenObtainView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", ThrottledTokenRefreshView.as_view(), name="token_refresh"),
    path("api/users/", include("apps.users.urls")),
    path("api/intake/", include("apps.intake.urls")),
    path("api/eligibility/", include("apps.eligibility.urls")),
    path("api/forms/", include("apps.forms.urls")),
    path("api/districts/", include("apps.districts.urls")),
    path("api/audit/", include("apps.audit.urls")),
    path("api/documents/", include("apps.documents.urls", namespace="documents")),
    # SPA catch-all — must be last; serves React index.html for all non-API routes
    re_path(
        r".*", TemplateView.as_view(template_name="frontend/index.html", content_type="text/html")
    ),
]
