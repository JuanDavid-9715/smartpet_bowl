from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("ingresar/", views.SignInView.as_view(), name="login"),
    path("salir/", LogoutView.as_view(), name="logout"),
    path("registro/", views.register, name="register"),
]
