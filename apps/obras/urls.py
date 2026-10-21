from django.urls import path

from . import views

app_name = "obras"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("nueva/", views.obra_form, name="nueva"),
    path("<int:pk>/", views.detalle, name="detalle"),
    path("<int:pk>/editar/", views.obra_form, name="editar"),
    path("<int:pk>/duplicar/", views.duplicar, name="duplicar"),
    path("<int:pk>/tareas/a-plantilla/", views.tareas_a_plantilla, name="tareas_a_plantilla"),
    path("<int:pk>/equipo/agregar/", views.equipo_agregar, name="equipo_agregar"),
    path("<int:pk>/equipo/<int:asignacion_pk>/quitar/", views.equipo_quitar, name="equipo_quitar"),
    path("<int:pk>/equipo/<int:asignacion_pk>/responsable/", views.equipo_responsable, name="equipo_responsable"),
    path("<int:pk>/tareas/", views.tareas_guardar, name="tareas_guardar"),
    path("<int:pk>/tareas/plantilla/", views.tareas_aplicar_plantilla, name="tareas_plantilla"),
    path("<int:pk>/tareas/<int:tarea_pk>/avance/", views.tarea_avance, name="tarea_avance"),
    path("<int:pk>/hitos/agregar/", views.hito_agregar, name="hito_agregar"),
    path("<int:pk>/hitos/<int:hito_pk>/alternar/", views.hito_alternar, name="hito_alternar"),
    path("<int:pk>/hitos/<int:hito_pk>/borrar/", views.hito_borrar, name="hito_borrar"),
]
