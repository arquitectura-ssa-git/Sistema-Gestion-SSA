from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("tablero/", views.tablero, name="tablero"),
    path("ayuda/", views.ayuda, name="ayuda"),
]
