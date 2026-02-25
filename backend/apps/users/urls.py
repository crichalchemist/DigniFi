from django.urls import path

from .views import RegisterView, CurrentUserView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="user-register"),
    path("me/", CurrentUserView.as_view(), name="user-me"),
]
