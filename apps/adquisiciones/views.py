import mimetypes
import uuid
from collections import Counter, OrderedDict
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.agenda.models import Contacto, TipoContacto
from apps.auditoria.services import registrar
from apps.cuentas import permisos
from apps.informes.forms import preparar_foto
from apps.obras.models import Obra

from . import importar_trello, reglas
from .forms import (AdjuntosForm, CotizacionForm, EntregaForm, FacturaForm, ImportarTrelloForm, ItemsFormSet,
                    PedidoForm, RecepcionForm)
from .models import Adjunto, Cotizacion, Movimiento, Pedido, Recepcion

E = Pedido.Estado
ABIERTOS = [e for e in E if e not in (E.CERRADO, E.RECHAZADO)]
UNIDADES = ["unidades", "bolsas", "m", "m²", "m³", "kg", "t", "litros", "par", "rollos", "global"]


def _menu(request):
    request.menu_activo = "adquisiciones:inicio"


def _pedido(request, pk):
    p = get_object_or_404(Pedido.objects.select_related("obra", "creado_por"), pk=pk, obra__eliminada=False)
    permisos.exigir(permisos.puede_ver_pedido(request.user, p))
    return p


def _obras_para_pedir(u):
    obras = Obra.objects.filter(eliminada=False).exclude(estado=Obra.Estado.FINALIZADA)
    if not (permisos.puede_gestionar_compras(u) or permisos.es_coordinador(u)):
        obras = obras.filter(asignaciones__usuario=u).distinct()
    return obras.order_by("tipo", "codigo")


def _filtros(request, qs):
    obra = request.GET.get("obra", "")
    tipo = request.GET.get("tipo", "")
    q = request.GET.get("q", "").strip()
    if obra.isdigit():
        qs = qs.filter(obra_id=obra)
    if tipo in Pedido.Tipo.values:
        qs = qs.filter(tipo=tipo)
    if q:
        qs = reglas.busqueda(qs, q)
    return qs, {"obra": obra, "tipo": tipo, "q": q}


def _con_montos(u, pedidos):
    for p in pedidos:
        p.ver_montos = permisos.puede_ver_montos_pedido(u, p)
    return pedidos


@permisos.solo_personal
def inicio(request):
    """«Mis pendientes»: lo que le toca mover a cada uno, el resumen por obra y los últimos movimientos."""
    _menu(request)
    u = request.user
    visibles = reglas.visibles(u)
    mios = _con_montos(u, reglas.pendientes_de(u))
    abiertos = list(visibles.filter(estado__in=ABIERTOS).prefetch_related("cotizaciones"))
    _con_montos(u, abiertos)
    grupos = OrderedDict()
    for p in sorted(abiertos, key=lambda x: (x.obra.tipo, x.obra.codigo)):
        g = grupos.setdefault(p.obra_id, {"obra": p.obra, "cuenta": Counter(), "monto": 0, "sin_monto": 0, "ver": True})
        g["cuenta"][p.estado] += 1
        if p.monto is not None:
            g["monto"] += p.monto
        else:
            g["sin_monto"] += 1
        g["ver"] = g["ver"] and p.ver_montos
    columnas = [e for e in reglas.CIRCUITO_OBRA]
    por_obra = [{**g, "celdas": [g["cuenta"].get(e, 0) for e in columnas]} for g in grupos.values()]
    hoy_ids = {p.pk for p in mios}
    tarjetas = {
        "nuevos": [p for p in mios if p.estado == E.PEDIDO and not p.devuelto],
        "devueltos": [p for p in mios if p.devuelto],
        "autorizar": [p for p in mios if p.estado == E.AUTORIZACION],
        "recibir": [p for p in mios if p.estado == E.RECEPCION],
    }
    movimientos = (Movimiento.objects.filter(pedido__in=visibles).select_related("pedido", "usuario")[:12])
    return render(request, "adquisiciones/inicio.html", {
        "mios": mios, "tarjetas": tarjetas, "por_obra": por_obra,
        "columnas_tabla": list(zip(["Pedido", "Cotiz.", "OC", "DIR", "Factura", "Compra", "Entrega", "Recibido"],
                                   [E(e).label for e in columnas])),
        "movimientos": movimientos, "total_abiertos": len(abiertos), "hoy_ids": hoy_ids,
        "obras_abiertas": len(grupos), "puede_pedir": _obras_para_pedir(u).exists(),
        "es_compras": permisos.puede_gestionar_compras(u),
    })


