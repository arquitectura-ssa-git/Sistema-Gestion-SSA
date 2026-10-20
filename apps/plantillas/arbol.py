"""Listados de tareas en árbol: etapas → rubros → ítems.

Cada nodo tiene una incidencia relativa a sus hermanos. Al guardar se normalizan para que cada
grupo sume 100%, así agregar o quitar filas nunca deja el total descuadrado. El avance se carga en
las hojas; el de cada rama es el promedio ponderado de sus hijos.

El editor de pantalla trabaja con una lista de diccionarios:
    {"id": 12, "tipo": "rubro", "nombre": "...", "incidencia": 25.0, "avance": 40, "hijos": [...]}
"""

from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError

from .models import NodoTarea

T = NodoTarea.Tipo
HIJO_VALIDO = {None: {T.ETAPA, T.RUBRO}, T.ETAPA: {T.RUBRO}, T.RUBRO: {T.ITEM}, T.ITEM: set()}
CIEN = Decimal(100)
MAX_NODOS = 500


# --- Lectura -----------------------------------------------------------------

def armar(nodos):
    """De una lista plana de nodos (con padre_id) a una lista de raíces, cada una con `.hijos_lista`."""
    por_padre = {}
    for n in sorted(nodos, key=lambda n: (n.orden, n.id or 0)):
        por_padre.setdefault(n.padre_id, []).append(n)
    for n in nodos:
        n.hijos_lista = por_padre.get(n.id, [])
    return por_padre.get(None, [])


def _avance(nodo):
    if not nodo.hijos_lista:
        return Decimal(getattr(nodo, "avance", 0) or 0)
    return _promedio(nodo.hijos_lista)


def _promedio(hermanos):
    total = sum((h.incidencia for h in hermanos), Decimal(0))
    if total <= 0:
        return Decimal(0)
    return sum((h.incidencia * _avance(h) for h in hermanos), Decimal(0)) / total


def avance_total(nodos):
    """Avance (0-100, Decimal) del listado completo."""
    return _promedio(armar(list(nodos)))


def anotar(nodos):
    """Arma el árbol y le agrega a cada nodo: numero ('3', '3.2'), peso_total (% del total) y avance_calculado."""
    raices = armar(list(nodos))
    contador = {"rubro": 0}

    def recorrer(hermanos, peso_padre, numero_rubro=None):
        suma = sum((h.incidencia for h in hermanos), Decimal(0)) or Decimal(1)
        for i, n in enumerate(hermanos, start=1):
            n.peso_total = peso_padre * n.incidencia / suma
            n.avance_calculado = _avance(n)
            if n.tipo == T.RUBRO:
                contador["rubro"] += 1
                n.numero = str(contador["rubro"])
            elif n.tipo == T.ITEM:
                n.numero = f"{numero_rubro}.{i}"
            else:
                n.numero = ""
            recorrer(n.hijos_lista, n.peso_total, n.numero if n.tipo == T.RUBRO else numero_rubro)

    recorrer(raices, CIEN)
    return raices


def a_datos(nodos, con_avance=False):
    """Árbol listo para el editor de pantalla (JSON)."""

    def convertir(n):
        d = {"id": n.id, "tipo": n.tipo, "nombre": n.nombre, "incidencia": float(n.incidencia),
             "hijos": [convertir(h) for h in n.hijos_lista]}
        if con_avance:
            d["avance"] = int(getattr(n, "avance", 0) or 0)
        return d

    return [convertir(n) for n in armar(list(nodos))]


# --- Escritura ---------------------------------------------------------------

def validar(datos, con_avance=False):
    """Revisa lo que manda el editor y lo devuelve limpio. Lanza ValidationError con mensajes legibles."""
    if not isinstance(datos, list):
        raise ValidationError("El listado de tareas llegó mal armado. Recargá la página y probá de nuevo.")
    errores, cuenta = [], [0]

    def limpiar(lista, tipo_padre, ruta):
        limpios = []
        for d in lista:
            cuenta[0] += 1
            if not isinstance(d, dict):
                errores.append("Hay una fila mal armada.")
                continue
            tipo = d.get("tipo")
            nombre = str(d.get("nombre") or "").strip()[:300]
            donde = f"{ruta} › {nombre}" if ruta else nombre
            if tipo not in HIJO_VALIDO[tipo_padre]:
                errores.append(f"«{nombre or 'sin nombre'}» no puede ir ahí.")
                continue
            if not nombre:
                errores.append(f"Hay {dict(T.choices)[tipo].lower()} sin nombre{f' en {ruta}' if ruta else ''}.")
            try:
                incidencia = Decimal(str(d.get("incidencia")))
            except Exception:
                incidencia = Decimal(0)
            if not incidencia.is_finite() or incidencia <= 0:
                errores.append(f"«{donde}» tiene que tener una incidencia mayor a 0%.")
                incidencia = Decimal(1)
            nodo = {"tipo": tipo, "nombre": nombre, "incidencia": incidencia,
                    "hijos": limpiar(d.get("hijos") or [], tipo, donde)}
            if con_avance:
                try:
                    nodo["avance"] = max(0, min(100, int(round(float(d.get("avance") or 0)))))
                except (TypeError, ValueError):
                    nodo["avance"] = 0
            if tipo == T.ETAPA and not nodo["hijos"]:
                errores.append(f"La etapa «{nombre}» no tiene rubros: agregale al menos uno o quitala.")
            limpios.append(nodo)
        return limpios

    limpio = limpiar(datos, None, "")
    if cuenta[0] > MAX_NODOS:
        errores.append(f"El listado tiene más de {MAX_NODOS} filas.")
    if errores:
        raise ValidationError(list(dict.fromkeys(errores)))
    return limpio


def normalizar(hermanos):
    """Incidencias de un grupo llevadas a sumar exactamente 100 (con 3 decimales)."""
    total = sum((h["incidencia"] for h in hermanos), Decimal(0))
    if not hermanos or total <= 0:
        return
    acumulado = Decimal(0)
    for h in hermanos[:-1]:
        h["incidencia"] = (h["incidencia"] * CIEN / total).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        acumulado += h["incidencia"]
    hermanos[-1]["incidencia"] = max(CIEN - acumulado, Decimal("0.001"))


def guardar(modelo, dueño, datos, con_avance=False):
    """Reemplaza el listado de `dueño` (ej. {"plantilla": p} u {"obra": o}) por `datos` ya validados."""
    modelo.objects.filter(**dueño).delete()

    def crear(lista, padre):
        normalizar(lista)
        for orden, d in enumerate(lista):
            extra = {"avance": d.get("avance", 0)} if con_avance else {}
            nodo = modelo.objects.create(tipo=d["tipo"], nombre=d["nombre"], incidencia=d["incidencia"],
                                         orden=orden, padre=padre, **dueño, **extra)
            crear(d["hijos"], nodo)

    crear(datos, None)


def copiar(nodos_origen, modelo, dueño):
    """Copia un listado (ej. de una plantilla) a otro dueño, con el avance en 0."""
    datos = a_datos(nodos_origen)

    def a_validos(lista):
        return [{"tipo": d["tipo"], "nombre": d["nombre"], "incidencia": Decimal(str(d["incidencia"])),
                 "avance": 0, "hijos": a_validos(d["hijos"])} for d in lista]

    guardar(modelo, dueño, a_validos(datos), con_avance=hasattr(modelo, "avance"))
