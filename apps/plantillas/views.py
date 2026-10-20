import json

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.auditoria.services import registrar
from apps.cuentas import permisos

from . import arbol
from .forms import PlantillaForm, leer_estructura
from .models import Plantilla, TareaPlantilla

T = TareaPlantilla.Tipo


@permisos.solo_personal
def lista(request):
    plantillas = Plantilla.objects.annotate(
        etapas=Count("tareas", filter=Q(tareas__tipo=T.ETAPA)),
        rubros=Count("tareas", filter=Q(tareas__tipo=T.RUBRO)),
        items=Count("tareas", filter=Q(tareas__tipo=T.ITEM)),
    )
    return render(request, "plantillas/lista.html", {
        "plantillas": plantillas,
        "puede_gestionar": permisos.puede_gestionar_plantillas(request.user),
    })


@permisos.solo_personal
def detalle(request, pk):
    plantilla = get_object_or_404(Plantilla, pk=pk)
    return render(request, "plantillas/detalle.html", {
        "plantilla": plantilla,
        "arbol": arbol.anotar(plantilla.tareas.all()),
        "puede_gestionar": permisos.puede_gestionar_plantillas(request.user),
    })


@permisos.solo_personal
def plantilla_form(request, pk=None):
    permisos.exigir(permisos.puede_gestionar_plantillas(request.user))
    plantilla = get_object_or_404(Plantilla, pk=pk) if pk else Plantilla()
    form = PlantillaForm(request.POST or None, instance=plantilla)
    estructura = request.POST.get("estructura") if request.method == "POST" else json.dumps(
        arbol.a_datos(plantilla.tareas.all()) if plantilla.pk else [])
    errores_estructura = []
    if request.method == "POST":
        try:
            datos = leer_estructura(estructura)
        except ValidationError as e:
            errores_estructura = e.messages
        if form.is_valid() and not errores_estructura:
            es_alta = plantilla.pk is None
            with transaction.atomic():
                plantilla = form.save(commit=False)
                if es_alta:
                    plantilla.creada_por = request.user
                plantilla.save()
                arbol.guardar(TareaPlantilla, {"plantilla": plantilla}, datos)
            registrar("plantilla.alta" if es_alta else "plantilla.edicion",
                      f"{'Nueva plantilla' if es_alta else 'Plantilla modificada'}: {plantilla}", objeto=plantilla,
                      detalle={"rubros": plantilla.tareas.filter(tipo=T.RUBRO).count(),
                               "items": plantilla.tareas.filter(tipo=T.ITEM).count()})
            messages.success(request, f"La plantilla «{plantilla}» quedó guardada.")
            return redirect("plantillas:detalle", plantilla.pk)
    return render(request, "plantillas/form.html", {
        "form": form, "plantilla": plantilla if plantilla.pk else None,
        "estructura": estructura, "errores_estructura": errores_estructura,
    })


@permisos.solo_personal
@require_POST
def duplicar(request, pk):
    permisos.exigir(permisos.puede_gestionar_plantillas(request.user))
    original = get_object_or_404(Plantilla, pk=pk)
    nombre, n = f"{original.nombre} (copia)", 2
    while Plantilla.objects.filter(nombre=nombre).exists():
        nombre, n = f"{original.nombre} (copia {n})", n + 1
    with transaction.atomic():
        copia = Plantilla.objects.create(nombre=nombre, uso=original.uso, descripcion=original.descripcion,
                                         creada_por=request.user)
        arbol.copiar(original.tareas.all(), TareaPlantilla, {"plantilla": copia})
    registrar("plantilla.alta", f"Nueva plantilla: {copia} (copia de {original})", objeto=copia)
    messages.success(request, f"Se creó «{copia}». Cambiale el nombre y ajustala.")
    return redirect("plantillas:editar", copia.pk)


@permisos.solo_personal
@require_POST
def borrar(request, pk):
    permisos.exigir(permisos.puede_gestionar_plantillas(request.user))
    plantilla = get_object_or_404(Plantilla, pk=pk)
    registrar("plantilla.baja", f"Se borró la plantilla: {plantilla}", objeto=plantilla)
    plantilla.delete()
    messages.success(request, f"Plantilla «{plantilla}» borrada. Los proyectos y obras que la usaron conservan sus tareas.")
    return redirect("plantillas:lista")
