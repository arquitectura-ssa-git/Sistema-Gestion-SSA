from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.cuentas import permisos
from apps.obras.models import Obra


@login_required
def inicio(request):
    if permisos.es_cliente(request.user):
        return redirect(permisos.inicio_cliente())
    return redirect("core:tablero")


@permisos.solo_personal
def tablero(request):
    u = request.user
    activas = permisos.obras_visibles(u).filter(estado=Obra.Estado.ACTIVA).select_related("cliente")
    T = Obra.Tipo
    contexto = {
        "secciones": [
            {"tipo": tipo, "titulo": titulo, "icono": icono, "url": url,
             "items": activas.filter(tipo=tipo)[:8], "total": activas.filter(tipo=tipo).count()}
            for tipo, titulo, icono, url in [(T.PROYECTO, "Proyectos activos", "pencil-square", "proyectos:lista"),
                                             (T.OBRA, "Obras activas", "buildings", "obras:lista")]
        ],
        "mis_areas": u.membresias.select_related("area"),
    }
    if apps.is_installed("apps.horas"):
        from django.db.models import Sum

        from apps.horas import reglas
        from apps.horas.models import Habilitacion, RegistroHoras

        contexto["horas_hoy"] = RegistroHoras.objects.filter(usuario=u, fecha=reglas.hoy()).aggregate(
            t=Sum("horas"))["t"] or 0
        contexto["jornada_hoy"] = reglas.horas_contratadas(u, reglas.hoy())
        if permisos.puede_habilitar_horas(u):
            contexto["pedidos_horas"] = Habilitacion.objects.filter(
                estado=Habilitacion.Estado.PENDIENTE).select_related("usuario").order_by("pedida")[:6]
    if apps.is_installed("apps.aprobaciones"):
        from apps.aprobaciones.models import Solicitud

        E = Solicitud.Estado
        visibles = permisos.solicitudes_visibles(u).select_related("obra")
        contexto["esperando_cliente"] = visibles.filter(estado__in=[E.ENVIADA, E.VENCIDA]).order_by("fecha_limite")[:8]
        contexto["mis_borradores"] = visibles.filter(creada_por=u, estado__in=[E.BORRADOR, E.OBSERVADA])[:8]
        if permisos.puede_revisar_solicitudes(u):
            contexto["para_revisar"] = visibles.filter(estado=E.EN_REVISION)[:8]
        contexto["respondidas"] = visibles.filter(
            creada_por=u, estado__in=[E.APROBADA, E.RECHAZADA, E.OBSERVADA]
        ).order_by("-respondida_en")[:5]
    if apps.is_installed("apps.documentos"):
        from datetime import date, timedelta

        visibles = permisos.documentos_visibles(u).filter(archivado=False)
        contexto["ultimos_documentos"] = visibles.select_related("obra").order_by("-actualizado")[:6]
        contexto["permisos_por_vencer"] = visibles.filter(
            tipo="permisos", vencimiento__isnull=False, vencimiento__lte=date.today() + timedelta(days=60),
        ).select_related("obra").order_by("vencimiento")[:6]
        contexto["hoy"] = date.today()
        if permisos.puede_aprobar_planos(u):
            contexto["planos_a_revisar"] = visibles.filter(tipo="planos", estado_plano="revision").select_related(
                "obra")[:6]
    if apps.is_installed("apps.comunicados"):
        contexto["comunicados_sin_leer"] = u.comunicados_recibidos.filter(leido_en__isnull=True).select_related(
            "comunicado__autor")[:5]
    return render(request, "core/tablero.html", contexto)
