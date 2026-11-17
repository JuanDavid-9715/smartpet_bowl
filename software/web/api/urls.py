from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("ingest/", views.ingest, name="ingest"),
    path("health/", views.health, name="health"),
]
