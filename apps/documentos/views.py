import mimetypes

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST

from apps.auditoria.models import RegistroActividad
from apps.auditoria.services import registrar
from apps.core.utils import cambios_de_formulario
from apps.cuentas import permisos
from apps.cuentas.models import Area
from apps.obras.models import Obra

from . import formatos, procesar, services
from .forms import DocumentoForm, EnlaceForm, SubirForm, VersionForm
from .models import Documento, VersionDocumento

T = Documento.Tipo
CON_VERSIONES = Prefetch("versiones", queryset=VersionDocumento.objects.order_by("-numero"),
                         to_attr="_versiones_prefetch")


def _documento(request, pk, incluir_papelera=False):
    doc = get_object_or_404(Documento.objects.select_related("obra", "area", "creado_por"), pk=pk)
    permisos.exigir(permisos.puede_ver_documento(request.user, doc, incluir_papelera=incluir_papelera))
    return doc


def _exigir_admin(request, doc):
    permisos.exigir(permisos.puede_administrar_documento(request.user, doc))


def _volver(doc):
    return redirect("documentos:detalle", pk=doc.pk)


def _ejecutar(request, doc, operacion, *args, exito=None):
    try:
        operacion(doc, request.user, *args)
        if exito:
            messages.success(request, exito)
    except services.OperacionNoPermitida as e:
        messages.error(request, str(e))
    return _volver(doc)


# --- Listados ----------------------------------------------------------------

@permisos.solo_personal
def lista(request):
    u = request.user
    f = {k: request.GET.get(k, "") for k in ("obra", "tipo", "area", "acceso", "q", "vista")}
    docs = permisos.documentos_visibles(u).select_related("obra", "area").prefetch_related(CON_VERSIONES)
    docs = docs.filter(archivado=(f["vista"] == "archivados"))
    if f["vista"] == "mios":
        docs = docs.filter(creado_por=u)
    if f["obra"] == "general":
        docs = docs.filter(obra__isnull=True)
    elif f["obra"].isdigit():
        docs = docs.filter(obra_id=f["obra"])
    if f["tipo"]:
        docs = docs.filter(tipo=f["tipo"])
    if f["area"].isdigit():
        docs = docs.filter(area_id=f["area"])
    if f["acceso"]:
        docs = docs.filter(acceso=f["acceso"])
    if f["q"]:
        q = f["q"]
        docs = docs.filter(Q(titulo__icontains=q) | Q(numero__icontains=q) | Q(etiquetas__icontains=q)
                           | Q(descripcion__icontains=q) | Q(versiones__nombre_original__icontains=q)).distinct()
    pagina = Paginator(docs.order_by("-actualizado"), 30).get_page(request.GET.get("pagina"))
    return render(request, "documentos/lista.html", {
        "pagina": pagina, "f": f,
        "obras": permisos.obras_del_equipo(u).order_by("nombre"),
        "tipos": T.choices, "areas": Area.objects.all(), "accesos": Documento.Acceso.choices,
        "en_papelera": Documento.objects.filter(en_papelera=True).count() if permisos.es_gerencia(u) else None,
    })


@permisos.solo_personal
def papelera(request):
    docs = Documento.objects.filter(en_papelera=True).select_related("obra", "papelera_por")
    visibles = [d for d in docs.order_by("-papelera_en") if permisos.puede_administrar_documento(request.user, d)]
    return render(request, "documentos/papelera.html", {
        "documentos": visibles, "puede_eliminar": permisos.puede_eliminar_definitivo(request.user),
    })


# --- Subir ---------------------------------------------------------------------

@permisos.solo_personal
def agregar_enlace(request):
    """Documento que vive en Google Drive: se guarda el enlace, no se sube ni se duplica el archivo."""
    u = request.user
    inicial = {"tipo": request.GET.get("tipo") or T.PLANOS}
    if request.GET.get("obra", "").isdigit():
        inicial["obra"] = request.GET["obra"]
    form = EnlaceForm(request.POST or None, usuario=u, initial=inicial)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        previo = services.enlace_repetido(d["obra"], d["enlace"])
        if previo:
            messages.warning(request, f"Ese enlace ya está cargado como «{previo.documento}».")
            return redirect("documentos:detalle", pk=previo.documento_id)
        doc, _ = services.crear_documento_enlace(
            u, d["enlace"], obra=d["obra"], tipo=d["tipo"], titulo=d["titulo"], area=d["area"], acceso=d["acceso"],
            etiquetas=d["etiquetas"], comentario=d["comentario"],
            numero=d["numero"] if d["tipo"] == T.PLANOS else "")
        messages.success(request, f"Se agregó «{doc}» con su enlace de Drive.")
        return redirect("documentos:detalle", pk=doc.pk)
    return render(request, "documentos/enlace.html", {"form": form})


