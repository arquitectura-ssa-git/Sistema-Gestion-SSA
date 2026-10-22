import json
from datetime import date, timedelta
from decimal import Decimal

from django.apps import apps
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.auditoria.services import registrar
from apps.core.utils import cambios_de_formulario as _cambios
from apps.cuentas import permisos

from apps.plantillas import arbol
from apps.plantillas.forms import AplicarPlantillaForm, leer_estructura
from apps.plantillas.models import Plantilla, TareaPlantilla

from . import avances, certificados
from .forms import AsignacionForm, DuplicarObraForm, GuardarPlantillaForm, HitoForm, ImportarCertificadoForm, ObraForm
from .models import AsignacionObra, Certificado, Hito, Obra, TareaObra

PESTANAS = [
    ("resumen", "Resumen", "info-circle"),
    ("equipo", "Equipo", "people"),
    ("tareas", "Tareas", "list-check"),
    ("historial", "Historial de avance", "graph-up-arrow"),
    ("certificados", "Certificados", "receipt"),
    ("hitos", "Hitos", "flag"),
    ("archivos", "Archivos", "folder2-open"),
    ("solicitudes", "Solicitudes", "check2-square"),
    ("horas", "Horas", "clock"),
    ("actividad", "Actividad", "journal-text"),
]
# Pestañas que dependen de secciones que todavía pueden no estar activas.
PESTANA_APP = {"archivos": "apps.documentos", "solicitudes": "apps.aprobaciones", "horas": "apps.horas"}


def _marcar_menu(request, tipo):
    """Los proyectos comparten las pantallas de obras; esto ilumina la sección correcta del menú."""
    request.menu_activo = "proyectos:lista" if tipo == Obra.Tipo.PROYECTO else "obras:lista"


def _obra_visible(request, pk):
    obra = get_object_or_404(Obra.objects.select_related("cliente"), pk=pk)
    permisos.exigir(permisos.puede_ver_obra(request.user, obra))
    _marcar_menu(request, obra.tipo)
    return obra


def _exigir_edicion(request, obra):
    permisos.exigir(permisos.puede_editar_obra(request.user, obra))


@permisos.solo_personal
def lista(request, tipo=Obra.Tipo.OBRA):
    estado = request.GET.get("estado", Obra.Estado.ACTIVA)
    etapa = request.GET.get("etapa", "")
    q = request.GET.get("q", "").strip()
    obras = (permisos.obras_visibles(request.user).filter(tipo=tipo).select_related("cliente")
             .annotate(personas=Count("asignaciones__usuario", distinct=True)))
    if estado:
        obras = obras.filter(estado=estado)
    if etapa:
        obras = obras.filter(etapa=etapa)
    if q:
        obras = obras.filter(Q(nombre__icontains=q) | Q(codigo__icontains=q) | Q(cliente__nombre__icontains=q)
                             | Q(localidad__icontains=q))
    # Primero los que tienen a la persona en el equipo, después el resto; cada grupo por nombre.
    mias = AsignacionObra.objects.filter(obra=OuterRef("pk"), usuario=request.user)
    obras = obras.annotate(es_mia=Exists(mias)).order_by("-es_mia", "nombre")
    return render(request, "obras/lista.html", {
        "obras": obras,
        "asignadas": permisos.ids_asignadas(request.user),
        "estado": estado, "etapa": etapa, "q": q,
        "estados": Obra.Estado.choices, "etapas": Obra.Etapa.choices,
        "puede_crear": permisos.puede_crear_obra(request.user),
        "es_proyecto": tipo == Obra.Tipo.PROYECTO,
    })


def lista_proyectos(request):
    return lista(request, tipo=Obra.Tipo.PROYECTO)


