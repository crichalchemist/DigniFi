from django.urls import path

from .views import CurrentUserView, DemoLoginView, RegisterView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="user-register"),
    path("me/", CurrentUserView.as_view(), name="user-me"),
    path("demo/", DemoLoginView.as_view(), name="user-demo-login"),
]
