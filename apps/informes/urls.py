from django.urls import path

from . import views

app_name = "informes"

urlpatterns = [
    path("obra/<int:pk>/<str:fecha>/", views.informe, name="informe"),
    path("obra/<int:pk>/<str:fecha>/corregir/", views.pedir_correccion, name="pedir"),
    path("foto/<int:pk>/", views.foto, name="foto"),
    path("foto/<int:pk>/quitar/", views.foto_quitar, name="foto_quitar"),
    path("correcciones/<int:pk>/", views.resolver, name="resolver"),
    path("gremios/", views.gremios, name="gremios"),
]
