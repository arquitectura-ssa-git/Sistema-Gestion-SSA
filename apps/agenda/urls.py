from django.urls import path

from . import views

app_name = "agenda"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("nuevo/", views.contacto_form, name="nuevo"),
    path("<int:pk>/editar/", views.contacto_form, name="editar"),
    path("<int:pk>/eliminar/", views.eliminar, name="eliminar"),
    path("tipos/", views.tipos, name="tipos"),
]
