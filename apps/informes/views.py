from datetime import date, timedelta

from django.contrib import messages
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.auditoria.services import registrar
from apps.cuentas import permisos
from apps.horas.reglas import fin_del_dia, hoy
from apps.obras import avances
from apps.obras.models import AvanceTarea, Obra
from apps.plantillas import arbol

from . import reglas
from .forms import GremioForm, InformeForm, PedidoCorreccionForm
from .models import FotoInforme, Gremio, HabilitacionInforme, InformeDiario, PersonalGremio


def _obra(request, pk):
    obra = get_object_or_404(Obra, pk=pk, tipo=Obra.Tipo.OBRA, eliminada=False)
    permisos.exigir(permisos.puede_ver_informes(request.user, obra))
    request.menu_activo = "obras:lista"
    return obra


def _fecha(texto):
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise Http404


def url_informe(obra, fecha):
    return reverse("informes:informe", args=[obra.pk, fecha.isoformat()])


def _filas_avance(obra):
    """Las tareas de la obra en orden, con su nivel, para mover las barras desde el informe."""
    filas = []

    def recorrer(nodos, nivel):
        for n in nodos:
            filas.append({"nodo": n, "nivel": nivel, "hoja": not n.hijos_lista})
            recorrer(n.hijos_lista, nivel + 1)

    recorrer(arbol.anotar(obra.tareas.all()), 0)
    return filas


def _guardar_avances(request, obra):
    """Las barras del informe (solo el día de hoy) se guardan igual que en la pestaña Tareas y quedan en el
    historial de avance."""
    cambios = []
    for tarea in obra.tareas.filter(hijos__isnull=True):
        valor = request.POST.get(f"avance-{tarea.pk}")
        if valor is None:
            continue
        try:
            nuevo = max(0, min(100, int(valor)))
        except ValueError:
            continue
        if nuevo != tarea.avance:
            anterior, tarea.avance = tarea.avance, nuevo
            tarea.save(update_fields=["avance", "actualizada"])
            avances.registrar(tarea, anterior, nuevo, usuario=request.user)
            cambios.append(f"{tarea.nombre} {anterior}% → {nuevo}%")
    if cambios:
        obra.recalcular_avance()
    return cambios


@permisos.solo_personal
def informe(request, pk, fecha):
    obra = _obra(request, pk)
    dia = _fecha(fecha)
    inf = InformeDiario.objects.filter(obra=obra, fecha=dia).prefetch_related("personal__gremio", "fotos").first()
    puede_cargar = permisos.puede_cargar_informe(request.user, obra)
    abierto = puede_cargar and reglas.abierto(obra, dia)
    es_hoy = dia == hoy()

    form = None
    if abierto:
        instancia = inf or InformeDiario(obra=obra, fecha=dia)
        form = InformeForm(request.POST or None, request.FILES or None, instance=instancia,
                           fotos_actuales=inf.fotos.count() if inf else 0)
        if request.method == "POST" and form.is_valid():
            es_alta = inf is None
            with transaction.atomic():
                inf = form.save(commit=False)
                inf.se_trabajo = form.cleaned_data["se_trabajo"]
                inf.motivo_sin_trabajo = form.cleaned_data["motivo_sin_trabajo"]
                if es_alta:
                    inf.autor = request.user
                inf.save()
                inf.personal.all().delete()
                PersonalGremio.objects.bulk_create(
                    [PersonalGremio(informe=inf, gremio=g, cantidad=c) for g, c in form.personal().items()])
                for archivo in form.cleaned_data["fotos_nuevas"]:
                    FotoInforme.objects.create(informe=inf, archivo=archivo)
                for archivo in form.cleaned_data["fotos_libro"]:
                    FotoInforme.objects.create(informe=inf, archivo=archivo, del_libro=True,
                                               detalle="Hoja del libro de obra")
                for foto in inf.fotos.all():
                    if f"foto-{foto.pk}-detalle" in request.POST:
                        foto.detalle = request.POST[f"foto-{foto.pk}-detalle"].strip()[:200]
                        tarea_id = request.POST.get(f"foto-{foto.pk}-tarea") or None
                        foto.tarea = obra.tareas.filter(pk=tarea_id).first() if tarea_id else None
                        foto.save(update_fields=["detalle", "tarea"])
                cambios = _guardar_avances(request, obra) if es_hoy else []
            registrar("informe.alta" if es_alta else "informe.edicion",
                      f"{'Informe diario' if es_alta else 'Corrección del informe'} del {dia:%d/%m/%Y}"
                      + (f" · avance: {'; '.join(cambios)}" if cambios else ""), objeto=inf)
            messages.success(request, f"Informe del {dia:%d/%m} guardado.")
            return redirect(url_informe(obra, dia))

    contexto = {
        "obra": obra, "dia": dia, "informe": inf, "form": form, "es_hoy": es_hoy, "puede_cargar": puede_cargar,
        "abierto": abierto,
        "avances_del_dia": AvanceTarea.objects.filter(obra=obra, fecha=dia).select_related("tarea", "usuario")
        .order_by("tarea__orden", "id"),
        "anterior": InformeDiario.objects.filter(obra=obra, fecha__lt=dia).order_by("-fecha").first(),
        "siguiente": InformeDiario.objects.filter(obra=obra, fecha__gt=dia).order_by("fecha").first(),
    }
    if form is not None:
        filas = _filas_avance(obra)
        contexto["tareas_foto"] = [f["nodo"] for f in filas if f["hoja"]]
        if es_hoy:
            contexto["filas_avance"] = filas
    elif puede_cargar and dia < hoy():
        contexto["pedido"] = HabilitacionInforme.objects.filter(obra=obra, fecha=dia).first()
        contexto["form_pedido"] = PedidoCorreccionForm()
    return render(request, "informes/informe.html", contexto)


