"""Proyectos: usan las mismas pantallas que las obras (ficha, equipo, tareas...), con su propia lista."""

from django.urls import path

from . import views

app_name = "proyectos"

urlpatterns = [
    path("", views.lista_proyectos, name="lista"),
    path("nuevo/", views.proyecto_form, name="nuevo"),
]
