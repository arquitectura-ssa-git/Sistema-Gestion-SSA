"""Pasa a SOPHIA los pedidos de un tablero de Trello exportado como JSON (Menú del tablero → Imprimir, exportar y
compartir → Exportar como JSON). Un tablero por obra. Cada tarjeta abierta es un pedido; la lista donde está define
el estado; la descripción, los ítems; los comentarios, el historial. No se repite una tarjeta ya importada."""

import json
import re
from datetime import datetime, timezone as tz
from decimal import Decimal, InvalidOperation

from django.utils.dateparse import parse_datetime

from .models import ItemPedido, Movimiento, Pedido

E = Pedido.Estado

UNIDADES = {"m", "m2", "m²", "m3", "m³", "ml", "kg", "kgs", "t", "tn", "lt", "lts", "l", "u", "un", "unid", "unidad",
            "unidades", "bolsa", "bolsas", "par", "pares", "rollo", "rollos", "caja", "cajas", "barra", "barras",
            "balde", "baldes", "litro", "litros", "metro", "metros", "kilo", "kilos", "lata", "latas", "placa", "placas", "pack", "global", "gl", "camion", "camión", "viaje"}
ENCABEZADOS = ("listado de materiales", "materiales y/o recursos")
LINEA = re.compile(r"^\s*[-•*]?\s*(\d+(?:[.,]\d+)?)\s*(?:x\s+)?(.+)$", re.I)
PREFIJO = re.compile(r"^\s*REQ\.?\s*N?[º°o]?\s*\.?\s*(\d+)\s*[-–:.]?\s*", re.I)


MARKDOWN_IMAGEN = re.compile(r"!\[[^\]]*\]\([^)]*\)")
MARKDOWN_ENLACE = re.compile(r"\[([^\]]*)\]\((https?://[^)]*)\)")


def limpiar(texto):
    """Los comentarios de Trello traen imágenes y enlaces en formato markdown: quedan legibles."""
    texto = MARKDOWN_IMAGEN.sub("(imagen en Trello)", texto)
    texto = MARKDOWN_ENLACE.sub(lambda m: m.group(2) if m.group(1) == m.group(2) else f"{m.group(1)} ({m.group(2)})", texto)
    return texto.replace("\\-", "-").strip()


class ArchivoInvalido(Exception):
    pass


def estado_de_lista(nombre):
    n = nombre.upper()
    reglas = [("MAL", E.RECHAZADO), ("COTIZ", E.COTIZACION), ("AUTORIZ", E.AUTORIZACION), ("LOGIST", E.LOGISTICA),
              ("RECEPCI", E.RECEPCION), ("FINALIZ", E.CERRADO), ("CIERRE", E.CERRADO), ("FACTUR", E.FACTURACION),
              ("ORDEN", E.ORDEN), ("COMPRA", E.COMPRA)]
    return next((estado for clave, estado in reglas if clave in n), E.PEDIDO)


def items_de(descripcion):
    items = []
    for linea in (descripcion or "").splitlines():
        texto = linea.strip().strip("*").strip()
        if not texto or any(e in texto.lower() for e in ENCABEZADOS) or not re.search(r"\w", texto):
            continue
        m = LINEA.match(texto)
        cantidad, unidad, desc = None, "", texto
        if m:
            try:
                cantidad = Decimal(m.group(1).replace(",", "."))
            except InvalidOperation:
                cantidad = None
            desc = m.group(2).strip()
            primera = desc.split(" ", 1)
            if len(primera) == 2 and primera[0].lower().strip(".") in UNIDADES:
                unidad, desc = primera[0].strip(".").lower(), re.sub(r"^de\s+", "", primera[1].strip(), flags=re.I)
        items.append({"descripcion": desc[:200], "cantidad": cantidad, "unidad": unidad[:20]})
    return items[:100]


def _fecha(texto):
    d = parse_datetime(texto) if texto else None
    return d


