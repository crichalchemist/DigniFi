from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/token/obtain/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/users/", include("apps.users.urls")),
    path("api/intake/", include("apps.intake.urls")),
    path("api/eligibility/", include("apps.eligibility.urls")),
    path("api/forms/", include("apps.forms.urls")),
    path("api/districts/", include("apps.districts.urls")),
]