@permisos.solo_personal
def foto(request, pk):
    f = get_object_or_404(FotoInforme.objects.select_related("informe__obra"), pk=pk)
    permisos.exigir(permisos.puede_ver_informes(request.user, f.informe.obra))
    respuesta = FileResponse(f.archivo.open("rb"), content_type="image/jpeg")
    respuesta["Cache-Control"] = "private, max-age=86400"
    return respuesta


@permisos.solo_personal
@require_POST
def foto_quitar(request, pk):
    f = get_object_or_404(FotoInforme.objects.select_related("informe__obra"), pk=pk)
    inf = f.informe
    permisos.exigir(permisos.puede_cargar_informe(request.user, inf.obra) and reglas.abierto(inf.obra, inf.fecha))
    f.archivo.delete(save=False)
    f.delete()
    registrar("informe.foto_baja", f"Se quitó una foto del informe del {inf.fecha:%d/%m/%Y}", objeto=inf)
    return redirect(url_informe(inf.obra, inf.fecha))


@permisos.solo_personal
@require_POST
def pedir_correccion(request, pk, fecha):
    obra = _obra(request, pk)
    dia = _fecha(fecha)
    permisos.exigir(permisos.puede_cargar_informe(request.user, obra) and dia < hoy())
    form = PedidoCorreccionForm(request.POST)
    if form.is_valid():
        HabilitacionInforme.objects.filter(obra=obra, fecha=dia, estado=HabilitacionInforme.Estado.PENDIENTE).delete()
        pedido = form.save(commit=False)
        pedido.obra, pedido.fecha, pedido.usuario = obra, dia, request.user
        pedido.save()
        registrar("informe.pedido", f"Pidió cargar o corregir el informe del {dia:%d/%m/%Y}: {pedido.motivo}",
                  objeto=obra)
        messages.success(request, "Pedido enviado. DIR lo va a ver en su Dashboard.")
    else:
        messages.error(request, "Escribí el motivo.")
    return redirect(url_informe(obra, dia))


@permisos.solo_personal
@require_POST
def resolver(request, pk):
    permisos.exigir(permisos.puede_autorizar_correccion_informe(request.user))
    pedido = get_object_or_404(HabilitacionInforme, pk=pk, estado=HabilitacionInforme.Estado.PENDIENTE)
    aprobar = request.POST.get("accion") == "aprobar"
    pedido.estado = HabilitacionInforme.Estado.APROBADA if aprobar else HabilitacionInforme.Estado.RECHAZADA
    pedido.resuelta_por, pedido.resuelta = request.user, timezone.now()
    pedido.valida_hasta = fin_del_dia() if aprobar else None
    pedido.save()
    registrar("informe.habilitacion", f"{'Autorizó' if aprobar else 'Rechazó'} corregir el informe del "
              f"{pedido.fecha:%d/%m/%Y} ({pedido.usuario.nombre_completo})", objeto=pedido.obra)
    messages.success(request, f"{pedido.obra.nombre}, {pedido.fecha:%d/%m}: "
                              f"{'se puede corregir hasta hoy a las 23:59' if aprobar else 'pedido rechazado'}.")
    return redirect(request.POST.get("volver") or "core:tablero")