@permisos.solo_personal
def tablero(request):
    _menu(request)
    u = request.user
    qs, filtro = _filtros(request, reglas.visibles(u).filter(estado__in=ABIERTOS).prefetch_related("cotizaciones"))
    pedidos = _con_montos(u, list(qs.order_by("-urgente", "necesario_para", "creado")))
    columnas = [{"estado": e, "titulo": E(e).label, "pedidos": [p for p in pedidos if p.estado == e],
                 "dir": e == E.AUTORIZACION} for e in reglas.CIRCUITO_OBRA]
    return render(request, "adquisiciones/tablero.html", {
        "columnas": columnas, "filtro": filtro, "obras": _obras_con_pedidos(u), "tipos": Pedido.Tipo.choices,
        "total": len(pedidos), "puede_pedir": _obras_para_pedir(u).exists(),
    })


@permisos.solo_personal
def lista(request):
    _menu(request)
    u = request.user
    qs, filtro = _filtros(request, reglas.visibles(u).prefetch_related("cotizaciones"))
    estado = request.GET.get("estado", "abiertos")
    if estado == "abiertos":
        qs = qs.filter(estado__in=ABIERTOS)
    elif estado in E.values:
        qs = qs.filter(estado=estado)
    filtro["estado"] = estado
    pedidos = _con_montos(u, list(qs.order_by("-creado")[:300]))
    return render(request, "adquisiciones/lista.html", {
        "pedidos": pedidos, "filtro": filtro, "obras": _obras_con_pedidos(u), "tipos": Pedido.Tipo.choices,
        "estados": E.choices, "puede_pedir": _obras_para_pedir(u).exists(),
    })


def _obras_con_pedidos(u):
    ids = reglas.visibles(u).values_list("obra_id", flat=True).distinct()
    return Obra.objects.filter(pk__in=ids).order_by("tipo", "codigo")


@permisos.solo_personal
def nuevo(request):
    _menu(request)
    u = request.user
    obras = _obras_para_pedir(u)
    permisos.exigir(obras.exists())
    inicial = {}
    if request.GET.get("obra", "").isdigit():
        inicial["obra"] = request.GET["obra"]
    elif obras.count() == 1:
        inicial["obra"] = obras.first().pk  # el DT de una sola obra no tiene que elegirla
    form = PedidoForm(request.POST or None, obras=obras, initial=inicial)
    items = ItemsFormSet(request.POST or None, prefix="items")
    adjuntos = AdjuntosForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid() and items.is_valid() and adjuntos.is_valid():
        if not any(f.cleaned_data and not f.cleaned_data.get("DELETE") for f in items.forms):
            messages.error(request, "Cargá al menos un ítem.")
        else:
            permisos.exigir(permisos.puede_crear_pedido(u, form.cleaned_data["obra"]))
            with transaction.atomic():
                pedido = form.save(commit=False)
                pedido.creado_por = u
                pedido.save()
                items.instance = pedido
                items.save()
                _guardar_adjuntos(pedido, adjuntos.cleaned_data["adjuntos"], u)
                reglas.al_crear(pedido, u)
            messages.success(request, f"Se envió el pedido {pedido.codigo} a Compras.")
            return redirect(reglas.url(pedido))
    return render(request, "adquisiciones/form.html", {"form": form, "items": items, "adjuntos": adjuntos,
                                                       "unidades": UNIDADES, "nuevo": True})