@permisos.solo_personal
def obra_form(request, pk=None, tipo=Obra.Tipo.OBRA):
    obra = None
    if pk:
        obra = _obra_visible(request, pk)
        _exigir_edicion(request, obra)
    else:
        permisos.exigir(permisos.puede_crear_obra(request.user))
        _marcar_menu(request, tipo)
    form = ObraForm(request.POST or None, instance=obra, usuario=request.user, initial={} if obra else {
        "cliente": request.GET.get("cliente"), "tipo": tipo})
    if request.method == "POST" and form.is_valid():
        es_alta = obra is None
        cambios = {} if es_alta else _cambios(form)
        obra = form.save(commit=False)
        if es_alta:
            obra.creada_por = request.user
        plantilla = form.cleaned_data.get("plantilla") if es_alta else None
        origen = form.cleaned_data.get("copiar_de") if es_alta else None
        with transaction.atomic():
            obra.save()
            if plantilla or origen:
                arbol.copiar((plantilla or origen).tareas.all(), TareaObra, {"obra": obra})
                obra.recalcular_avance()
        if es_alta:
            fuente = f"la plantilla «{plantilla}»" if plantilla else f"las tareas de «{origen}»" if origen else ""
            registrar("obra.alta", f"Alta de {obra.etiqueta}: {obra}" + (f" con {fuente}" if fuente else ""), objeto=obra)
            if fuente:
                messages.success(request, f"{'Proyecto' if obra.es_proyecto else 'Obra'} {obra.codigo} "
                                          f"{'creado' if obra.es_proyecto else 'creada'} con {fuente}. "
                                          "Ajustá las etapas, rubros e ítems para este caso y guardá.")
                return redirect(f"{obra_url(obra)}?tab=tareas&editar=1")
            messages.success(request, f"{'Proyecto' if obra.es_proyecto else 'Obra'} {obra.codigo} "
                                      f"{'creado' if obra.es_proyecto else 'creada'}. Ahora sumá a su equipo.")
            return redirect(f"{obra_url(obra)}?tab=equipo")
        if cambios:
            registrar("obra.edicion", f"Edición de {obra.etiqueta}: {', '.join(cambios)}", objeto=obra,
                      detalle=cambios)
        messages.success(request, "Los datos quedaron guardados.")
        return redirect(obra_url(obra))
    return render(request, "obras/form.html", {"form": form, "obra": obra, "tipo": obra.tipo if obra else tipo})


def proyecto_form(request):
    return obra_form(request, tipo=Obra.Tipo.PROYECTO)


def obra_url(obra):
    return reverse("obras:detalle", args=[obra.pk])


@permisos.solo_personal
def detalle(request, pk):
    obra = _obra_visible(request, pk)
    puede_editar = permisos.puede_editar_obra(request.user, obra)
    pestanas = [p for p in PESTANAS if p[0] not in PESTANA_APP or apps.is_installed(PESTANA_APP[p[0]])]
    if not (puede_editar or permisos.puede_habilitar_horas(request.user)):
        pestanas = [p for p in pestanas if p[0] != "horas"]  # las horas del proyecto: responsables y quienes habilitan
    ver_montos = permisos.puede_ver_montos(request.user)
    if not (ver_montos and (obra.certificados.exists() or obra.tipo == Obra.Tipo.OBRA)):
        pestanas = [p for p in pestanas if p[0] != "certificados"]  # montos: Gerencia y Gestión Administrativa
    if not permisos.puede_ver_historial_avance(request.user):
        pestanas = [p for p in pestanas if p[0] != "historial"]
    tab = request.GET.get("tab", "resumen")
    if tab not in {p[0] for p in pestanas}:
        tab = "resumen"

    asignaciones = obra.asignaciones.select_related("usuario", "area")
    hitos = obra.hitos.all()
    contexto = {
        "obra": obra, "tab": tab, "pestanas": pestanas, "puede_editar": puede_editar, "hoy": date.today(),
        "asignaciones": asignaciones, "hitos": hitos,
        "personas_equipo": len({a.usuario_id for a in asignaciones}),
        "proximo_hito": hitos.filter(completado=False).first(),
        "hitos_hechos": sum(1 for h in hitos if h.completado),
    }
    if tab == "equipo" and puede_editar:
        contexto["form_asignacion"] = AsignacionForm(obra=obra)
    if tab == "hitos" and puede_editar:
        contexto["form_hito"] = HitoForm()
    if tab == "tareas":
        contexto.update(_contexto_tareas(obra, puede_editar))
        if permisos.puede_importar_certificado(request.user, obra):
            contexto["form_certificado"] = ImportarCertificadoForm()
        contexto["puede_crear_plantilla"] = permisos.puede_gestionar_plantillas(request.user)
        contexto["editando_tareas"] = puede_editar and request.GET.get("editar") == "1"
    if tab == "historial":
        filas = avances.retrospectiva(obra)
        contexto.update({"retrospectiva": filas,
                         "terminadas_medidas": [f for f in filas if f["dias"] is not None]})
    if tab == "certificados":
        contexto.update(_contexto_certificados(obra))
    if tab == "archivos":
        from apps.documentos.views import contexto_pestana_obra

        contexto.update(contexto_pestana_obra(request, obra))
    if tab == "horas":
        from apps.horas.views import horas_de_obra

        contexto.update(horas_de_obra(obra))
    if tab == "actividad":
        pagina = Paginator(obra.actividad.select_related("usuario"), 40).get_page(request.GET.get("pagina"))
        contexto["pagina"] = pagina
    return render(request, "obras/detalle.html", contexto)


