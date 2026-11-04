"""Importar proyectos desde la planilla modelo: vista previa, confirmación, plantilla y duplicados."""

import io
from datetime import date
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import Workbook

from apps.obras.models import Obra
from apps.plantillas.models import Plantilla

from .conftest import cliente_de

ENCABEZADO = ["Nombre *", "Código", "Dirección", "Localidad", "Superficie (m²)", "Etapa", "Estado",
              "Fecha de inicio", "Descripción"]


def planilla(*filas):
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Proyectos"
    hoja.append(ENCABEZADO)
    hoja.append(["Casa Ejemplo (borrar esta fila)", "", "", "", 180, "Anteproyecto", "Activo", "", ""])
    for f in filas:
        hoja.append(list(f) + [None] * (len(ENCABEZADO) - len(f)))
    salida = io.BytesIO()
    libro.save(salida)
    return SimpleUploadedFile("proyectos.xlsx", salida.getvalue())


def base():
    return Plantilla.objects.get(nombre="Proyecto de Arquitectura")


def subir(c, archivo, plantilla=None):
    return c.post("/proyectos/importar/", {"archivo": archivo, "plantilla": plantilla.pk if plantilla else ""})


def test_vista_previa_y_alta_con_la_plantilla(dir_):
    c = cliente_de(dir_)
    r = subir(c, planilla(
        ("Casa Norte", "CN", "Country Praderas", "Yerba Buena", "1.250,5", "Proyecto Ejecutivo", "Activo",
         date(2026, 11, 1), "Vivienda unifamiliar"),
        ("Torre Sur", None, None, "SDE", None, "Pre Anteproyecto", "Stand by"),
        ("Plaza", None, None, None, None, "Masterplan", None),
    ), base())
    html = r.content.decode()
    assert r.status_code == 200 and "Crear 3 proyectos" in html and "Casa Ejemplo" not in html
    assert not Obra.objects.exists()  # la vista previa no crea nada

    r = c.post("/proyectos/importar/", {"confirmar": "1"})
    assert r.status_code == 302
    casa = Obra.objects.get(nombre="Casa Norte")
    assert (casa.tipo, casa.codigo, casa.etapa, casa.estado) == ("proyecto", "CN", "ejecutivo", "activa")
    assert (casa.superficie_m2, casa.fecha_inicio, casa.creada_por) == (Decimal("1250.50"), date(2026, 11, 1), dir_)
    assert casa.tareas.count() == base().tareas.count() > 0
    torre = Obra.objects.get(nombre="Torre Sur")
    assert (torre.etapa, torre.estado, torre.codigo.startswith("PR-")) == ("preanteproyecto", "pausada", True)
    assert Obra.objects.get(nombre="Plaza").etapa == "masterplan"


def test_no_duplica_nombres_ni_codigos(dir_):
    Obra.objects.create(tipo=Obra.Tipo.PROYECTO, nombre="Casa Norte", codigo="CN")
    c = cliente_de(dir_)
    html = subir(c, planilla(("casa  norte",), ("Otra", "CN"), ("Otra más", "CN"))).content.decode()
    assert "Ya existe un proyecto con ese nombre" in html and "ya está usado" in html
    c.post("/proyectos/importar/", {"confirmar": "1"})
    assert Obra.objects.filter(nombre__iexact="casa norte").count() == 1
    otra = Obra.objects.get(nombre="Otra")
    assert otra.codigo != "CN" and otra.tareas.count() == 0  # sin plantilla


def test_avisa_lo_que_no_entiende(dir_):
    html = subir(cliente_de(dir_), planilla(("Casa", None, None, None, "mucho", "Etapa rara", None, "ayer"))).content.decode()
    for aviso in ("no es un número", "Etapa «Etapa rara» desconocida", "no se entiende"):
        assert aviso in html


def test_planilla_sin_columna_nombre(dir_):
    libro = Workbook()
    libro.active.append(["Cualquier cosa"])
    salida = io.BytesIO()
    libro.save(salida)
    html = subir(cliente_de(dir_), SimpleUploadedFile("x.xlsx", salida.getvalue())).content.decode()
    assert "No encontré la columna «Nombre»" in html


def test_solo_dir_importa(coordinador, comun):
    for u in (coordinador, comun):
        assert cliente_de(u).get("/proyectos/importar/").status_code == 403
        assert "Importar desde Excel" not in cliente_de(u).get("/proyectos/").content.decode()