@permisos.solo_personal
def editar(request, pk):
    _menu(request)
    p = _pedido(request, pk)
    permisos.exigir(reglas.puede_editar(request.user, p))
    form = PedidoForm(request.POST or None, instance=p, obras=Obra.objects.filter(pk=p.obra_id))
    form.fields["obra"].disabled = True
    items = ItemsFormSet(request.POST or None, instance=p, prefix="items")
    adjuntos = AdjuntosForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid() and items.is_valid() and adjuntos.is_valid():
        with transaction.atomic():
            form.save()
            items.save()
            _guardar_adjuntos(p, adjuntos.cleaned_data["adjuntos"], request.user)
            reglas.anotar(p, request.user, f"{request.user.nombre_completo} corrigió los datos del pedido")
        messages.success(request, "Se guardaron los cambios.")
        return redirect(reglas.url(p))
    return render(request, "adquisiciones/form.html", {"form": form, "items": items, "adjuntos": adjuntos,
                                                       "unidades": UNIDADES, "pedido": p})


def _guardar_adjuntos(pedido, archivos, usuario):
    for a in archivos:
        es_foto = (a.content_type or "").startswith("image/")
        nombre = a.name[:200]
        Adjunto.objects.create(pedido=pedido, archivo=preparar_foto(a) if es_foto else a, nombre=nombre,
                               es_foto=es_foto, subido_por=usuario)


def _proveedores():
    return Contacto.objects.filter(tipo__codigo=TipoContacto.PROVEEDOR).order_by("empresa", "apellido")


@permisos.solo_personal
def pedido(request, pk):
    _menu(request)
    u = request.user
    p = _pedido(request, pk)
    cotizaciones = list(p.cotizaciones.all())
    accion = reglas.accion_actual(p)
    puede_accion = bool(accion) and reglas.puede_hacer(u, p, accion[2])
    puede_cotizar = reglas.puede_cotizar(u, p)
    return render(request, "adquisiciones/pedido.html", {
        "p": p, "pasos": reglas.pasos(p), "items": p.items.all(), "cotizaciones": cotizaciones,
        "adjuntos": p.adjuntos.all(), "recepciones": p.recepciones.select_related("usuario"),
        "movimientos": p.movimientos.select_related("usuario"),
        "ver_montos": permisos.puede_ver_montos_pedido(u, p),
        "accion": accion if puede_accion else None,
        "autorizar": p.estado == E.AUTORIZACION and permisos.puede_autorizar_pedidos(u),
        "puede_editar": reglas.puede_editar(u, p),
        "puede_cotizar": puede_cotizar and len(cotizaciones) < Cotizacion.MAXIMO,
        "puede_elegir": puede_cotizar,
        "form_cot": CotizacionForm(proveedores=_proveedores()) if puede_cotizar else None,
        "form_factura": FacturaForm(), "form_entrega": EntregaForm(), "form_recepcion": RecepcionForm(),
        "maximo": Cotizacion.MAXIMO,
        "ultima_devolucion": p.movimientos.filter(texto__startswith="DIR lo devolvió").first() if p.devuelto else None,
    })


