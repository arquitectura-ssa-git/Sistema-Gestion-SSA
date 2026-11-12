import mimetypes
from datetime import timedelta

from django.contrib import messages
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.auditoria.models import RegistroActividad
from apps.auditoria.services import registrar
from apps.cuentas import permisos
from apps.cuentas.models import Usuario
from apps.horas.reglas import hoy

from .forms import DocumentoForm
from .models import DocumentoLegajo

T = DocumentoLegajo.Tipo
DIAS_AVISO = 60


def _exigir(request):
    permisos.exigir(permisos.puede_ver_legajos(request.user))
    request.menu_activo = "cuentas:personal"


def _personal():
    return Usuario.objects.filter(tipo=Usuario.Tipo.PERSONAL, is_active=True).order_by("last_name", "first_name")



@permisos.solo_personal
def lista(request):
    _exigir(request)
    q = request.GET.get("q", "").strip()
    solo_incompletos = request.GET.get("incompletos") == "1"
    personas = _personal()
    if q:
        personas = personas.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))
    docs = {}
    for d in DocumentoLegajo.objects.filter(usuario__in=personas).order_by("-subido"):
        docs.setdefault(d.usuario_id, []).append(d)
    limite = hoy() + timedelta(days=DIAS_AVISO)
    filas, vencen = [], 0
    personas = sorted(personas, key=lambda p: p.orden_apellido)
    for p in personas:
        propios = docs.get(p.pk, [])
        tipos = {d.tipo for d in propios}
        estado = [{"tipo": t, "cargado": t in tipos} for t in DocumentoLegajo.OBLIGATORIOS]
        faltan = sum(1 for e in estado if not e["cargado"])
        contrato = next((d for d in propios if d.tipo == T.CONTRATO and d.vence), None)
        por_vencer = bool(contrato and contrato.vence <= limite)
        vencen += por_vencer
        if solo_incompletos and not faltan:
            continue
        filas.append({"persona": p, "estado": estado, "faltan": faltan, "contrato": contrato, "por_vencer": por_vencer,
                      "otros": sum(1 for d in propios if d.tipo == T.OTRO)})
    todas = len(personas)
    completos = sum(1 for p in personas if {d.tipo for d in docs.get(p.pk, [])} >= set(DocumentoLegajo.OBLIGATORIOS))
    return render(request, "legajos/lista.html", {
        "filas": filas, "q": q, "solo_incompletos": solo_incompletos,
        "resumen": {"personas": todas, "completos": completos, "incompletos": todas - completos, "vencen": vencen},
        "obligatorios": [(t.value, t.label) for t in DocumentoLegajo.OBLIGATORIOS],
    })


@permisos.solo_personal
def detalle(request, pk):
    _exigir(request)
    persona = get_object_or_404(Usuario, pk=pk, tipo=Usuario.Tipo.PERSONAL)
    if request.method == "POST":
        form = DocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.usuario, doc.subido_por = persona, request.user
            doc.nombre_original = request.FILES["archivo"].name[:200]
            doc.save()
            registrar("legajo.alta", f"Legajo de {persona.nombre_completo}: se subió «{doc.titulo}»", objeto=persona)
            messages.success(request, f"Se subió «{doc.titulo}».")
            return redirect("legajos:detalle", pk=persona.pk)
        messages.error(request, " ".join(e for errores in form.errors.values() for e in errores))
    propios = list(persona.legajo.select_related("subido_por"))
    secciones = [{"tipo": t.value, "titulo": t.label, "docs": [d for d in propios if d.tipo == t],
                  "con_vencimiento": t == T.CONTRATO} for t in DocumentoLegajo.OBLIGATORIOS]
    otros = [d for d in propios if d.tipo == T.OTRO]
    faltan = sum(1 for s in secciones if not s["docs"])
    contrato = next((d for d in propios if d.tipo == T.CONTRATO and d.vence), None)
    return render(request, "legajos/detalle.html", {
        "persona": persona, "secciones": secciones, "otros": otros, "faltan": faltan, "contrato": contrato,
        "hoy": hoy(), "limite_aviso": hoy() + timedelta(days=DIAS_AVISO),
        "movimientos": RegistroActividad.objects.filter(accion__in=["legajo.alta", "legajo.baja"],
                                                        objeto_id=str(persona.pk)).order_by("-id")[:8],
    })


@permisos.solo_personal
def archivo(request, pk):
    _exigir(request)
    doc = get_object_or_404(DocumentoLegajo.objects.select_related("usuario"), pk=pk)
    registrar("legajo.ver", f"Legajo de {doc.usuario.nombre_completo}: se abrió «{doc.titulo}»", objeto=doc.usuario)
    tipo = mimetypes.guess_type(doc.archivo.name)[0] or "application/octet-stream"
    respuesta = FileResponse(doc.archivo.open("rb"), content_type=tipo,
                             as_attachment=request.GET.get("descargar") == "1",
                             filename=doc.nombre_original or None)
    respuesta["Cache-Control"] = "private, no-store"
    return respuesta


@permisos.solo_personal
@require_POST
def quitar(request, pk):
    _exigir(request)
    doc = get_object_or_404(DocumentoLegajo.objects.select_related("usuario"), pk=pk)
    persona, titulo = doc.usuario, doc.titulo
    doc.archivo.delete(save=False)
    doc.delete()
    registrar("legajo.baja", f"Legajo de {persona.nombre_completo}: se quitó «{titulo}»", objeto=persona)
    messages.success(request, f"Se quitó «{titulo}».")
    return redirect("legajos:detalle", pk=persona.pk)
