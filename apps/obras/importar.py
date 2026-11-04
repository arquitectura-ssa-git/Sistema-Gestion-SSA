"""Carga de varios proyectos de una vez desde la planilla modelo («Carga de proyectos - SOPHIA.xlsx»).

Primero se lee y se muestra qué va a pasar con cada fila (`leer`); recién con el OK se crean (`crear`).
Los nombres que ya existen no se duplican y los códigos repetidos se reemplazan por uno automático.
"""

import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction
from openpyxl import load_workbook

from apps.auditoria.services import registrar
from apps.plantillas import arbol

from .models import Obra, TareaObra

COLUMNAS = {
    "nombre": "nombre", "codigo": "codigo", "direccion": "direccion", "localidad": "localidad",
    "superficie": "superficie_m2", "etapa": "etapa", "estado": "estado", "fecha de inicio": "fecha_inicio",
    "descripcion": "descripcion", "tipo": "uso",
}
LARGOS = {"nombre": 200, "direccion": 200, "localidad": 100}
ESTADOS = {"activo": Obra.Estado.ACTIVA, "activa": Obra.Estado.ACTIVA, "standby": Obra.Estado.PAUSADA,
           "pausada": Obra.Estado.PAUSADA, "suspendido": Obra.Estado.PAUSADA, "superado": Obra.Estado.FINALIZADA,
           "finalizada": Obra.Estado.FINALIZADA, "terminado": Obra.Estado.FINALIZADA}


class PlanillaInvalida(Exception):
    pass


def _clave(texto):
    """'Pre Anteproyecto' → 'preanteproyecto'; 'Stand by (suspendido…)' → 'standby'."""
    texto = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().lower()
    texto = texto.split("(")[0]
    return "".join(c for c in texto if c.isalnum())


ETAPAS = {_clave(v): v for v, _ in Obra.Etapa.choices} | {_clave(t): v for v, t in Obra.Etapa.choices}
USOS = {_clave(v): v for v, _ in Obra.Uso.choices} | {_clave(t): v for v, t in Obra.Uso.choices}
USOS |= {"residencialcolectiva": Obra.Uso.RESIDENCIAL, "vivienda": Obra.Uso.RESIDENCIAL,
         "urbanizacion": Obra.Uso.URBANIZACION, "edificioenaltura": Obra.Uso.ALTURA, "otro": Obra.Uso.OTROS}
ETAPAS |= {"enejecucion": Obra.Etapa.EJECUCION, "ejecucion": Obra.Etapa.EJECUCION,
           "proyectoejecutivo": Obra.Etapa.EJECUTIVO, "preante": Obra.Etapa.PRE_ANTEPROYECTO}


def _texto(valor):
    return " ".join(str(valor).split()) if valor not in (None, "") else ""


def _fecha(valor):
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = _texto(valor)
    for formato in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            pass
    raise ValueError


def _superficie(valor):
    if isinstance(valor, (int, float)):
        return Decimal(str(valor)).quantize(Decimal("0.01"))
    texto = _texto(valor).lower().replace("m2", "").replace("m²", "").strip()
    # «1.250,5» (como se escribe acá) o «1250.5»
    texto = texto.replace(".", "").replace(",", ".") if "," in texto else texto
    return Decimal(texto).quantize(Decimal("0.01"))


def _leer_filas(archivo):
    try:
        libro = load_workbook(archivo, read_only=True, data_only=True)
    except Exception as e:  # archivo dañado o que no es Excel
        raise PlanillaInvalida("No se pudo abrir el archivo. ¿Es la planilla de Excel (.xlsx)?") from e
    hoja = next((libro[n] for n in libro.sheetnames if _clave(n) == "proyectos"), libro.worksheets[0])
    filas = hoja.iter_rows(values_only=True)
    encabezado = next(filas, None) or ()
    columnas = {}
    for i, titulo in enumerate(encabezado):
        nombre = " ".join(str(titulo or "").replace("*", "").split("(")[0].split()).lower()
        nombre = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
        if nombre in COLUMNAS:
            columnas[COLUMNAS[nombre]] = i
    if "nombre" not in columnas:
        raise PlanillaInvalida("No encontré la columna «Nombre». Usá la planilla modelo, sin cambiar los títulos.")
    for numero, valores in enumerate(filas, start=2):
        yield numero, {campo: (valores[i] if i < len(valores) else None) for campo, i in columnas.items()}


