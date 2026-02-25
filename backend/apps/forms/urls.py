from rest_framework.routers import DefaultRouter

from .views import GeneratedFormViewSet

router = DefaultRouter()
router.register("", GeneratedFormViewSet, basename="generated-forms")

urlpatterns = router.urls