def _creada(card_id):
    try:
        return datetime.fromtimestamp(int(card_id[:8], 16), tz=tz.utc)
    except (ValueError, TypeError):
        return None


def leer(contenido):
    try:
        datos = json.loads(contenido)
        listas = {l["id"]: l.get("name", "") for l in datos["lists"]}
        tarjetas = datos["cards"]
    except (ValueError, KeyError, TypeError):
        raise ArchivoInvalido("No es un tablero de Trello exportado como JSON.")
    comentarios, adjuntos = {}, {}
    for a in datos.get("actions", []):
        if a.get("type") == "commentCard":
            card = (a.get("data") or {}).get("card", {}).get("id")
            texto = (a.get("data") or {}).get("text", "")
            autor = (a.get("memberCreator") or {}).get("fullName", "")
            if card and texto:
                comentarios.setdefault(card, []).append({"fecha": _fecha(a.get("date")), "autor": autor,
                                                         "texto": limpiar(texto)[:2000]})
    filas = []
    for c in tarjetas:
        if c.get("closed"):
            continue
        nombre = c.get("name", "").strip() or "Pedido sin nombre"
        m = PREFIJO.match(nombre)
        referencia = f"REQ {m.group(1)}" if m else ""
        titulo = (PREFIJO.sub("", nombre).strip(" -–") or nombre)[:150]
        lista = listas.get(c.get("idList"), "")
        adj = [{"nombre": x.get("name", "")[:120], "url": x.get("url", "")} for x in c.get("attachments", [])]
        filas.append({
            "trello_id": c.get("id", ""), "titulo": titulo, "referencia": referencia, "lista": lista,
            "estado": estado_de_lista(lista), "items": items_de(c.get("desc", "")),
            "necesario_para": (_fecha(c.get("due")).date() if c.get("due") else None),
            "creada": _creada(c.get("id", "")), "url": c.get("shortUrl") or c.get("url", ""),
            "comentarios": sorted(comentarios.get(c.get("id"), []), key=lambda x: x["fecha"] or datetime.min.replace(tzinfo=tz.utc)),
            "adjuntos": adj,
        })
    return {"tablero": datos.get("name", ""), "filas": filas}


def crear(obra, filas, usuario):
    ya = set(Pedido.objects.filter(obra=obra).exclude(trello_id="").values_list("trello_id", flat=True))
    creados = 0
    for f in filas:
        if f["trello_id"] in ya:
            continue
        nota = [f"Importado de Trello ({f['lista']})" + (f" · {f['referencia']}" if f["referencia"] else "")]
        if f["url"]:
            nota.append(f"Tarjeta: {f['url']}")
        if f["adjuntos"]:
            nota.append("Adjuntos en Trello: " + " · ".join(f"{a['nombre']} ({a['url']})" for a in f["adjuntos"]))
        p = Pedido.objects.create(obra=obra, titulo=f["titulo"], estado=f["estado"], necesario_para=f["necesario_para"],
                                  nota="\n".join(nota), trello_id=f["trello_id"])
        ItemPedido.objects.bulk_create(ItemPedido(pedido=p, **i) for i in f["items"])
        m = Movimiento.objects.create(pedido=p, texto=f"Importado de Trello (estaba en «{f['lista']}»)", usuario=usuario,
                                      hacia=p.estado)
        for c in f["comentarios"]:
            mc = Movimiento.objects.create(pedido=p, texto=f"Comentario en Trello de {c['autor'] or 'alguien'}",
                                           comentario=c["texto"], hacia=p.estado)
            if c["fecha"]:
                Movimiento.objects.filter(pk=mc.pk).update(fecha=c["fecha"])
        if f["creada"]:
            Pedido.objects.filter(pk=p.pk).update(creado=f["creada"], estado_desde=f["creada"])
            Movimiento.objects.filter(pk=m.pk).update(fecha=f["creada"])
        creados += 1
    return creados