@permisos.solo_personal
@require_POST
def accion(request, pk, codigo):
    p = _pedido(request, pk)
    datos = {k: v for k, v in request.POST.items()}
    try:
        with transaction.atomic():
            if codigo == "factura":
                f = FacturaForm(request.POST, request.FILES)
                if not f.is_valid():
                    raise reglas.NoSePuede(" ".join(e for err in f.errors.values() for e in err))
                datos.update(f.cleaned_data)
            elif codigo == "entrega":
                f = EntregaForm(request.POST)
                if not f.is_valid():
                    raise reglas.NoSePuede("Poné la fecha de entrega.")
                datos.update(f.cleaned_data)
            elif codigo == "recibir":
                f = RecepcionForm(request.POST, request.FILES)
                if not f.is_valid():
                    raise reglas.NoSePuede(" ".join(e for err in f.errors.values() for e in err))
                if not permisos.puede_recibir_pedido(request.user, p) or p.estado != E.RECEPCION:
                    raise reglas.NoSePuede("Esa acción no corresponde en este momento del pedido.")
                r = f.save(commit=False)
                r.pedido, r.usuario = p, request.user
                r.save()
                datos["recepcion"] = r
            reglas.ejecutar(p, codigo, request.user, datos)
    except reglas.NoSePuede as e:
        messages.error(request, str(e))
    else:
        messages.success(request, f"Listo: {p.codigo} quedó en «{p.get_estado_display()}».")
    volver = request.POST.get("volver", "")
    if volver.startswith("/") and not volver.startswith("//"):
        return redirect(volver)
    return redirect(reglas.url(p))


@permisos.solo_personal
@require_POST
def cotizacion(request, pk):
    p = _pedido(request, pk)
    permisos.exigir(reglas.puede_cotizar(request.user, p))
    if p.cotizaciones.count() >= Cotizacion.MAXIMO:
        messages.error(request, f"Ya hay {Cotizacion.MAXIMO} cotizaciones: quitá una para cargar otra.")
        return redirect(reglas.url(p))
    form = CotizacionForm(request.POST, request.FILES, proveedores=_proveedores())
    if form.is_valid():
        c = form.save(commit=False)
        c.pedido, c.cargada_por = p, request.user
        c.proveedor_nombre = form.cleaned_data["proveedor_nombre"]
        if c.archivo:
            c.nombre_archivo = request.FILES["archivo"].name[:200]
        c.elegida = not p.cotizaciones.exists()  # la primera queda elegida; después se puede cambiar
        c.save()
        reglas.anotar(p, request.user, f"{request.user.nombre_completo} cargó la cotización de {c.proveedor_nombre}")
        messages.success(request, f"Se cargó la cotización de {c.proveedor_nombre}.")
    else:
        messages.error(request, " ".join(e for err in form.errors.values() for e in err))
    return redirect(reglas.url(p) + "#cotizaciones")


@permisos.solo_personal
@require_POST
def cotizacion_elegir(request, pk):
    c = get_object_or_404(Cotizacion.objects.select_related("pedido__obra"), pk=pk)
    p = c.pedido
    permisos.exigir(permisos.puede_ver_pedido(request.user, p) and reglas.puede_cotizar(request.user, p))
    p.cotizaciones.update(elegida=False)
    c.elegida = True
    c.save(update_fields=["elegida"])
    reglas.anotar(p, request.user, f"{request.user.nombre_completo} eligió la cotización de {c.proveedor_nombre}")
    return redirect(reglas.url(p) + "#cotizaciones")


@permisos.solo_personal
@require_POST
def cotizacion_quitar(request, pk):
    c = get_object_or_404(Cotizacion.objects.select_related("pedido__obra"), pk=pk)
    p = c.pedido
    permisos.exigir(permisos.puede_ver_pedido(request.user, p) and reglas.puede_cotizar(request.user, p))
    era_elegida = c.elegida
    if c.archivo:
        c.archivo.delete(save=False)
    c.delete()
    if era_elegida:
        otra = p.cotizaciones.first()
        if otra:
            otra.elegida = True
            otra.save(update_fields=["elegida"])
    reglas.anotar(p, request.user, f"{request.user.nombre_completo} quitó la cotización de {c.proveedor_nombre}")
    return redirect(reglas.url(p) + "#cotizaciones")