def leer(archivo):
    """Devuelve una fila por proyecto con sus datos limpios, la acción («crear» o «saltear») y los avisos."""
    existentes = {_clave(n) for n in Obra.objects.filter(tipo=Obra.Tipo.PROYECTO).values_list("nombre", flat=True)}
    codigos = {c.lower() for c in Obra.objects.values_list("codigo", flat=True)}
    resultado = []
    for numero, crudo in _leer_filas(archivo):
        nombre = _texto(crudo.get("nombre"))
        if not any(_texto(v) for v in crudo.values()) or "borrar esta fila" in nombre.lower():
            continue
        fila = {"fila": numero, "nombre": nombre, "accion": "crear", "avisos": []}
        avisos = fila["avisos"]
        if not nombre:
            fila.update(accion="saltear", motivo="Falta el nombre")
            resultado.append(fila)
            continue
        if _clave(nombre) in existentes:
            fila.update(accion="saltear", motivo="Ya existe un proyecto con ese nombre")
            resultado.append(fila)
            continue
        existentes.add(_clave(nombre))

        for campo, largo in LARGOS.items():
            valor = nombre if campo == "nombre" else _texto(crudo.get(campo))
            if len(valor) > largo:
                avisos.append(f"{campo.capitalize()} recortado a {largo} letras")
            fila[campo] = valor[:largo]
        fila["descripcion"] = str(crudo.get("descripcion") or "").strip()

        codigo = _texto(crudo.get("codigo"))
        if codigo and len(codigo) > 20:
            avisos.append(f"El código «{codigo}» es muy largo (máx. 20): se genera uno automático")
            codigo = ""
        elif codigo and codigo.lower() in codigos:
            avisos.append(f"El código «{codigo}» ya está usado: se genera uno automático")
            codigo = ""
        if codigo:
            codigos.add(codigo.lower())
        fila["codigo"] = codigo

        etapa = _texto(crudo.get("etapa"))
        fila["etapa"] = ETAPAS.get(_clave(etapa), Obra.Etapa.ANTEPROYECTO)
        if etapa and _clave(etapa) not in ETAPAS:
            avisos.append(f"Etapa «{etapa}» desconocida: queda Anteproyecto")

        uso = _texto(crudo.get("uso"))
        fila["uso"] = USOS.get(_clave(uso), "")
        if uso and not fila["uso"]:
            avisos.append(f"Tipo «{uso}» desconocido: queda sin definir")
        fila["uso_texto"] = Obra.Uso(fila["uso"]).label if fila["uso"] else ""

        estado = _texto(crudo.get("estado"))
        fila["estado"] = ESTADOS.get(_clave(estado), Obra.Estado.ACTIVA)
        if estado and _clave(estado) not in ESTADOS:
            avisos.append(f"Estado «{estado}» desconocido: queda Activo")

        fila["superficie_m2"] = None
        if _texto(crudo.get("superficie_m2")):
            try:
                fila["superficie_m2"] = str(_superficie(crudo["superficie_m2"]))
            except (InvalidOperation, ValueError):
                avisos.append(f"Superficie «{_texto(crudo['superficie_m2'])}» no es un número: queda vacía")

        fila["fecha_inicio"] = None
        if _texto(crudo.get("fecha_inicio")):
            try:
                fila["fecha_inicio"] = _fecha(crudo["fecha_inicio"]).isoformat()
            except ValueError:
                avisos.append(f"Fecha «{_texto(crudo['fecha_inicio'])}» no se entiende (usá dd/mm/aaaa): queda vacía")

        fila["etapa_texto"] = Obra.Etapa(fila["etapa"]).label
        fila["estado_texto"] = Obra.Estado(fila["estado"]).label.split(" (")[0]
        resultado.append(fila)
    return resultado


def crear(filas, usuario, plantilla=None):
    """Crea los proyectos marcados «crear» (todo o nada) y devuelve la lista de creados."""
    creados = []
    with transaction.atomic():
        for f in filas:
            if f["accion"] != "crear":
                continue
            # Se vuelve a controlar por si alguien creó uno igual entre la vista previa y el OK.
            if Obra.objects.filter(tipo=Obra.Tipo.PROYECTO, nombre__iexact=f["nombre"]).exists():
                continue
            codigo = f["codigo"] if f["codigo"] and not Obra.objects.filter(codigo__iexact=f["codigo"]).exists() else ""
            obra = Obra.objects.create(
                tipo=Obra.Tipo.PROYECTO, nombre=f["nombre"], codigo=codigo, direccion=f["direccion"],
                localidad=f["localidad"], descripcion=f["descripcion"], uso=f.get("uso", ""), etapa=f["etapa"], estado=f["estado"],
                superficie_m2=Decimal(f["superficie_m2"]) if f["superficie_m2"] else None,
                fecha_inicio=date.fromisoformat(f["fecha_inicio"]) if f["fecha_inicio"] else None,
                creada_por=usuario,
            )
            if plantilla:
                arbol.copiar(plantilla.tareas.all(), TareaObra, {"obra": obra})
                obra.recalcular_avance()
            fuente = f" con la plantilla «{plantilla}»" if plantilla else ""
            registrar("obra.alta", f"Alta de proyecto: {obra}{fuente} (importado desde Excel)", objeto=obra,
                      usuario=usuario)
            creados.append(obra)
    return creados
