"""Importar un certificado de avance de obra desde Excel (formato del contratista: rubros, ítems con unidad,
cantidad, precio y avance acumulado, y al final el resumen de montos).

El certificado manda: el listado de tareas de la obra queda igual al del Excel. Las filas que ya existían
(mismo código y nombre) se actualizan en su lugar, así conservan su historial de avance.
"""

import re
import unicodedata
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.plantillas import arbol

from . import avances
from .models import AvanceTarea, Certificado, TareaObra

T = TareaObra.Tipo
CIEN = Decimal(100)
MINIMA = Decimal("0.001")  # incidencia de lo que todavía no tiene precio: no pesa, pero el editor la acepta

# Renglones del resumen final que se guardan (empiezan con estos textos, sin importar mayúsculas).
RESUMEN = ("SUBTOTAL", "ACTUALIZACIONES", "FONDO DE REPARO", "IVA", "MATERIALES", "ANTICIPOS", "DEVOLUCION",
           "DEVOLUCIÓN", "TOTAL")


def _texto(valor):
    return re.sub(r"\s+", " ", str(valor)).strip() if valor is not None else ""


def _clave(texto):
    """Para comparar nombres sin acentos, mayúsculas ni espacios de más."""
    texto = unicodedata.normalize("NFKD", _texto(texto)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def _numero(valor):
    if isinstance(valor, bool) or valor is None:
        return None
    if isinstance(valor, (int, float)):
        return Decimal(str(valor))
    try:
        return Decimal(_texto(valor).replace(".", "").replace(",", "."))
    except Exception:
        return None


def _dinero(valor):
    n = _numero(valor)
    return n.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if n is not None else None


def _codigo(valor):
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return _texto(valor).replace(",", ".").rstrip(".")


def _columnas(fila):
    """Ubica cada dato por el título de su columna. Los títulos de avance se repiten: el primer ACUM es el
    porcentaje y el segundo, el monto."""
    col = {}
    for i, v in enumerate(fila):
        t = _clave(v)
        if t in ("n", "no", "nro", "numero"):
            col.setdefault("codigo", i)
        elif t == "item":
            col["nombre"] = i
        elif t in ("un", "unidad"):
            col["unidad"] = i
        elif t == "cantidad":
            col["cantidad"] = i
        elif t == "pu mo":
            col["precio_unitario"] = i
        elif t == "pf mo":
            col["monto"] = i
        elif t.startswith("precio final"):
            # Puede haber material, mano de obra y total: el certificado es de mano de obra.
            if t == "precio final mo" or "monto_rubro" not in col:
                col["monto_rubro"] = i
        elif t == "acum":
            col["acumulado" if "avance" in col else "avance"] = i
        elif t == "actual":
            col["actual" if "actual_pct" in col else "actual_pct"] = i
    return col


def _sin_certificado(etiqueta):
    """«SUBTOTAL - CERTIFICADO N° 04- 091026» → «SUBTOTAL»."""
    return re.sub(r"\s*-?\s*CERTIFICADO\s*N.*$", "", _texto(etiqueta), flags=re.I).strip(" -")


def _repartir(montos):
    """Incidencias (que suman 100) proporcionales a los montos. Lo que no tiene monto lleva la mínima; si nada
    tiene monto, se reparte en partes iguales."""
    if not montos:
        return []
    total = sum((m for m in montos if m and m > 0), Decimal(0))
    if total <= 0:
        partes = [CIEN / len(montos)] * len(montos)
    else:
        partes = [(m * CIEN / total) if m and m > 0 else Decimal(0) for m in montos]
    partes = [max(p.quantize(MINIMA, rounding=ROUND_HALF_UP), MINIMA) for p in partes]
    mayor = max(range(len(partes)), key=lambda i: partes[i])
    partes[mayor] += CIEN - sum(partes)
    return partes


def leer(archivo):
    """Lee el Excel y devuelve {"numero", "fecha", "obra", "rubros": [...], "presupuesto", "acumulado",
    "periodo", "saldo", "resumen": [[concepto, monto], ...]}. Lanza ValidationError si no se entiende."""
    import openpyxl

    try:
        libro = openpyxl.load_workbook(archivo, data_only=True, read_only=True)
    except Exception:
        raise ValidationError("No se pudo abrir el archivo. Tiene que ser un Excel (.xlsx).")
    # Si el Excel tiene varias pestañas, se usa la del certificado: primero las que se llaman «certificado…», y
    # de todas, la primera que tenga la fila de títulos con la columna de avance acumulado (ACUM).
    hojas = sorted(libro.worksheets, key=lambda h: "certif" not in _clave(h.title))
    filas = encabezado = None
    for hoja in hojas:
        candidatas = [list(f) for f in hoja.iter_rows(values_only=True)]
        fila = next((i for i, f in enumerate(candidatas)
                     if {"item", "cantidad", "acum"} <= {_clave(v) for v in f}), None)
        if fila is not None:
            filas, encabezado = candidatas, fila
            break
    libro.close()
    if encabezado is None:
        raise ValidationError("No encontré en ninguna pestaña la fila de títulos del certificado (Nº, ITEM, UN., "
                              "CANTIDAD… y AVANCE ACUM). ¿Es un certificado de obra?")
    col = _columnas(filas[encabezado])
    faltan = [n for n in ("codigo", "nombre", "unidad", "cantidad", "monto", "avance") if n not in col]
    if faltan:
        raise ValidationError(f"Al certificado le faltan columnas: {', '.join(faltan)}.")

    def dato(fila, nombre):
        i = col.get(nombre)
        return fila[i] if i is not None and i < len(fila) else None

    resultado = {"numero": None, "fecha": None, "obra": "", "rubros": [], "resumen": [],
                 "presupuesto": None, "acumulado": None, "periodo": None, "saldo": None}
    for f in filas:  # el número y la fecha pueden estar en el título o en los renglones del final
        for v in f:
            t = _texto(v)
            m = re.search(r"CERTIFICADO\s*N\s*[°º]?\s*(\d+)\s*-?\s*(\d{2})(\d{2})(\d{2})\b", t, re.I)
            if m and resultado["numero"] is None:
                resultado["numero"] = int(m.group(1))
                try:
                    resultado["fecha"] = date(2000 + int(m.group(4)), int(m.group(3)), int(m.group(2)))
                except ValueError:
                    pass
            if t.upper().startswith("OBRA:") and not resultado["obra"]:
                resultado["obra"] = t[5:].strip(" -")

    rubros, rubro, subgrupo = resultado["rubros"], None, None
    i = encabezado + 1
    for i in range(encabezado + 1, len(filas)):
        f = filas[i]
        nombre, codigo, unidad = _texto(dato(f, "nombre")), _codigo(dato(f, "codigo")), _texto(dato(f, "unidad"))
        if nombre.upper().startswith("SUBTOTAL"):
            resultado["presupuesto"] = _dinero(dato(f, "monto_rubro"))
            resultado["acumulado"] = _dinero(dato(f, "acumulado"))
            periodo = _dinero(dato(f, "actual"))
            if periodo is not None:  # en algunas planillas este mismo renglón trae lo certificado en el período
                resultado["periodo"] = periodo
                resultado["resumen"].append([_sin_certificado(nombre) or "SUBTOTAL", str(periodo)])
            break
        if not nombre:
            continue
        if not unidad and "." not in codigo:
            rubro = {"tipo": T.RUBRO, "codigo": codigo, "nombre": nombre, "unidad": "", "cantidad": None,
                     "monto": _dinero(dato(f, "monto_rubro")), "hijos": []}
            rubros.append(rubro)
            subgrupo = None
            continue
        if rubro is None:
            continue
        if not unidad:  # subgrupo (ej. 1.9 MEDIANERAS): sus ítems van al rubro con el nombre adelante
            subgrupo = (codigo, nombre.capitalize())
            continue
        if subgrupo and not codigo.startswith(subgrupo[0] + "."):
            subgrupo = None
        destino = rubro
        cabeza = codigo.split(".")[0]
        if cabeza and cabeza != rubro["codigo"]:  # ítem fuera de lugar (ej. 11.6 debajo del 17): va a su rubro
            destino = next((r for r in reversed(rubros) if r["codigo"] == cabeza), rubro)
        avance = _numero(dato(f, "avance")) or Decimal(0)
        destino["hijos"].append({
            "tipo": T.ITEM, "codigo": codigo, "unidad": unidad[:15],
            "nombre": f"{subgrupo[1]}: {nombre}" if subgrupo else nombre,
            "cantidad": arbol._cantidad(dato(f, "cantidad")),
            "precio_unitario": _dinero(dato(f, "precio_unitario")), "monto": _dinero(dato(f, "monto")),
            "monto_certificado": _dinero(dato(f, "acumulado")),
            "avance": int((max(Decimal(0), min(Decimal(1), avance)) * CIEN).quantize(Decimal(1), rounding=ROUND_HALF_UP)),
            "hijos": [],
        })
    else:
        raise ValidationError("No encontré la fila SUBTOTAL que cierra el listado de rubros.")

    for f in filas[i + 1:]:
        etiqueta = next((_texto(v) for v in f if isinstance(v, str) and _texto(v)), "")
        monto = _dinero(dato(f, "actual"))
        if not etiqueta or monto is None or not etiqueta.upper().startswith(RESUMEN):
            continue
        etiqueta = _sin_certificado(etiqueta)
        resultado["resumen"].append([etiqueta, str(monto)])
        clave = etiqueta.upper()
        if re.match(r"SUBTOTAL\s+1\b", clave) and resultado["periodo"] is None:
            resultado["periodo"] = monto
        if clave.startswith("TOTAL"):
            resultado["saldo"] = monto

    if not rubros:
        raise ValidationError("El certificado no tiene rubros.")
    items = [h for r in rubros for h in r["hijos"]]
    if resultado["presupuesto"] is None:
        resultado["presupuesto"] = sum((h["monto"] or Decimal(0) for h in items), Decimal(0))
    if resultado["acumulado"] is None and any(h["monto_certificado"] is not None for h in items):
        resultado["acumulado"] = sum((h["monto_certificado"] or Decimal(0) for h in items), Decimal(0))
    # Incidencias por monto: cada rubro sobre el total y cada ítem sobre su rubro.
    for r, inc in zip(rubros, _repartir([r["monto"] or sum((h["monto"] or 0 for h in r["hijos"]), Decimal(0)) for r in rubros])):
        r["incidencia"] = inc
        for h, inc_h in zip(r["hijos"], _repartir([h["monto"] for h in r["hijos"]])):
            h["incidencia"] = inc_h
        if not r["hijos"]:
            r["avance"] = 0
    return resultado


@transaction.atomic
def aplicar(obra, datos, usuario, numero=None, fecha=None, archivo=None):
    """Deja las tareas de la obra como dice el certificado, guarda el certificado y anota los avances en el
    historial con la fecha del certificado. Devuelve el Certificado creado."""
    numero = numero or datos["numero"]
    fecha = fecha or datos["fecha"]
    if not numero or not fecha:
        raise ValidationError("Indicá el número y la fecha del certificado.")
    if obra.certificados.filter(numero=numero).exists():
        raise ValidationError(f"El certificado N° {numero} ya está cargado en esta obra.")

    estaba_vacia = not obra.tareas.exists()
    # Reusa las filas existentes con el mismo código y nombre: así conservan su historial.
    libres = {}
    for t in obra.tareas.all():
        libres.setdefault((t.tipo, t.codigo, _clave(t.nombre)), []).append(t.pk)

    def asignar(lista):
        for d in lista:
            ids = libres.get((d["tipo"], d["codigo"], _clave(d["nombre"])))
            d["id"] = ids.pop(0) if ids else None
            asignar(d["hijos"])

    asignar(datos["rubros"])
    antes = arbol.guardar(TareaObra, {"obra": obra}, datos["rubros"], con_avance=True)

    certificado = Certificado.objects.create(
        obra=obra, numero=numero, fecha=fecha, presupuesto=datos["presupuesto"], acumulado=datos["acumulado"],
        periodo=datos["periodo"], saldo=datos["saldo"], resumen=datos["resumen"], cargado_por=usuario,
        **({"archivo": archivo} if archivo else {}))
    for tarea in obra.tareas.filter(hijos__isnull=True):
        if estaba_vacia:
            # Carga inicial: no se sabe cuándo empezó lo que ya traía avance.
            if tarea.avance:
                AvanceTarea.objects.create(tarea=tarea, obra=obra, fecha=fecha, anterior=None, avance=tarea.avance,
                                           origen=AvanceTarea.Origen.CERTIFICADO, certificado=certificado,
                                           usuario=usuario)
        else:
            previo = antes.get(tarea.pk)
            avances.registrar(tarea, previo or 0, tarea.avance, usuario, fecha, AvanceTarea.Origen.CERTIFICADO,
                              certificado)
    obra.recalcular_avance()
    return certificado
