from django.urls import path

from .views import DocumentViewSet

doc_list = DocumentViewSet.as_view({"get": "list"})
doc_detail = DocumentViewSet.as_view({"get": "retrieve"})
doc_upload = DocumentViewSet.as_view({"post": "upload"})
doc_validate = DocumentViewSet.as_view({"post": "validate"})

app_name = "documents"
urlpatterns = [
    path("", doc_list, name="list"),
    path("upload/", doc_upload, name="upload"),
    path("<int:pk>/", doc_detail, name="detail"),
    path("<int:pk>/validate/", doc_validate, name="validate"),
]
