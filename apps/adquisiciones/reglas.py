"""El circuito del pedido: qué acción corresponde en cada estado, quién la hace y a quién avisa.

Solo se avanza al paso siguiente y nada se compra sin la autorización de DIR. Cada cambio queda en el historial del
pedido y en el registro de actividad, y el que sigue recibe un aviso en la campana de SOPHIA."""

from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.services import registrar
from apps.cuentas import permisos
from apps.cuentas.models import Area, Usuario
from apps.notificaciones.services import avisar

from .models import Movimiento, Pedido, siguiente_oc

E = Pedido.Estado

CIRCUITO_OBRA = [E.PEDIDO, E.COTIZACION, E.ORDEN, E.AUTORIZACION, E.FACTURACION, E.COMPRA, E.LOGISTICA, E.RECEPCION]
CIRCUITO_PROYECTO = [E.PEDIDO, E.AUTORIZACION, E.ORDEN]

# Acciones: (código, texto del botón, quién: "compras" | "dir" | "obra" | "creador_o_compras")
ACCIONES_OBRA = {
    E.PEDIDO: ("cotizar", "Pedir cotizaciones", "compras"),
    E.COTIZACION: ("orden", "Armar orden de compra", "compras"),
    E.ORDEN: ("a_dir", "Enviar a DIR", "compras"),
    E.FACTURACION: ("factura", "Factura recibida", "compras"),
    E.COMPRA: ("comprado", "Compra confirmada", "compras"),
    E.LOGISTICA: ("entrega", "Confirmar entrega", "compras"),
    E.RECEPCION: ("recibir", "Registrar recepción", "obra"),
}
ACCIONES_PROYECTO = {
    E.PEDIDO: ("a_dir", "Enviar a DIR", "creador_o_compras"),
    E.ORDEN: ("emitir", "Emitir orden de compra", "compras"),
}


def circuito(pedido):
    return CIRCUITO_PROYECTO if pedido.es_de_proyecto else CIRCUITO_OBRA


def pasos(pedido):
    """Los pasos del circuito con su situación, para la barra de estado de la ficha."""
    lista = circuito(pedido)
    actual = lista.index(pedido.estado) if pedido.estado in lista else len(lista)
    return [{"nombre": E(e).label, "hecho": i < actual, "actual": i == actual} for i, e in enumerate(lista)]


def accion_actual(pedido):
    if not pedido.abierto:
        return None
    return (ACCIONES_PROYECTO if pedido.es_de_proyecto else ACCIONES_OBRA).get(pedido.estado)


def puede_hacer(u, pedido, quien):
    if quien == "compras":
        return permisos.puede_gestionar_compras(u)
    if quien == "obra":
        return permisos.puede_recibir_pedido(u, pedido)
    if quien == "creador_o_compras":
        return permisos.puede_gestionar_compras(u) or pedido.creado_por_id == u.pk or permisos.esta_asignado(u, pedido.obra)
    return False


def puede_cotizar(u, pedido):
    """Las cotizaciones se cargan mientras se cotiza (y en un proyecto, al cargar el pedido o si DIR lo devolvió)."""
    if pedido.es_de_proyecto:
        return pedido.estado == E.PEDIDO and puede_hacer(u, pedido, "creador_o_compras")
    return pedido.estado in (E.COTIZACION, E.ORDEN) and permisos.puede_gestionar_compras(u)


def puede_editar(u, pedido):
    """Los datos del pedido se corrigen mientras nadie empezó a gestionarlo (o si DIR lo devolvió)."""
    if not pedido.abierto or pedido.estado not in (E.PEDIDO, E.COTIZACION, E.ORDEN):
        return False
    return permisos.puede_gestionar_compras(u) or (pedido.estado == E.PEDIDO and pedido.creado_por_id == u.pk)


# --- A quién se avisa ---------------------------------------------------------

def compras():
    return list(Usuario.objects.filter(gestion_compras=True, is_active=True))


def direccion():
    return list(Usuario.objects.filter(is_active=True, membresias__area__codigo=Area.Codigo.GERENCIA).distinct())


def equipo_obra(pedido):
    """El que cargó el pedido y la Dirección Técnica de la obra."""
    gente = [pedido.creado_por] if pedido.creado_por else []
    gente += [a.usuario for a in pedido.obra.asignaciones.filter(area__codigo=Area.Codigo.DIRECCION_TECNICA)
              .select_related("usuario")]
    return gente