@permisos.solo_personal
def subir(request):
    u = request.user
    inicial = {"tipo": request.GET.get("tipo") or T.PLANOS}
    if request.GET.get("obra", "").isdigit():
        inicial["obra"] = request.GET["obra"]
    form = SubirForm(request.POST or None, request.FILES or None, usuario=u, initial=inicial)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        resumen = services.subir_lote(u, d["archivos"], obra=d["obra"], tipo=d["tipo"], area=d["area"],
                                      acceso=d["acceso"], etiquetas=d["etiquetas"], comentario=d["comentario"])
        if resumen["creados"]:
            messages.success(request, f"Se subieron {len(resumen['creados'])} documento(s).")
        for texto in resumen["versiones"]:
            messages.success(request, f"Versión nueva: {texto}.")
        for texto in resumen["duplicados"]:
            messages.warning(request, texto)
        for texto in resumen["rechazados"]:
            messages.error(request, texto)
        if len(resumen["creados"]) == 1 and not resumen["versiones"]:
            return redirect("documentos:detalle", pk=resumen["creados"][0].pk)
        if d["obra"] is not None:
            return redirect(f"{reverse('obras:detalle', args=[d['obra'].pk])}?tab=archivos&tipo={d['tipo']}")
        return redirect(f"{reverse('documentos:lista')}?obra=general")
    formatos_por_tipo = {t: formatos.descripcion_formatos(t) for t, _ in T.choices}
    return render(request, "documentos/subir.html", {"form": form, "formatos_por_tipo": formatos_por_tipo})


# --- Ficha del documento ----------------------------------------------------

@permisos.solo_personal
def detalle(request, pk):
    u = request.user
    doc = _documento(request, pk, incluir_papelera=True)
    versiones = list(doc.versiones.select_related("subido_por", "aprobada_por"))
    vigente = versiones[0] if versiones else None
    hojas = None
    if vigente and vigente.es_planilla and not vigente.es_enlace:
        try:
            hojas = procesar.leer_planilla(vigente)
        except Exception:  # noqa: BLE001
            hojas = []
    actividad = RegistroActividad.objects.filter(objeto_tipo=Documento._meta.verbose_name,
                                                 objeto_id=str(doc.pk)).select_related("usuario")[:50]
    puede_admin = permisos.puede_administrar_documento(u, doc)
    return render(request, "documentos/detalle.html", {
        "doc": doc, "versiones": versiones, "vigente": vigente, "hojas": hojas, "actividad": actividad,
        "para_obra": doc.version_para_obra() if doc.es_plano else None,
        "puede_admin": puede_admin,
        "puede_compartir": permisos.puede_compartir_con_cliente(u, doc),
        "puede_aprobar": doc.es_plano and permisos.puede_aprobar_planos(u),
        "puede_eliminar": permisos.puede_eliminar_definitivo(u),
        "form_version": VersionForm(documento=doc) if puede_admin else None,
    })


@permisos.solo_personal
def editar(request, pk):
    doc = _documento(request, pk)
    _exigir_admin(request, doc)
    form = DocumentoForm(request.POST or None, instance=doc, usuario=request.user)
    if request.method == "POST" and form.is_valid():
        cambios = cambios_de_formulario(form)
        acceso_anterior = Documento.objects.get(pk=doc.pk).acceso
        form.save()
        if cambios:
            accion = "documento.edicion"
            if doc.acceso != acceso_anterior and Documento.Acceso.CLIENTE in (doc.acceso, acceso_anterior):
                accion = "documento.compartido" if doc.acceso == Documento.Acceso.CLIENTE else "documento.descompartido"
            registrar(accion, f"Editó «{doc}»: {', '.join(cambios)}", objeto=doc, detalle=cambios)
        messages.success(request, "Los datos del documento quedaron guardados.")
        return _volver(doc)
    return render(request, "documentos/editar.html", {"form": form, "doc": doc})


