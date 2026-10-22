"""Reglas de acceso del sistema, en un solo lugar.

- Gerencia ve y administra todo.
- El resto del personal ve las obras donde está asignado y actúa según su área.
- Los clientes ven solo sus obras, los documentos compartidos y sus solicitudes.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import NoReverseMatch, reverse

from .models import Area, MiembroArea

A = Area.Codigo

# Qué áreas pueden crear cada tipo de solicitud al cliente (Gerencia puede todas).
TIPOS_SOLICITUD_POR_AREA = {
    "gasto": {A.GESTION_ADMINISTRATIVA, A.GESTION_OBRAS},
    "decision": {A.GESTION_PROYECTOS, A.DESARROLLO_PROYECTOS, A.DIRECCION_TECNICA, A.GESTION_OBRAS},
    "cambio": {A.GESTION_PROYECTOS, A.DESARROLLO_PROYECTOS, A.DIRECCION_TECNICA, A.GESTION_OBRAS},
}


# --- Identidad -------------------------------------------------------------

def _cache(usuario):
    if not hasattr(usuario, "_permisos_cache"):
        membresias = []
        if usuario.is_authenticated and usuario.es_personal:
            membresias = list(usuario.membresias.select_related("area"))
        usuario._permisos_cache = {
            "areas": {m.area.codigo for m in membresias},
            "responsable": {m.area.codigo for m in membresias if m.rol == MiembroArea.Rol.RESPONSABLE},
        }
    return usuario._permisos_cache


def olvidar_cache(usuario):
    if hasattr(usuario, "_permisos_cache"):
        del usuario._permisos_cache


def es_personal(u):
    return u.is_authenticated and u.is_active and u.es_personal


def es_cliente(u):
    return u.is_authenticated and u.is_active and u.es_cliente


def codigos_areas(u):
    return _cache(u)["areas"] if es_personal(u) else set()


def es_responsable_de(u, codigo):
    return es_personal(u) and codigo in _cache(u)["responsable"]


def es_gerencia(u):
    return es_personal(u) and (u.is_superuser or A.GERENCIA in codigos_areas(u))


def pertenece_a(u, *codigos):
    return es_gerencia(u) or bool(codigos_areas(u) & set(codigos))


# --- Personal y clientes ---------------------------------------------------

def puede_gestionar_personal(u):
    return es_gerencia(u)


def puede_gestionar_clientes(u):
    return pertenece_a(u, A.GESTION_ADMINISTRATIVA)


# --- Obras -----------------------------------------------------------------

def es_coordinador(u):
    """Coordinación: responsables de Gestión de Proyectos o de Gestión de Obras. Ven todo, como Gerencia."""
    return es_responsable_de(u, A.GESTION_PROYECTOS) or es_responsable_de(u, A.GESTION_OBRAS)


def ve_todas_las_obras(u):
    return es_gerencia(u) or es_coordinador(u) or puede_ver_montos(u)


def puede_ver_montos(u):
    """Presupuestos y certificados de obra: Gerencia y el responsable de Gestión Administrativa."""
    return es_gerencia(u) or es_responsable_de(u, A.GESTION_ADMINISTRATIVA)


def puede_importar_certificado(u, obra):
    return puede_editar_obra(u, obra) or puede_ver_montos(u)


def obras_visibles(u):
    """Lo que se puede abrir: todo el personal ve todos los proyectos; las obras, solo su equipo
    (Gerencia y Coordinación ven todo)."""
    from apps.obras.models import Obra

    if ve_todas_las_obras(u):
        return Obra.objects.all()
    if es_cliente(u):
        return Obra.objects.filter(cliente_id=u.cliente_id) if u.cliente_id else Obra.objects.none()
    if es_personal(u):
        return Obra.objects.filter(Q(tipo=Obra.Tipo.PROYECTO) | Q(asignaciones__usuario=u)).distinct()
    return Obra.objects.none()


def obras_del_equipo(u):
    """Donde la persona trabaja: las asignadas (Gerencia y Coordinación, todas). Define los archivos que ve
    y lo que aparece en su Dashboard."""
    from apps.obras.models import Obra

    if ve_todas_las_obras(u):
        return Obra.objects.all()
    if es_personal(u):
        return Obra.objects.filter(asignaciones__usuario=u).distinct()
    return obras_visibles(u)


def ids_asignadas(u):
    """Proyectos y obras donde la persona está en el equipo (para marcarlos en los listados)."""
    if not es_personal(u):
        return set()
    return set(u.asignaciones.values_list("obra_id", flat=True))


def puede_ver_obra(u, obra):
    return obras_visibles(u).filter(pk=obra.pk).exists()


def esta_asignado(u, obra):
    return es_personal(u) and obra.asignaciones.filter(usuario=u).exists()


def trabaja_en(u, obra):
    return es_coordinador(u) or esta_asignado(u, obra)


def puede_crear_obra(u):
    return es_gerencia(u)


def puede_editar_obra(u, obra):
    return es_gerencia(u) or (es_personal(u) and obra.asignaciones.filter(usuario=u, es_responsable=True).exists())


# --- Time Report -------------------------------------------------------------

def puede_habilitar_horas(u):
    """Habilita la carga tardía de horas y ve los reportes: Gerencia y el coordinador de proyectos."""
    return es_gerencia(u) or es_responsable_de(u, A.GESTION_PROYECTOS)


# --- Plantillas de tareas ---------------------------------------------------

def puede_gestionar_plantillas(u):
    return pertenece_a(u, A.GESTION_PROYECTOS, A.GESTION_OBRAS)


# --- Documentos ------------------------------------------------------------

def documentos_visibles(u):
    """Documentos que el usuario puede ver (sin los de la papelera).

    - Equipo de la obra: las personas asignadas a la obra (y Gerencia).
    - Restringido: Gerencia y los integrantes del área responsable del documento.
    - Compartido con el cliente: lo anterior + el cliente de la obra.
    Los documentos sin obra son la Biblioteca general: los ve todo el personal (salvo los restringidos).
    """
    from apps.documentos.models import Documento

    A = Documento.Acceso
    qs = Documento.objects.filter(en_papelera=False)
    if es_gerencia(u):
        return qs
    if es_cliente(u):
        return qs.filter(obra__in=obras_visibles(u), acceso=A.CLIENTE, archivado=False)
    if es_personal(u):
        abiertos = Q(acceso__in=[A.EQUIPO, A.CLIENTE]) & (Q(obra__isnull=True) | Q(obra__in=obras_del_equipo(u)))
        restringidos = Q(acceso=A.RESTRINGIDO, area__codigo__in=codigos_areas(u))
        return qs.filter(abiertos | restringidos)
    return qs.none()


def puede_subir_documentos(u, obra=None):
    if not es_personal(u):
        return False
    return obra is None or es_gerencia(u) or trabaja_en(u, obra)


def es_responsable_de_obra(u, obra):
    return es_personal(u) and obra.asignaciones.filter(usuario=u, es_responsable=True).exists()


def puede_administrar_documento(u, doc):
    """Subir versiones, editar datos, archivar y mandar a la papelera:
    quien lo subió, el área responsable y los responsables de la obra (y Gerencia)."""
    if not es_personal(u):
        return False
    if es_gerencia(u):
        return True
    if not puede_ver_documento(u, doc, incluir_papelera=True):
        return False
    if doc.creado_por_id == u.pk:
        return True
    if doc.obra_id and es_responsable_de_obra(u, doc.obra):
        return True
    if doc.area_id:
        codigo = doc.area.codigo
        if es_responsable_de(u, codigo):
            return True
        if codigo in codigos_areas(u):
            return doc.obra_id is None or esta_asignado(u, doc.obra)
    return False


def puede_ver_documento(u, doc, incluir_papelera=False):
    if doc.en_papelera and not incluir_papelera:
        return puede_administrar_documento(u, doc)
    from apps.documentos.models import Documento

    if es_gerencia(u):
        return True
    if es_cliente(u):
        return (not doc.en_papelera and not doc.archivado and doc.acceso == Documento.Acceso.CLIENTE
                and doc.obra_id is not None and u.cliente_id is not None and doc.obra.cliente_id == u.cliente_id)
    if not es_personal(u):
        return False
    if doc.acceso == Documento.Acceso.RESTRINGIDO:
        return bool(doc.area_id and doc.area.codigo in codigos_areas(u))
    return doc.obra_id is None or trabaja_en(u, doc.obra)


def puede_compartir_con_cliente(u, doc):
    return bool(doc.obra_id) and (es_gerencia(u) or es_responsable_de_obra(u, doc.obra))


def puede_aprobar_planos(u):
    return pertenece_a(u, A.DIRECCION_TECNICA)


def puede_eliminar_definitivo(u):
    return es_gerencia(u)


# --- Solicitudes de aprobación --------------------------------------------

def tipos_solicitud_permitidos(u, obra=None):
    if not es_personal(u):
        return []
    if es_gerencia(u):
        return list(TIPOS_SOLICITUD_POR_AREA)
    if obra is not None and not esta_asignado(u, obra):
        return []
    areas = codigos_areas(u)
    return [tipo for tipo, permitidas in TIPOS_SOLICITUD_POR_AREA.items() if permitidas & areas]


def solicitudes_visibles(u):
    from apps.aprobaciones.models import Solicitud

    E = Solicitud.Estado
    if es_gerencia(u):
        return Solicitud.objects.all()
    if es_personal(u):
        return Solicitud.objects.filter(obra__in=obras_del_equipo(u))
    if es_cliente(u):
        return Solicitud.objects.filter(obra__in=obras_visibles(u)).filter(
            Q(estado__in=Solicitud.ESTADOS_VISIBLES_CLIENTE) | Q(estado=E.CANCELADA, enviada_en__isnull=False)
        )
    return Solicitud.objects.none()


def puede_editar_solicitud(u, s):
    return (
        es_personal(u)
        and s.estado in (s.Estado.BORRADOR, s.Estado.OBSERVADA)
        and (s.creada_por_id == u.pk or es_gerencia(u))
    )


def puede_revisar_solicitudes(u):
    return pertenece_a(u, A.DIRECCION_TECNICA)


def puede_responder_solicitud(u, s):
    return (
        es_cliente(u)
        and u.cliente_id is not None
        and u.cliente_id == s.obra.cliente_id
        and s.estado in (s.Estado.ENVIADA, s.Estado.VENCIDA)
    )


# --- Registro de actividad -------------------------------------------------

def puede_ver_auditoria_global(u):
    return es_gerencia(u)


# --- Decoradores para vistas -----------------------------------------------

def exigir(condicion):
    if not condicion:
        raise PermissionDenied


def inicio_cliente():
    """Destino del cliente al entrar: el portal, o su perfil mientras el portal no esté activo."""
    try:
        return reverse("portal:inicio")
    except NoReverseMatch:
        return reverse("cuentas:perfil")


def solo_personal(vista):
    @login_required
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if es_cliente(request.user):
            return redirect(inicio_cliente())
        exigir(es_personal(request.user))
        return vista(request, *args, **kwargs)

    return envoltura


def solo_gerencia(vista):
    @solo_personal
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        exigir(es_gerencia(request.user))
        return vista(request, *args, **kwargs)

    return envoltura


def solo_cliente(vista):
    @login_required
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if es_personal(request.user):
            return redirect("core:tablero")
        exigir(es_cliente(request.user))
        return vista(request, *args, **kwargs)

    return envoltura
