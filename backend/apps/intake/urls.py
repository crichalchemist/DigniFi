from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import IntakeSessionViewSet, AssetViewSet, DebtViewSet

router = DefaultRouter()
router.register(r"sessions", IntakeSessionViewSet, basename="intake-session")
router.register(r"assets", AssetViewSet, basename="asset-info")
router.register(r"debts", DebtViewSet, basename="debt-info")

urlpatterns = [
    path("", include(router.urls)),
]