@permisos.solo_personal
@require_POST
def nueva_version(request, pk):
    doc = _documento(request, pk)
    _exigir_admin(request, doc)
    form = VersionForm(request.POST, request.FILES, documento=doc)
    if form.is_valid():
        d = form.cleaned_data
        if d["enlace"]:
            version = services.agregar_version_enlace(doc, request.user, d["enlace"], comentario=d["comentario"],
                                                      revision=d["revision"])
            messages.success(request, f"Se agregó la Rev {version.revision} (enlace de Drive).")
            return _volver(doc)
        sha = procesar.huella(d["archivo"])
        previo = services.duplicado_en_obra(doc.obra, sha)
        if previo:
            messages.warning(request, f"Ese archivo ya está subido como «{previo.documento}» Rev {previo.revision}.")
            return _volver(doc)
        version = services.agregar_version(doc, request.user, d["archivo"], comentario=d["comentario"],
                                           revision=d["revision"], editable=d.get("editable"), sha256=sha)
        messages.success(request, f"Se subió la Rev {version.revision}.")
    else:
        for errores in form.errors.values():
            for e in errores:
                messages.error(request, e)
    return _volver(doc)


# --- Acciones ------------------------------------------------------------------

@permisos.solo_personal
@require_POST
def compartir(request, pk):
    doc = _documento(request, pk)
    nuevo = Documento.Acceso.EQUIPO if doc.acceso == Documento.Acceso.CLIENTE else Documento.Acceso.CLIENTE
    texto = "Ahora el cliente ve este documento." if nuevo == Documento.Acceso.CLIENTE else \
        "El cliente ya no ve este documento."
    return _ejecutar(request, doc, services.cambiar_acceso, nuevo, exito=texto)


@permisos.solo_personal
@require_POST
def plano_revision(request, pk):
    doc = _documento(request, pk)
    _exigir_admin(request, doc)
    return _ejecutar(request, doc, services.pasar_a_revision, exito="El plano pasó a revisión de Dirección Técnica.")


@permisos.solo_personal
@require_POST
def plano_aprobar(request, pk):
    doc = _documento(request, pk)
    return _ejecutar(request, doc, services.aprobar_plano, exito="Plano aprobado para obra.")


@permisos.solo_personal
@require_POST
def plano_observar(request, pk):
    doc = _documento(request, pk)
    comentario = request.POST.get("comentario", "").strip()
    if not comentario:
        messages.error(request, "Escribí las observaciones para que se puedan corregir.")
        return _volver(doc)
    return _ejecutar(request, doc, services.observar_plano, comentario,
                     exito="El plano volvió a elaboración con tus observaciones.")


@permisos.solo_personal
@require_POST
def archivar(request, pk):
    doc = _documento(request, pk)
    _exigir_admin(request, doc)
    return _ejecutar(request, doc, services.alternar_archivado)


@permisos.solo_personal
@require_POST
def a_papelera(request, pk):
    doc = _documento(request, pk)
    _exigir_admin(request, doc)
    services.a_papelera(doc, request.user)
    messages.success(request, f"«{doc}» se mandó a la papelera. Se puede restaurar.")
    if doc.obra_id:
        return redirect(f"{reverse('obras:detalle', args=[doc.obra_id])}?tab=archivos")
    return redirect("documentos:lista")


@permisos.solo_personal
@require_POST
def restaurar(request, pk):
    doc = _documento(request, pk, incluir_papelera=True)
    _exigir_admin(request, doc)
    return _ejecutar(request, doc, services.restaurar, exito="Documento restaurado.")


@permisos.solo_personal
def eliminar(request, pk):
    doc = _documento(request, pk, incluir_papelera=True)
    permisos.exigir(permisos.puede_eliminar_definitivo(request.user))
    if request.method == "POST":
        try:
            services.eliminar_definitivo(doc, request.user)
            messages.success(request, "El documento se borró definitivamente. El registro de actividad lo conserva.")
            return redirect("documentos:papelera")
        except services.OperacionNoPermitida as e:
            messages.error(request, str(e))
            return _volver(doc)
    return render(request, "documentos/eliminar.html", {"doc": doc, "versiones": doc.versiones.all()})


