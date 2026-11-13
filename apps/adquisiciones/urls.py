from django.urls import path

from . import views

app_name = "adquisiciones"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("tablero/", views.tablero, name="tablero"),
    path("lista/", views.lista, name="lista"),
    path("nuevo/", views.nuevo, name="nuevo"),
    path("importar-trello/", views.importar, name="importar"),
    path("<int:pk>/", views.pedido, name="pedido"),
    path("<int:pk>/editar/", views.editar, name="editar"),
    path("<int:pk>/accion/<slug:codigo>/", views.accion, name="accion"),
    path("<int:pk>/cotizacion/", views.cotizacion, name="cotizacion"),
    path("cotizacion/<int:pk>/elegir/", views.cotizacion_elegir, name="cotizacion_elegir"),
    path("cotizacion/<int:pk>/quitar/", views.cotizacion_quitar, name="cotizacion_quitar"),
    path("archivo/<slug:clase>/<int:pk>/", views.archivo, name="archivo"),
]
