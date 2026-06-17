from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import FormSchemaUIView, GeneratedFormViewSet

router = DefaultRouter()
router.register("", GeneratedFormViewSet, basename="generated-forms")

urlpatterns = [
    path(
        "schema/<str:form_type>/ui-spec/",
        FormSchemaUIView.as_view(),
        name="form-schema-ui-spec",
    ),
] + router.urls