# --- Archivos (siempre a través del permiso) --------------------------------

def _version_accesible(request, version_pk):
    version = get_object_or_404(VersionDocumento.objects.select_related("documento__obra", "documento__area"),
                                pk=version_pk)
    doc = version.documento
    permisos.exigir(permisos.puede_ver_documento(request.user, doc, incluir_papelera=True))
    if doc.en_papelera:
        permisos.exigir(permisos.puede_administrar_documento(request.user, doc))
    if permisos.es_cliente(request.user):
        para_cliente = doc.version_para_cliente()
        if para_cliente is None or para_cliente.pk != version.pk:
            raise Http404
    return version


def _respuesta(archivo, nombre, descarga):
    tipo = mimetypes.guess_type(nombre)[0] or "application/octet-stream"
    respuesta = FileResponse(archivo.open("rb"), as_attachment=descarga, filename=nombre, content_type=tipo)
    respuesta["Cache-Control"] = "private, no-store"
    return respuesta


@login_required
@xframe_options_sameorigin
def ver(request, version_pk):
    version = _version_accesible(request, version_pk)
    if version.es_enlace:
        services.registrar_acceso(version, request.user, descarga=False)
        return redirect(version.enlace)
    if version.vista_previa and version.extension in ("heic", "heif"):
        archivo, nombre = version.vista_previa, version.nombre_original.rsplit(".", 1)[0] + ".jpg"
    elif version.se_ve_en_navegador:
        archivo, nombre = version.archivo, version.nombre_original
    else:
        return redirect("documentos:descargar", version_pk=version.pk)
    services.registrar_acceso(version, request.user, descarga=False)
    return _respuesta(archivo, nombre, descarga=False)


@login_required
def descargar(request, version_pk):
    version = _version_accesible(request, version_pk)
    if version.es_enlace:  # el archivo vive en Drive: se abre ahí (Drive tiene su propio botón de descarga)
        services.registrar_acceso(version, request.user, descarga=False)
        return redirect(version.enlace)
    services.registrar_acceso(version, request.user, descarga=True)
    return _respuesta(version.archivo, version.nombre_original, descarga=True)


@permisos.solo_personal
def descargar_editable(request, version_pk):
    version = _version_accesible(request, version_pk)
    if not version.editable:
        raise Http404
    services.registrar_acceso(version, request.user, descarga=True, editable=True)
    return _respuesta(version.editable, version.editable_nombre, descarga=True)


@login_required
def miniatura(request, version_pk):
    """Vista previa liviana para galerías. No se asienta (sería una fila por cada foto de la grilla)."""
    version = _version_accesible(request, version_pk)
    if not version.vista_previa:
        raise Http404
    return _respuesta(version.vista_previa, "vista.jpg", descarga=False)


# --- Pestaña "Archivos" de la obra -------------------------------------------

def contexto_pestana_obra(request, obra):
    """Lo usa la ficha de la obra para armar su pestaña de archivos."""
    u = request.user
    tipo = request.GET.get("tipo", "")
    docs = (permisos.documentos_visibles(u).filter(obra=obra, archivado=False).select_related("area")
            .prefetch_related(CON_VERSIONES))
    cantidades = {f["tipo"]: f["n"] for f in docs.order_by().values("tipo").annotate(n=Count("id"))}
    carpetas = [{"tipo": t, "nombre": n, "cantidad": cantidades.get(t, 0)} for t, n in T.choices]
    if tipo:
        docs = docs.filter(tipo=tipo)
    if tipo == T.PLANOS:
        docs = docs.order_by("numero", "titulo")
    elif tipo == T.FOTOS:
        docs = docs.order_by("-fecha_documento", "-creado")
    else:
        docs = docs.order_by("tipo", "-actualizado")
    return {
        "carpetas": carpetas, "tipo_actual": tipo, "documentos": docs,
        "puede_subir": permisos.puede_subir_documentos(u, obra),
        "total_documentos": sum(cantidades.values()),
    }
