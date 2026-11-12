from django.urls import path

from . import views

app_name = "legajos"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("<int:pk>/", views.detalle, name="detalle"),
    path("documento/<int:pk>/", views.archivo, name="archivo"),
    path("documento/<int:pk>/quitar/", views.quitar, name="quitar"),
]
