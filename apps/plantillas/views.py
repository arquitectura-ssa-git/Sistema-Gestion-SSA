from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.auditoria.services import registrar
from apps.cuentas import permisos

from .forms import PlantillaForm, TareasPlantillaFormSet
from .models import Plantilla


@permisos.solo_personal
def lista(request):
    plantillas = Plantilla.objects.annotate(cantidad=Count("tareas"), total=Sum("tareas__incidencia"))
    return render(request, "plantillas/lista.html", {
        "plantillas": plantillas,
        "puede_gestionar": permisos.puede_gestionar_plantillas(request.user),
    })


@permisos.solo_personal
def detalle(request, pk):
    plantilla = get_object_or_404(Plantilla, pk=pk)
    return render(request, "plantillas/detalle.html", {
        "plantilla": plantilla,
        "tareas": plantilla.tareas.all(),
        "puede_gestionar": permisos.puede_gestionar_plantillas(request.user),
    })


@permisos.solo_personal
def plantilla_form(request, pk=None):
    permisos.exigir(permisos.puede_gestionar_plantillas(request.user))
    plantilla = get_object_or_404(Plantilla, pk=pk) if pk else Plantilla()
    form = PlantillaForm(request.POST or None, instance=plantilla)
    formset = TareasPlantillaFormSet(request.POST or None, instance=plantilla, prefix="tareas")
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        es_alta = plantilla.pk is None
        with transaction.atomic():
            plantilla = form.save(commit=False)
            if es_alta:
                plantilla.creada_por = request.user
            plantilla.save()
            formset.instance = plantilla
            formset.save()
        registrar("plantilla.alta" if es_alta else "plantilla.edicion",
                  f"{'Nueva plantilla' if es_alta else 'Plantilla modificada'}: {plantilla}", objeto=plantilla,
                  detalle={t.nombre: f"{t.incidencia:g}%" for t in plantilla.tareas.all()})
        messages.success(request, f"La plantilla «{plantilla}» quedó guardada.")
        return redirect("plantillas:detalle", plantilla.pk)
    return render(request, "plantillas/form.html", {
        "form": form, "formset": formset, "plantilla": plantilla if plantilla.pk else None,
    })


@permisos.solo_personal
@require_POST
def borrar(request, pk):
    permisos.exigir(permisos.puede_gestionar_plantillas(request.user))
    plantilla = get_object_or_404(Plantilla, pk=pk)
    registrar("plantilla.baja", f"Se borró la plantilla: {plantilla}", objeto=plantilla)
    plantilla.delete()
    messages.success(request, f"Plantilla «{plantilla}» borrada. Los proyectos y obras que la usaron conservan sus tareas.")
    return redirect("plantillas:lista")
