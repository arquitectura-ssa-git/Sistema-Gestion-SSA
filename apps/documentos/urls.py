from django.urls import path

from . import views

app_name = "documentos"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("subir/", views.subir, name="subir"),
    path("enlace/", views.agregar_enlace, name="agregar_enlace"),
    path("papelera/", views.papelera, name="papelera"),
    path("<int:pk>/", views.detalle, name="detalle"),
    path("<int:pk>/editar/", views.editar, name="editar"),
    path("<int:pk>/version/", views.nueva_version, name="nueva_version"),
    path("<int:pk>/compartir/", views.compartir, name="compartir"),
    path("<int:pk>/plano/revision/", views.plano_revision, name="plano_revision"),
    path("<int:pk>/plano/aprobar/", views.plano_aprobar, name="plano_aprobar"),
    path("<int:pk>/plano/observar/", views.plano_observar, name="plano_observar"),
    path("<int:pk>/archivar/", views.archivar, name="archivar"),
    path("<int:pk>/papelera/", views.a_papelera, name="a_papelera"),
    path("<int:pk>/restaurar/", views.restaurar, name="restaurar"),
    path("<int:pk>/eliminar/", views.eliminar, name="eliminar"),
    path("archivo/<int:version_pk>/ver/", views.ver, name="ver"),
    path("archivo/<int:version_pk>/descargar/", views.descargar, name="descargar"),
    path("archivo/<int:version_pk>/editable/", views.descargar_editable, name="descargar_editable"),
    path("archivo/<int:version_pk>/miniatura/", views.miniatura, name="miniatura"),
]