# --- Equipo ------------------------------------------------------------------

@permisos.solo_personal
@require_POST
def equipo_agregar(request, pk):
    obra = _obra_visible(request, pk)
    _exigir_edicion(request, obra)
    form = AsignacionForm(request.POST, obra=obra)
    if form.is_valid():
        a = form.save()
        registrar("obra.equipo_alta", f"Se sumó a {a.usuario.nombre_completo} por {a.area.nombre}", objeto=obra,
                  detalle={"persona": a.usuario.email, "area": a.area.nombre, "funcion": a.funcion,
                           "responsable": a.es_responsable})
        messages.success(request, f"{a.usuario.nombre_completo} se sumó al equipo.")
    else:
        for errores in form.errors.values():
            for e in errores:
                messages.error(request, e)
    return redirect(f"{obra_url(obra)}?tab=equipo")


@permisos.solo_personal
@require_POST
def equipo_quitar(request, pk, asignacion_pk):
    obra = _obra_visible(request, pk)
    _exigir_edicion(request, obra)
    a = get_object_or_404(AsignacionObra, pk=asignacion_pk, obra=obra)
    if a.es_responsable and not obra.asignaciones.filter(es_responsable=True).exclude(pk=a.pk).exists() \
            and not permisos.es_gerencia(request.user):
        messages.error(request, "No podés quitar al único responsable de la obra. Pedíselo a Gerencia.")
        return redirect(f"{obra_url(obra)}?tab=equipo")
    registrar("obra.equipo_baja", f"Se quitó a {a.usuario.nombre_completo} ({a.area.nombre})", objeto=obra,
              detalle={"persona": a.usuario.email, "area": a.area.nombre})
    a.delete()
    messages.success(request, f"{a.usuario.nombre_completo} ya no está en el equipo de la obra.")
    return redirect(f"{obra_url(obra)}?tab=equipo")


@permisos.solo_personal
@require_POST
def equipo_responsable(request, pk, asignacion_pk):
    obra = _obra_visible(request, pk)
    _exigir_edicion(request, obra)
    a = get_object_or_404(AsignacionObra, pk=asignacion_pk, obra=obra)
    a.es_responsable = not a.es_responsable
    a.save(update_fields=["es_responsable"])
    registrar("obra.equipo_responsable",
              f"{a.usuario.nombre_completo} {'pasó a ser' if a.es_responsable else 'dejó de ser'} responsable de la obra",
              objeto=obra)
    return redirect(f"{obra_url(obra)}?tab=equipo")


# --- Hitos -------------------------------------------------------------------

@permisos.solo_personal
@require_POST
def hito_agregar(request, pk):
    obra = _obra_visible(request, pk)
    _exigir_edicion(request, obra)
    form = HitoForm(request.POST)
    if form.is_valid():
        hito = form.save(commit=False)
        hito.obra = obra
        hito.save()
        registrar("obra.hito_alta", f"Nuevo hito: {hito}", objeto=obra)
        messages.success(request, "Hito agregado.")
    else:
        messages.error(request, "Completá el título y la fecha del hito.")
    return redirect(f"{obra_url(obra)}?tab=hitos")