def url(pedido):
    return reverse("adquisiciones:pedido", args=[pedido.pk])


# --- Cambios de estado -------------------------------------------------------

def mover(pedido, hacia, usuario, texto, comentario="", avisos=(), aviso=""):
    desde = pedido.estado
    pedido.estado = hacia
    pedido.estado_desde = timezone.now()
    pedido.save()
    Movimiento.objects.create(pedido=pedido, texto=texto, comentario=comentario, desde=desde, hacia=hacia, usuario=usuario)
    registrar("pedido.estado", f"{pedido.codigo}: {texto}", objeto=pedido, obra=pedido.obra)
    if avisos:
        avisar(avisos, f"{pedido.codigo} · {pedido.titulo}: {aviso or texto}", url(pedido), menos=usuario)


def anotar(pedido, usuario, texto, comentario=""):
    Movimiento.objects.create(pedido=pedido, texto=texto, comentario=comentario, desde=pedido.estado,
                              hacia=pedido.estado, usuario=usuario)


def al_crear(pedido, usuario):
    anotar(pedido, usuario, f"{usuario.nombre_completo} cargó el pedido")
    pedido.estado_desde = timezone.now()
    pedido.save(update_fields=["estado_desde"])
    registrar("pedido.alta", f"Nuevo pedido {pedido.codigo}: {pedido.titulo}", objeto=pedido, obra=pedido.obra)
    urg = " (urgente)" if pedido.urgente else ""
    avisar(compras(), f"Nuevo pedido {pedido.codigo}{urg} · {pedido.obra.nombre}: {pedido.titulo}", url(pedido),
           menos=usuario)


class NoSePuede(Exception):
    pass


