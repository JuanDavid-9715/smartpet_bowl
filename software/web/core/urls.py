from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("producto/", views.product, name="product"),
    path("planes/", views.plans, name="plans"),
    path("codigo-abierto/", views.open_source, name="open_source"),
    path("pago/", views.checkout, name="checkout"),
    path("pago/confirmado/", views.checkout_done, name="checkout_done"),
]