@permisos.solo_personal
def gremios(request):
    permisos.exigir(permisos.puede_editar_gremios(request.user))
    form = GremioForm(request.POST or None)
    if request.method == "POST":
        if "cambiar" in request.POST:
            g = get_object_or_404(Gremio, pk=request.POST["cambiar"])
            g.activo = not g.activo
            g.save(update_fields=["activo"])
            registrar("informe.gremio", f"Gremio {'activado' if g.activo else 'desactivado'}: {g}")
            return redirect("informes:gremios")
        if form.is_valid():
            g = form.save(commit=False)
            g.orden = (Gremio.objects.order_by("-orden").values_list("orden", flat=True).first() or 0) + 1
            g.save()
            registrar("informe.gremio", f"Nuevo gremio: {g}")
            messages.success(request, f"Se agregó «{g}».")
            return redirect("informes:gremios")
    return render(request, "informes/gremios.html", {"gremios": Gremio.objects.all(), "form": form,
                                                     "volver": request.GET.get("volver", "")})


# --- Para la ficha de la obra y el Dashboard -------------------------------------------------------------------

def contexto_pestana_obra(request, obra):
    informes = list(obra.informes.prefetch_related("personal", "fotos").select_related("autor"))
    desde = hoy() - timedelta(days=30)
    con_informe = {i.fecha for i in informes}
    faltan = [desde + timedelta(days=d) for d in range(31)
              if (desde + timedelta(days=d)) not in con_informe and reglas.es_dia_habil(desde + timedelta(days=d))
              and (desde + timedelta(days=d)) <= hoy()]
    if informes:
        primero = min(con_informe)
        faltan = [d for d in faltan if d >= primero]
    return {
        "informes": informes,
        "informes_resumen": {
            "total": len(informes),
            "trabajados": sum(1 for i in informes if i.se_trabajo),
            "lluvia": sum(1 for i in informes if i.clima == InformeDiario.Clima.LLUVIA),
            "perdidos": sum(1 for i in informes if not i.se_trabajo),
            "personal_prom": round(sum(i.personas for i in informes) / len(informes), 1) if informes else 0,
        },
        "informes_faltan": faltan,
        "puede_cargar_informe": permisos.puede_cargar_informe(request.user, obra),
        "hoy_tiene_informe": hoy() in con_informe,
        "url_informe_hoy": url_informe(obra, hoy()),
    }


def contexto_tablero(usuario):
    """Dashboard: el DT ve el informe de hoy de sus obras; DIR y Coordinación de Obras, qué obras no lo tienen."""
    from apps.cuentas.models import Area

    dia = hoy()
    contexto = {}
    mias = (Obra.objects.filter(tipo=Obra.Tipo.OBRA, estado=Obra.Estado.ACTIVA, eliminada=False,
                                asignaciones__usuario=usuario,
                                asignaciones__area__codigo=Area.Codigo.DIRECCION_TECNICA).distinct().order_by("nombre"))
    hechos = set(InformeDiario.objects.filter(fecha=dia).values_list("obra_id", flat=True))
    if mias:
        contexto["informes_mios"] = [{"obra": o, "hecho": o.pk in hechos, "url": url_informe(o, dia)} for o in mias]
    if permisos.ve_informes_de_todas(usuario) and reglas.es_dia_habil(dia):
        activas = Obra.objects.filter(tipo=Obra.Tipo.OBRA, estado=Obra.Estado.ACTIVA, eliminada=False).order_by("nombre")
        contexto["informes_hoy"] = [{"obra": o, "hecho": o.pk in hechos, "url": url_informe(o, dia)} for o in activas]
    if permisos.puede_autorizar_correccion_informe(usuario):
        contexto["pedidos_informe"] = HabilitacionInforme.objects.filter(
            estado=HabilitacionInforme.Estado.PENDIENTE).select_related("obra", "usuario")
    return contexto