def ejecutar(pedido, codigo, usuario, datos):
    """Hace la acción `codigo` sobre el pedido. `datos`: lo que vino del formulario (ya validado en la vista)."""
    nombre = usuario.nombre_completo
    if codigo in ("autorizar", "devolver", "rechazar"):
        if pedido.estado != E.AUTORIZACION or not permisos.puede_autorizar_pedidos(usuario):
            raise NoSePuede("Este pedido no está esperando tu autorización.")
        comentario = datos.get("comentario", "").strip()
        if codigo == "autorizar":
            hacia = E.ORDEN if pedido.es_de_proyecto else E.FACTURACION
            pedido.devuelto = False
            mover(pedido, hacia, usuario, f"DIR autorizó ({nombre})", comentario,
                  compras() + equipo_obra(pedido), "DIR lo autorizó")
            return
        if not comentario:
            raise NoSePuede("Escribí el motivo: el comentario es obligatorio para devolver o rechazar.")
        if codigo == "devolver":
            pedido.devuelto = True
            hacia = E.PEDIDO if pedido.es_de_proyecto else E.ORDEN
            avisos = compras() + ([pedido.creado_por] if pedido.es_de_proyecto else [])
            mover(pedido, hacia, usuario, f"DIR lo devolvió para corregir ({nombre})", comentario, avisos,
                  f"DIR lo devolvió para corregir: «{comentario[:120]}»")
            return
        mover(pedido, E.RECHAZADO, usuario, f"DIR lo rechazó ({nombre})", comentario,
              compras() + equipo_obra(pedido), f"DIR lo rechazó: «{comentario[:120]}»")
        return

    actual = accion_actual(pedido)
    if not actual or actual[0] != codigo or not puede_hacer(usuario, pedido, actual[2]):
        raise NoSePuede("Esa acción no corresponde en este momento del pedido.")

    if codigo == "cotizar":
        pedido.proveedores_consultados = datos.get("proveedores", "").strip()[:300]
        detalle = f": {pedido.proveedores_consultados}" if pedido.proveedores_consultados else ""
        mover(pedido, E.COTIZACION, usuario, f"{nombre} pidió cotizaciones{detalle}", avisos=equipo_obra(pedido),
              aviso="tu pedido está en gestión (se pidieron cotizaciones)")
    elif codigo == "orden":
        if not pedido.elegida:
            raise NoSePuede("Primero cargá las cotizaciones y elegí una.")
        if not pedido.oc_numero:
            pedido.oc_numero = siguiente_oc()
        mover(pedido, E.ORDEN, usuario, f"{nombre} armó la {pedido.oc_numero} con {pedido.elegida.proveedor_nombre}")
    elif codigo == "a_dir":
        if not pedido.elegida:
            raise NoSePuede("Falta la cotización o el presupuesto elegido.")
        reenvio = " (corregido)" if pedido.devuelto else ""
        pedido.devuelto = False
        mover(pedido, E.AUTORIZACION, usuario, f"{nombre} lo envió a autorización de DIR{reenvio}",
              avisos=direccion(), aviso=f"espera tu autorización{reenvio}")
    elif codigo == "emitir":
        if not pedido.oc_numero:
            pedido.oc_numero = siguiente_oc()
        mover(pedido, E.CERRADO, usuario, f"{nombre} emitió la {pedido.oc_numero}", avisos=equipo_obra(pedido),
              aviso=f"se emitió la {pedido.oc_numero}")
    elif codigo == "factura":
        pedido.factura_numero = datos.get("factura_numero", "").strip()[:40]
        if datos.get("factura_archivo"):
            pedido.factura_archivo = datos["factura_archivo"]
        mover(pedido, E.COMPRA, usuario, f"{nombre} cargó la factura {pedido.factura_numero}".strip())
    elif codigo == "comprado":
        mover(pedido, E.LOGISTICA, usuario, f"{nombre} confirmó la compra", avisos=equipo_obra(pedido),
              aviso="ya se compró")
    elif codigo == "entrega":
        if not datos.get("fecha_entrega"):
            raise NoSePuede("Poné la fecha de entrega.")
        pedido.fecha_entrega = datos["fecha_entrega"]
        pedido.entrega_detalle = datos.get("entrega_detalle", "").strip()[:150]
        quien = f" · {pedido.entrega_detalle}" if pedido.entrega_detalle else ""
        mover(pedido, E.RECEPCION, usuario, f"{nombre} confirmó la entrega para el {pedido.fecha_entrega:%d/%m}{quien}",
              avisos=equipo_obra(pedido), aviso=f"llega el {pedido.fecha_entrega:%d/%m}{quien}")
    elif codigo == "recibir":
        recepcion = datos["recepcion"]
        if recepcion.completa:
            mover(pedido, E.CERRADO, usuario, f"{nombre} recibió todo en obra", recepcion.nota, compras(),
                  "se recibió completo en obra")
        else:
            anotar(pedido, usuario, f"{nombre} recibió una parte: falta el resto", recepcion.nota)
            registrar("pedido.parcial", f"{pedido.codigo}: entrega parcial", objeto=pedido, obra=pedido.obra)
            avisar(compras() + direccion(), f"{pedido.codigo} · {pedido.titulo}: entrega parcial, falta el resto",
                   url(pedido), menos=usuario)


# --- Consultas ----------------------------------------------------------------

def visibles(u):
    qs = Pedido.objects.filter(obra__eliminada=False).select_related("obra", "creado_por")
    if permisos.ve_todos_los_pedidos(u):
        return qs
    return qs.filter(obra__asignaciones__usuario=u).distinct()


def pendientes_de(u):
    """Lo que le toca mover a esta persona ahora."""
    qs = visibles(u).exclude(estado__in=[E.CERRADO, E.RECHAZADO]).prefetch_related("cotizaciones")
    mios = []
    for p in qs:
        if p.estado == E.AUTORIZACION:
            if permisos.puede_autorizar_pedidos(u):
                mios.append(p)
            continue
        accion = accion_actual(p)
        if not accion:
            continue
        if accion[2] == "obra":
            if permisos.esta_asignado(u, p.obra):
                mios.append(p)
        elif puede_hacer(u, p, accion[2]) and not (accion[2] == "compras" and permisos.es_gerencia(u)
                                                    and not permisos.es_compras(u)):
            mios.append(p)
    return mios


def esperando_dir():
    return (Pedido.objects.filter(estado=E.AUTORIZACION, obra__eliminada=False)
            .select_related("obra").prefetch_related("cotizaciones").order_by("estado_desde"))


def busqueda(qs, q):
    return qs.filter(Q(titulo__icontains=q) | Q(codigo__icontains=q) | Q(obra__nombre__icontains=q)
                     | Q(items__descripcion__icontains=q)).distinct()
