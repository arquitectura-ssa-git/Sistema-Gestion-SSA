from django.urls import path

from . import views

app_name = "plantillas"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("nueva/", views.plantilla_form, name="nueva"),
    path("<int:pk>/", views.detalle, name="detalle"),
    path("<int:pk>/editar/", views.plantilla_form, name="editar"),
    path("<int:pk>/duplicar/", views.duplicar, name="duplicar"),
    path("<int:pk>/borrar/", views.borrar, name="borrar"),
]
