from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AssetViewSet,
    DebtViewSet,
    FeeWaiverViewSet,
    IntakeSessionViewSet,
    SOFAReportViewSet,
)

router = DefaultRouter()
router.register(r"sessions", IntakeSessionViewSet, basename="intake-session")
router.register(r"assets", AssetViewSet, basename="asset-info")
router.register(r"debts", DebtViewSet, basename="debt-info")
router.register(r"fee-waiver", FeeWaiverViewSet, basename="fee-waiver")
router.register(r"sofa-report", SOFAReportViewSet, basename="sofa-report")

urlpatterns = [
    path("", include(router.urls)),
]
