"""Listado de tareas (SPEC 13-15) e historial de avance."""

import json
from datetime import date, timedelta
from decimal import Decimal

from apps.obras import avances
from apps.obras.models import AvanceTarea, TareaObra
from apps.plantillas import arbol

from .conftest import asignar, cliente_de

T = TareaObra.Tipo


def armar(obra):
    """Un rubro con dos ítems (uno con montos) y un rubro suelto."""
    datos = [
        {"tipo": T.RUBRO, "nombre": "Hormigón", "codigo": "3", "incidencia": Decimal(60), "hijos": [
            {"tipo": T.ITEM, "nombre": "Bases", "codigo": "3.2", "unidad": "m³", "cantidad": Decimal("33.3"),
             "monto": Decimal("4831037.50"), "incidencia": Decimal(70), "avance": 0, "hijos": []},
            {"tipo": T.ITEM, "nombre": "Fustes", "codigo": "3.6", "unidad": "m³", "incidencia": Decimal(30),
             "avance": 0, "hijos": []},
        ]},
        {"tipo": T.RUBRO, "nombre": "Limpieza", "incidencia": Decimal(40), "avance": 50, "hijos": []},
    ]
    arbol.guardar(TareaObra, {"obra": obra}, datos, con_avance=True)
    return {t.nombre: t for t in obra.tareas.all()}


def estructura_del_editor(obra):
    return arbol.a_datos(obra.tareas.all(), con_avance=True)


def test_guardar_desde_el_editor_conserva_ids_unidad_y_montos(obra):
    t = armar(obra)
    datos = estructura_del_editor(obra)
    assert "monto" not in json.dumps(datos)  # los montos no viajan al editor
    datos[0]["hijos"][0]["nombre"] = "Bases (corregido)"
    datos[0]["hijos"][1]["avance"] = 40
    limpio = arbol.validar(datos, con_avance=True)
    arbol.guardar(TareaObra, {"obra": obra}, limpio, con_avance=True)
    bases = TareaObra.objects.get(pk=t["Bases"].pk)
    assert bases.nombre == "Bases (corregido)"
    assert bases.unidad == "m³" and bases.cantidad == Decimal("33.300") and bases.codigo == "3.2"
    assert bases.monto == Decimal("4831037.50")
    assert TareaObra.objects.get(pk=t["Fustes"].pk).avance == 40


def test_las_filas_quitadas_en_el_editor_se_borran(obra):
    armar(obra)
    datos = estructura_del_editor(obra)
    datos[0]["hijos"].pop(1)
    arbol.guardar(TareaObra, {"obra": obra}, arbol.validar(datos, con_avance=True), con_avance=True)
    assert not obra.tareas.filter(nombre="Fustes").exists()
    assert obra.tareas.get(nombre="Bases").incidencia == Decimal(100)  # el grupo vuelve a sumar 100


def test_las_incidencias_de_cada_grupo_suman_100(obra):
    armar(obra)
    for padre in [None, *obra.tareas.filter(hijos__isnull=False).distinct()]:
        hermanos = obra.tareas.filter(padre=padre)
        assert sum(h.incidencia for h in hermanos) == Decimal(100)


def test_mover_la_barra_queda_en_el_historial(comun, obra):
    asignar(comun, obra, responsable=True)
    t = armar(obra)
    c = cliente_de(comun)
    assert c.post(f"/obras/{obra.pk}/tareas/{t['Bases'].pk}/avance/", {"avance": 30}).status_code == 200
    assert c.post(f"/obras/{obra.pk}/tareas/{t['Bases'].pk}/avance/", {"avance": 45}).status_code == 200
    registros = list(AvanceTarea.objects.filter(tarea=t["Bases"]))
    assert len(registros) == 1  # mismo día y misma persona: un solo registro
    assert (registros[0].anterior, registros[0].avance, registros[0].usuario) == (0, 45, comun)
    c.post(f"/obras/{obra.pk}/tareas/{t['Bases'].pk}/avance/", {"avance": 0})
    assert not AvanceTarea.objects.filter(tarea=t["Bases"]).exists()  # volvió a como empezó el día


def test_guardar_el_editor_anota_los_avances_que_cambiaron(comun, obra):
    asignar(comun, obra, responsable=True)
    t = armar(obra)
    datos = estructura_del_editor(obra)
    datos[0]["hijos"][1]["avance"] = 100
    respuesta = cliente_de(comun).post(f"/obras/{obra.pk}/tareas/", {"estructura": json.dumps(datos)})
    assert respuesta.status_code == 302
    registro = AvanceTarea.objects.get(tarea=t["Fustes"])
    assert (registro.anterior, registro.avance) == (0, 100)
    assert not AvanceTarea.objects.filter(tarea=t["Bases"]).exists()


def test_la_retrospectiva_cuenta_los_dias_de_0_a_100(obra):
    t = armar(obra)
    bases, inicio = t["Bases"], date(2026, 9, 1)
    for dias, anterior, nuevo in [(0, 0, 20), (6, 20, 70), (14, 70, 100)]:
        avances.registrar(bases, anterior, nuevo, fecha=inicio + timedelta(days=dias), origen=AvanceTarea.Origen.CERTIFICADO)
    fila = next(f for f in avances.retrospectiva(obra) if f["tarea"].pk == bases.pk)
    assert (fila["inicio"], fila["fin"], fila["dias"]) == (inicio, inicio + timedelta(days=14), 14)


def test_si_ya_tenia_avance_en_la_primera_carga_no_se_inventa_el_inicio(obra):
    t = armar(obra)
    AvanceTarea.objects.create(tarea=t["Fustes"], obra=obra, fecha=date(2026, 9, 30), anterior=None, avance=60,
                               origen=AvanceTarea.Origen.CERTIFICADO)
    avances.registrar(t["Fustes"], 60, 100, fecha=date(2026, 10, 15), origen=AvanceTarea.Origen.CERTIFICADO)
    fila = next(f for f in avances.retrospectiva(obra) if f["tarea"].pk == t["Fustes"].pk)
    assert fila["inicio"] is None and fila["antes_de"] == date(2026, 9, 30)
    assert fila["fin"] == date(2026, 10, 15) and fila["dias"] is None


def test_lo_que_ya_estaba_completo_en_la_primera_carga_no_dice_cuando_termino(obra):
    t = armar(obra)
    AvanceTarea.objects.create(tarea=t["Bases"], obra=obra, fecha=date(2026, 9, 30), anterior=None, avance=100,
                               origen=AvanceTarea.Origen.CERTIFICADO)
    fila = next(f for f in avances.retrospectiva(obra) if f["tarea"].pk == t["Bases"].pk)
    assert fila["completa_antes"] and fila["fin"] is None and fila["dias"] is None
