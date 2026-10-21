from django.contrib import admin
from django.templatetags.static import static
from django.urls import include, path
from django.views.generic import RedirectView


class IconoRedirect(RedirectView):
    """La dirección se calcula al pedirla (con nombre por versión cuando está publicado)."""

    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        return static("favicon.ico")


admin.site.site_header = "Administración técnica"
admin.site.site_title = "Administración técnica"

urlpatterns = [
    path("admin/", admin.site.urls),
    # Los navegadores piden /favicon.ico por su cuenta, aunque la página indique otro.
    path("favicon.ico", IconoRedirect.as_view(), name="favicon"),
    path("cuenta/", include("django.contrib.auth.urls")),
    path("", include("apps.core.urls")),
    path("personal/", include("apps.cuentas.urls")),
    # Se activan a medida que se construye cada sección:
    path("proyectos/", include("apps.obras.urls_proyectos")),
    path("obras/", include("apps.obras.urls")),
    path("plantillas/", include("apps.plantillas.urls")),
    path("horas/", include("apps.horas.urls")),
    path("documentos/", include("apps.documentos.urls")),
    # path("solicitudes/", include("apps.aprobaciones.urls")),
    # path("notificaciones/", include("apps.notificaciones.urls")),
    # path("comunicados/", include("apps.comunicados.urls")),
    # path("actividad/", include("apps.auditoria.urls")),
    # path("portal/", include("apps.portal.urls")),
]
