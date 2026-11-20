from django.urls import path

from . import views

app_name = "pets"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("mascotas/", views.pet_list, name="list"),
    path("mascotas/nueva/", views.pet_create, name="create"),
    path("mascotas/<int:pk>/", views.pet_detail, name="detail"),
    path("mascotas/<int:pk>/editar/", views.pet_edit, name="edit"),
    path("mascotas/<int:pk>/fotos/", views.pet_photos, name="photos"),
    path("mascotas/<int:pk>/racion/", views.pet_ration, name="ration"),
    path("comederos/nuevo/", views.feeder_add, name="feeder_add"),
    path("comederos/<int:pk>/eliminar/", views.feeder_delete, name="feeder_delete"),
    path("comederos/<int:pk>/ordenar/", views.feeder_command, name="feeder_command"),
    path("mascotas/<int:pk>/archivar/", views.pet_archive, name="archive"),
    path("mascotas/<int:pk>/restaurar/", views.pet_restore, name="restore"),
    path("mascotas/<int:pk>/plato/quitar/", views.pet_unassign_feeder, name="unassign_feeder"),
    path("eventos/", views.events, name="events"),
    path("en-vivo/", views.live, name="live"),
    path("en-vivo/estado/", views.live_state, name="live_state"),
    path("en-vivo/video/", views.live_video, name="live_video"),
    path("historial/", views.history, name="history"),
    path("alertas/", views.alerts, name="alerts"),
    path("ajustes/", views.settings_view, name="settings"),
]
