from django.urls import path

from . import views

app_name = "cuentas"

urlpatterns = [
    path("", views.personal_lista, name="personal"),
    path("areas/", views.areas, name="areas"),
    path("nueva/", views.persona_form, name="persona_nueva"),
    path("<int:pk>/editar/", views.persona_form, name="persona_editar"),
    path("<int:pk>/invitar/", views.persona_invitar, name="persona_invitar"),
    path("clientes/", views.clientes_lista, name="clientes"),
    path("clientes/nuevo/", views.cliente_form, name="cliente_nuevo"),
    path("clientes/<int:pk>/", views.cliente_detalle, name="cliente"),
    path("clientes/<int:pk>/editar/", views.cliente_form, name="cliente_editar"),
    path("clientes/<int:cliente_pk>/contactos/nuevo/", views.contacto_form, name="contacto_nuevo"),
    path("clientes/<int:cliente_pk>/contactos/<int:pk>/", views.contacto_form, name="contacto_editar"),
    path("mi-perfil/", views.perfil, name="perfil"),
    path("<int:pk>/foto/", views.foto, name="foto"),
]
