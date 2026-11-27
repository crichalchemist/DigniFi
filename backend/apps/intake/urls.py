from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AssetViewSet,
    DebtViewSet,
    IntakeSessionViewSet,
)

router = DefaultRouter()
router.register(r"sessions", IntakeSessionViewSet, basename="intake-session")
router.register(r"assets", AssetViewSet, basename="asset-info")
router.register(r"debts", DebtViewSet, basename="debt-info")

urlpatterns = [
    path("", include(router.urls)),
]
