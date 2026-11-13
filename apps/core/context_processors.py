from django.apps import apps
from django.conf import settings

from apps.cuentas import permisos

from .menu import construir_menu


def globales(request):
    contexto = {"NOMBRE_ESTUDIO": settings.NOMBRE_ESTUDIO}
    usuario = getattr(request, "user", None)
    if usuario is None or not usuario.is_authenticated:
        return contexto

    perm = {
        "gerencia": permisos.es_gerencia(usuario),
        "personal": permisos.es_personal(usuario),
        "cliente": permisos.es_cliente(usuario),
        "clientes": permisos.puede_gestionar_clientes(usuario),
        "agenda": permisos.puede_gestionar_agenda(usuario),
        "crear_obras": permisos.puede_crear_obra(usuario),
        "auditoria": permisos.puede_ver_auditoria_global(usuario),
        "compras": permisos.puede_gestionar_compras(usuario),
    }
    contexto["perm"] = perm
    contexto["menu"] = construir_menu(request, perm)
    if apps.is_installed("apps.notificaciones"):
        contexto["mostrar_campana"] = True
        contexto["notif_no_leidas"] = usuario.notificaciones.filter(leida=False).count()
    return contexto
