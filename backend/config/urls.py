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


# Top-level paths owned by the backend (URLconf routes plus STATIC_URL/MEDIA_URL).
# The SPA catch-all excludes these so an unmatched backend URL 404s — or redirects
# via APPEND_SLASH — instead of returning the React shell with a 200, which reads
# as healthy to uptime monitoring. Keep in sync with urlpatterns; a test enforces it.
BACKEND_ROUTE_PREFIXES = ("admin", "api", "health", "metrics", "static", "media")

SPA_CATCHALL_PATTERN = rf"^(?!(?:{'|'.join(BACKEND_ROUTE_PREFIXES)})(?:/|$)).*"

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
    # SPA catch-all — must be last; serves React index.html for client-side routes
    # (/intake, /forms, /documents, ...). Unknown non-backend paths still land here
    # so React renders its own 404 page.
    re_path(
        SPA_CATCHALL_PATTERN,
        TemplateView.as_view(template_name="frontend/index.html", content_type="text/html"),
    ),
]