@permisos.solo_personal
@require_POST
def hito_alternar(request, pk, hito_pk):
    obra = _obra_visible(request, pk)
    _exigir_edicion(request, obra)
    hito = get_object_or_404(Hito, pk=hito_pk, obra=obra)
    hito.completado = not hito.completado
    hito.save(update_fields=["completado"])
    registrar("obra.hito_estado", f"Hito {'cumplido' if hito.completado else 'reabierto'}: {hito}", objeto=obra)
    return redirect(f"{obra_url(obra)}?tab=hitos")


@permisos.solo_personal
@require_POST
def hito_borrar(request, pk, hito_pk):
    obra = _obra_visible(request, pk)
    _exigir_edicion(request, obra)
    hito = get_object_or_404(Hito, pk=hito_pk, obra=obra)
    registrar("obra.hito_baja", f"Se quitó el hito: {hito}", objeto=obra)
    hito.delete()
    messages.success(request, "Hito quitado.")
    return redirect(f"{obra_url(obra)}?tab=hitos")


# --- Tareas (avance por incidencia) -----------------------------------------

def _contexto_tareas(obra, puede_editar, estructura=None, errores=None):
    tareas = list(obra.tareas.all())
    contexto = {
        "arbol": arbol.anotar(tareas),
        "con_codigos": any(t.codigo for t in tareas),
        "con_unidades": any(t.unidad for t in tareas),
        "estructura_json": estructura if estructura is not None else json.dumps(arbol.a_datos(tareas, con_avance=True)),
        "errores_estructura": errores or [],
    }
    if puede_editar:
        contexto["form_plantilla"] = AplicarPlantillaForm(tipo=obra.tipo)
    return contexto


@permisos.solo_personal
@require_POST
def tareas_guardar(request, pk):
    """Guarda la estructura completa (rubros, ítems, incidencias y avances) desde el editor."""
    obra = _obra_visible(request, pk)
    _exigir_edicion(request, obra)
    estructura = request.POST.get("estructura", "[]")
    try:
        datos = leer_estructura(estructura, con_avance=True, minimo_una=False)
    except ValidationError as e:
        messages.error(request, "Revisá las tareas: hay datos con errores.")
        contexto = {
            "obra": obra, "tab": "tareas", "puede_editar": True, "hoy": date.today(), "editando_tareas": True,
            "pestanas": [p for p in PESTANAS if p[0] not in PESTANA_APP or apps.is_installed(PESTANA_APP[p[0]])],
        }
        contexto.update(_contexto_tareas(obra, True, estructura, e.messages))
        return render(request, "obras/detalle.html", contexto)
    avance_antes = obra.avance
    with transaction.atomic():
        antes = arbol.guardar(TareaObra, {"obra": obra}, datos, con_avance=True)
        avances.registrar_cambios(obra, antes, usuario=request.user)
        obra.recalcular_avance()
    registrar("obra.tareas", f"Se modificó el listado de tareas · avance {avance_antes}% → {obra.avance}%",
              objeto=obra, detalle={"rubros": obra.tareas.filter(tipo=TareaObra.Tipo.RUBRO).count(),
                                    "items": obra.tareas.filter(tipo=TareaObra.Tipo.ITEM).count()})
    messages.success(request, f"Tareas guardadas. Avance: {obra.avance}%.")
    return redirect(f"{obra_url(obra)}?tab=tareas")


@permisos.solo_personal
@require_POST
def tarea_avance(request, pk, tarea_pk):
    """Guarda el avance de una tarea al soltar su barra. Responde los avances recalculados."""
    obra = _obra_visible(request, pk)
    _exigir_edicion(request, obra)
    tarea = get_object_or_404(TareaObra, pk=tarea_pk, obra=obra)
    if tarea.hijos.exists():
        return JsonResponse({"error": "El avance de un rubro o etapa se calcula con sus ítems."}, status=400)
    try:
        nuevo = max(0, min(100, int(request.POST.get("avance", ""))))
    except ValueError:
        return JsonResponse({"error": "Avance inválido."}, status=400)
    anterior = tarea.avance
    if nuevo != anterior:
        tarea.avance = nuevo
        tarea.save(update_fields=["avance", "actualizada"])
        avances.registrar(tarea, anterior, nuevo, usuario=request.user)
        obra.recalcular_avance()
        registrar("obra.tarea_avance", f"Avance de «{tarea.nombre}»: {anterior}% → {nuevo}%", objeto=obra)
    nodos = arbol.anotar(obra.tareas.all())
    calculados = {}

    def juntar(lista):
        for n in lista:
            calculados[n.id] = float(round(n.avance_calculado, 1))
            juntar(n.hijos_lista)

    juntar(nodos)
    return JsonResponse({"avance_obra": obra.avance, "avances": calculados})


