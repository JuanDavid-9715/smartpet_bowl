from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("cuenta/", include("accounts.urls")),
    path("app/", include("pets.urls")),
    path("api/v1/", include("api.urls")),
]