@permisos.solo_personal
def archivo(request, clase, pk):
    """Los archivos del pedido se ven solo con permiso (nunca por una dirección pública)."""
    if clase == "cotizacion":
        obj = get_object_or_404(Cotizacion.objects.select_related("pedido__obra"), pk=pk)
        p, campo, nombre = obj.pedido, obj.archivo, obj.nombre_archivo
        permisos.exigir(permisos.puede_ver_montos_pedido(request.user, p))
    elif clase == "adjunto":
        obj = get_object_or_404(Adjunto.objects.select_related("pedido__obra"), pk=pk)
        p, campo, nombre = obj.pedido, obj.archivo, obj.nombre
    elif clase == "recepcion":
        obj = get_object_or_404(Recepcion.objects.select_related("pedido__obra"), pk=pk)
        p, campo, nombre = obj.pedido, obj.foto, "remito.jpg"
    elif clase == "factura":
        p = get_object_or_404(Pedido.objects.select_related("obra"), pk=pk)
        campo, nombre = p.factura_archivo, f"factura-{p.codigo}"
        permisos.exigir(permisos.puede_ver_montos_pedido(request.user, p))
    else:
        raise Http404
    permisos.exigir(permisos.puede_ver_pedido(request.user, p))
    if not campo:
        raise Http404
    tipo = mimetypes.guess_type(campo.name)[0] or "application/octet-stream"
    respuesta = FileResponse(campo.open("rb"), content_type=tipo, filename=nombre or None,
                             as_attachment=request.GET.get("descargar") == "1")
    respuesta["Cache-Control"] = "private, max-age=3600"
    return respuesta


# --- Importar de Trello -------------------------------------------------------

SESION_TRELLO = "importar_trello"


def _carpeta_temporal():
    carpeta = Path(settings.MEDIA_ROOT) / "tmp-importar"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


@permisos.solo_personal
def importar(request):
    """Pasa a SOPHIA los pedidos de un tablero de Trello (uno por obra): primero muestra qué va a pasar."""
    _menu(request)
    permisos.exigir(permisos.puede_gestionar_compras(request.user))
    obras = Obra.objects.filter(eliminada=False).order_by("tipo", "codigo")
    if request.method == "POST" and "confirmar" in request.POST:
        pendiente = request.session.pop(SESION_TRELLO, None)
        ruta = _carpeta_temporal() / pendiente["archivo"] if pendiente else None
        if not pendiente or not ruta.exists():
            messages.error(request, "La vista previa venció. Subí el archivo de nuevo.")
            return redirect("adquisiciones:importar")
        obra = get_object_or_404(obras, pk=pendiente["obra"])
        try:
            leido = importar_trello.leer(ruta.read_bytes())
        finally:
            ruta.unlink(missing_ok=True)
        creados = importar_trello.crear(obra, leido["filas"], request.user)
        registrar("pedido.importar", f"Se importaron {creados} pedidos de Trello a {obra.nombre}", obra=obra)
        messages.success(request, f"Se importaron {creados} pedido{'s' if creados != 1 else ''} a {obra.nombre}.")
        return redirect(f"{reverse('adquisiciones:lista')}?obra={obra.pk}&estado=todos")
    form = ImportarTrelloForm(request.POST or None, request.FILES or None, obras=obras)
    leido = obra = None
    ya = set()
    if request.method == "POST" and form.is_valid():
        contenido = form.cleaned_data["archivo"].read()
        try:
            leido = importar_trello.leer(contenido)
        except importar_trello.ArchivoInvalido as e:
            form.add_error("archivo", str(e))
        else:
            obra = form.cleaned_data["obra"]
            nombre = f"{uuid.uuid4().hex}.json"
            (_carpeta_temporal() / nombre).write_bytes(contenido)
            request.session[SESION_TRELLO] = {"archivo": nombre, "obra": obra.pk}
            ya = set(Pedido.objects.filter(obra=obra).exclude(trello_id="").values_list("trello_id", flat=True))
            for f in leido["filas"]:
                f["repetido"] = f["trello_id"] in ya
                f["estado_texto"] = E(f["estado"]).label
    return render(request, "adquisiciones/importar.html", {
        "form": form, "leido": leido, "obra": obra,
        "a_crear": sum(not f["repetido"] for f in (leido or {}).get("filas", [])),
    })