@permisos.solo_personal
@require_POST
def tareas_aplicar_plantilla(request, pk):
    obra = _obra_visible(request, pk)
    _exigir_edicion(request, obra)
    form = AplicarPlantillaForm(request.POST, tipo=obra.tipo)
    if not form.is_valid():
        messages.error(request, "Elegí una plantilla.")
        return redirect(f"{obra_url(obra)}?tab=tareas")
    plantilla = form.cleaned_data["plantilla"]
    with transaction.atomic():
        reemplazadas = obra.tareas.count()
        arbol.copiar(plantilla.tareas.all(), TareaObra, {"obra": obra})
        obra.recalcular_avance()
    registrar("obra.plantilla", f"Se aplicó la plantilla «{plantilla}»"
              + (f" (reemplazó {reemplazadas} tareas)" if reemplazadas else ""), objeto=obra)
    messages.success(request, f"Se cargaron las tareas de «{plantilla}». Ajustalas si hace falta y "
                              "andá cargando el avance con las barras.")
    return redirect(f"{obra_url(obra)}?tab=tareas")


# --- Duplicar y reutilizar ---------------------------------------------------

@permisos.solo_personal
def duplicar(request, pk):
    """Crea un proyecto u obra nuevo con las mismas tareas (avance en 0) y, si se pide, el mismo equipo."""
    original = _obra_visible(request, pk)
    permisos.exigir(permisos.puede_crear_obra(request.user))
    form = DuplicarObraForm(request.POST or None, initial={
        "nombre": f"{original.nombre} (copia)", "cliente": original.cliente_id})
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            nueva = Obra.objects.create(
                tipo=original.tipo, nombre=form.cleaned_data["nombre"], cliente=form.cleaned_data["cliente"],
                descripcion=original.descripcion, superficie_m2=original.superficie_m2, creada_por=request.user,
            )
            arbol.copiar(original.tareas.all(), TareaObra, {"obra": nueva})
            nueva.recalcular_avance()
            if form.cleaned_data["copiar_equipo"]:
                AsignacionObra.objects.bulk_create([
                    AsignacionObra(obra=nueva, usuario_id=a.usuario_id, area_id=a.area_id, funcion=a.funcion,
                                   es_responsable=a.es_responsable)
                    for a in original.asignaciones.filter(usuario__is_active=True)
                ])
        registrar("obra.alta", f"Alta de {nueva.etiqueta}: {nueva} (duplicado de {original})", objeto=nueva)
        messages.success(request, f"Se creó {nueva.codigo} a partir de «{original.nombre}». "
                                  "Revisá las tareas y completá los datos que cambien.")
        return redirect(f"{obra_url(nueva)}?tab=tareas&editar=1")
    return render(request, "obras/duplicar.html", {"obra": original, "form": form})


@permisos.solo_personal
@require_POST
def tareas_a_plantilla(request, pk):
    """Guarda las tareas de este proyecto u obra (ya ajustadas) como una plantilla nueva."""
    obra = _obra_visible(request, pk)
    permisos.exigir(permisos.puede_gestionar_plantillas(request.user))
    form = GuardarPlantillaForm(request.POST)
    if not obra.tareas.exists():
        messages.error(request, "No hay tareas para guardar como plantilla.")
    elif not form.is_valid():
        messages.error(request, " ".join(e for errores in form.errors.values() for e in errores))
    else:
        with transaction.atomic():
            plantilla = Plantilla.objects.create(nombre=form.cleaned_data["nombre"], uso=obra.tipo,
                                                 descripcion=f"Creada a partir de {obra}.", creada_por=request.user)
            arbol.copiar(obra.tareas.all(), TareaPlantilla, {"plantilla": plantilla})
        registrar("plantilla.alta", f"Nueva plantilla: {plantilla} (desde {obra})", objeto=plantilla)
        messages.success(request, f"Se guardó la plantilla «{plantilla}». Ya la podés elegir al crear proyectos.")
    return redirect(f"{obra_url(obra)}?tab=tareas")


# --- Certificados de avance (montos: Gerencia y Gestión Administrativa) --------------------------------------

def _contexto_certificados(obra):
    lista = list(obra.certificados.all())
    # Cada certificado cubre desde el día siguiente al anterior (en general, una quincena).
    for actual, anterior in zip(lista, lista[1:] + [None]):
        actual.desde = anterior.fecha + timedelta(days=1) if anterior else None
    rubros = []
    presupuesto = certificado = Decimal(0)
    for nodo in arbol.anotar(obra.tareas.all()):
        hojas = []

        def juntar(n):
            if n.hijos_lista:
                for h in n.hijos_lista:
                    juntar(h)
            else:
                hojas.append(n)

        juntar(nodo)
        monto = sum((h.monto or 0 for h in hojas), Decimal(0))
        # Lo certificado según el certificado (puede pasar el presupuesto); si no hay, se estima con el avance.
        hecho = sum(((h.monto_certificado if h.monto_certificado is not None
                      else (h.monto or Decimal(0)) * h.avance / 100) for h in hojas), Decimal(0))
        if monto or hecho:
            rubros.append({"nodo": nodo, "monto": monto, "hecho": hecho, "pct": hecho * 100 / monto if monto else None,
                           "excedido": hecho > monto, "exceso": hecho - monto})
        presupuesto += monto
        certificado += hecho
    return {"certificados": lista, "ultimo_certificado": lista[0] if lista else None,
            "rubros_montos": rubros, "presupuesto_tareas": presupuesto, "certificado_tareas": certificado,
            "pct_certificado": certificado * 100 / presupuesto if presupuesto else None}


@permisos.solo_personal
@require_POST
def certificado_importar(request, pk):
    """Carga un certificado de avance desde Excel: deja las tareas como dice el certificado y guarda sus montos."""
    obra = _obra_visible(request, pk)
    permisos.exigir(permisos.puede_importar_certificado(request.user, obra))
    form = ImportarCertificadoForm(request.POST, request.FILES)
    if not form.is_valid():
        for errores in form.errors.values():
            for e in errores:
                messages.error(request, e)
        return redirect(f"{obra_url(obra)}?tab=tareas")
    archivo = form.cleaned_data["archivo"]
    try:
        datos = certificados.leer(archivo)
        archivo.seek(0)
        cert = certificados.aplicar(obra, datos, request.user, numero=form.cleaned_data["numero"],
                                    fecha=form.cleaned_data["fecha"], archivo=archivo)
    except ValidationError as e:
        for m in e.messages:
            messages.error(request, m)
        return redirect(f"{obra_url(obra)}?tab=tareas")
    items = obra.tareas.filter(tipo=TareaObra.Tipo.ITEM).count()
    registrar("obra.certificado", f"Se cargó el certificado N° {cert.numero} del {cert.fecha:%d/%m/%Y} · "
              f"avance {obra.avance}%", objeto=obra, detalle={"certificado": cert.pk, "items": items})
    messages.success(request, f"Certificado N° {cert.numero} cargado: {items} ítems, avance de la obra {obra.avance}%.")
    return redirect(f"{obra_url(obra)}?tab=tareas")


@permisos.solo_personal
def certificado_archivo(request, pk, cert_pk):
    obra = _obra_visible(request, pk)
    permisos.exigir(permisos.puede_ver_montos(request.user))
    cert = get_object_or_404(Certificado, pk=cert_pk, obra=obra)
    if not cert.archivo:
        raise Http404
    nombre = f"{obra.codigo or obra.nombre} - Certificado {cert.numero}.xlsx"
    return FileResponse(cert.archivo.open("rb"), as_attachment=True, filename=nombre)
